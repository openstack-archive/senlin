# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

import collections
import time

import eventlet
from oslo.config import cfg
import six

from senlin.common.i18n import _
from senlin.common.i18n import _LI
from senlin.db import api as db_api
from senlin.openstack.common import log as logging
from senlin.openstack.common import threadgroup

LOG = logging.getLogger(__name__)

wallclock = time.time


class Timeout(BaseException):
    """
    Timeout exception, raised within an action when it has exceeded
    its allotted(wallclock) running time.
    """

    def __init__(self, action_proc, timeout):
        """
        Initialise with the TaskRunner and a timeout period in seconds.
        """
        message = _('%s Timed out') % six.text_type(action_proc)
        super(Timeout, self).__init__(message)

        self._endtime = wallclock() + timeout

    def expired(self):
        return wallclock() > self._endtime


class ThreadGroupManager(object):

    def __init__(self):
        super(ThreadGroupManager, self).__init__()
        self.threads = {}
        self.events = collections.defaultdict(list)
        self.group = threadgroup.ThreadGroup()

        # Create dummy service task, because when there is nothing queued
        # on self.tg the process exits
        self.add_timer(cfg.CONF.periodic_interval, self._service_task)

    def _service_task(self):
        '''
        This is a dummy task which gets queued on the service.Service
        threadgroup.  Without this service.Service sees nothing running
        i.e has nothing to wait() on, so the process exits..
        This could also be used to trigger periodic non-cluster-specific
        housekeeping tasks

        (Yanyan)Not sure this is still necessary, just keep it temporarily.
        '''
        # TODO(Yanyan): have this task call dbapi purge events
        pass

    def start(self, func, *args, **kwargs):
        """
        Run the given method in a sub-thread.
        """
        return self.group.add_thread(func, *args, **kwargs)

    def start_action_thread(self, cnxt, action, event, *args, **kwargs):
        """
        Run the given action in a sub-thread and release the action lock
        when the thread finishes.

        :param cnxt: The context of rpc request
        :param action: The action to run in thread
        :param event: The event that action thread might wait for

        """
        def release(gt, cnxt, action_id):
            """
            Callback function that will be passed to GreenThread.link().
            """
            # Remove action thread from thread list
            self.threads.pop(action_id)

        action_proc = ActionProc(cnxt, action, event)
        th = self.start(action_proc, *args, **kwargs)
        th.link(release, cnxt, action.id)
        return th

    def add_timer(self, interval, func, *args, **kwargs):
        """
        Define a periodic task, to be run in a separate thread, in the target
        threadgroups.  Periodicity is cfg.CONF.periodic_interval
        """
        self.group.add_timer(cfg.CONF.periodic_interval,
                             func, *args, **kwargs)

    def add_event(self, action_id, event):
        '''Add an event to an action thread'''
        self.events[action_id].append(event)

    def remove_event(self, gt, action_id, event=None):
        '''Remove event from an action thread'''
        for e in self.events.pop(action_id, []):
            if event:
                if e is not event:
                    self.add_event(action_id, e)

    def stop_timers(self):
        self.group.stop_timers()

    def stop(self, graceful=False):
        '''Stop any active threads belong to this threadgroup.'''
        threads = self.group.threads[:]

        self.group.stop(graceful)
        self.group.wait()

        # Wait for link()ed functions (i.e. lock release)
        links_done = dict((th, False) for th in threads)

        def mark_done(gt, th):
            links_done[th] = True

        for th in threads:
            th.link(mark_done, th)

        while not all(links_done.values()):
            eventlet.sleep()

    def send(self, message, action_id, event=None):
        '''Send message to event belong to an action thread'''
        if event:
            # Just send message to specific event
            for e in self.events.pop(action_id, []):
                if e is event:
                    e.send(message)
        else:
            # Send message to all events
            for e in self.events.pop(action_id, []):
                e.send(message)

    def start_action(self, cnxt, action_id, engine_id):
        '''Start an action execution progress'''
        action = db_api.action_start_work_on(cnxt, action_id, engine_id)
        if action:
            # Lock action successfully, start a thread to run it
            LOG.info(_LI('Successfully locked action %s.'), action_id)
            # Create an event and inject it into thread, this
            # event is for action progress control, e.g. canceling
            event = eventlet.event.Event()
            th = self.start_action_thread(cnxt, action, event)
            th.link(self.remove_event, action.id)
            self.add_event(action.id, event)
            self.threads[action.id] = th
        else:
            # The action has been locked which means other
            # dispatcher has start to work on it, so just return
            LOG.info(_LI('Action %s has been locked by other dispatcher'),
                     action_id)

    def suspend_action(self, cnxt, action_id):
        '''Try to suspend an action execution progress'''
        self.send(ActionCheckpoint.SUSPEND, action_id)
        # TODO: need db_api support
        db_api.action_mark_suspended(self.cnxt, self.action.id)

    def resume_action(self, cnxt, action_id):
        '''Try to resume an action execution progress'''
        self.send(ActionCheckpoint.RESUME, action_id)
        # TODO: need db_api support
        db_api.action_mark_running(self.cnxt, self.action.id)

    def cancel_action(self, cnxt, action_id):
        '''Try to cancel an action execution progress'''
        self.send(ActionCheckpoint.CANCEL, action_id)
        db_api.action_mark_cancelled(self.cnxt, self.action.id)


class ActionProc(object):
    """
    Wrapper for a resumable task(co-routine) for action execution
    """
    def __init__(self, cnxt, action, event=None):
        self.cnxt = cnxt
        self.action = action
        self.event = event

    def __call__(self, wait_time=1):
        """
        Start and run action progress.

        Action progress will sleep for `wait_time` seconds between
        each step. To avoid sleeping, pass `None` for `wait_time`.
        """
        status = self.action.get_status()
        while status in (self.action.INIT, self.action.WAITING):
            # TODO(Qiming): Handle 'start_time' field of an action
            action_sleep(self.wait_time)
            status = self.action.get_status()

        # Exit quickly if action has been taken care of or marked
        # completed or cancelled by other activities
        if status != self.action.READY:
            return

        # Do the first step
        LOG.debug('%s starting' % six.text_type(self))

        if self.action.timeout is not None:
            _timeout = Timeout(self, self.action.timeout)
        else:
            _timeout = None

        # Create checkpoint for this action
        checkpoint = ActionCheckpoint(self.event, _timeout)

        # Start action execute
        self.action.set_status(self.action.RUNNING)
        result = self.action.execute(checkpoint=checkpoint)

        if result == self.action.ERROR:
            # Error happened during the start,
            # mark entire action as failed and return
            LOG.info(_LI('Successfully run action %s.'), self.action.id)
            db_api.action_mark_failed(self.cnxt, self.action.id)
        elif result == self.action.OK:
            LOG.info(_LI('Action %s run failed.'), self.action.id)
            db_api.action_mark_succeeded(self.cnxt, self.action.id)
        else:
            # TODO(Yanyan): handle action retry scenario?
            pass


class ActionCheckpoint(object):
    """
    Check possible action control input.
    """
    CONTROLS = (CANCEL, SUSPEND, RESUME, TIMEOUT) = (
        'cancel', 'suspend', 'resume', 'timeout')

    def __init__(self, event, timeout=None):
        self.event = event
        self.timeout = timeout

    def __call__(self, wait_time=0):
        """
        Check whether there are some action control events
        need to be handled or the action proc has timeout

        :param wait_time: seconds to wait if no any control
                          event exists; if None, no wait.
        """
        # Check timeout first, if true, return timeout message
        if self.timeout is not None and self.timeout.expired():
            LOG.info(_LI('%s timed out'), six.text_type(self))
            return self.TIMEOUT

        # Check possible control event
        if not self.event.ready():
            # Event is not ready, sleep if
            # necessary and then return
            self.action_sleep(wait_time)
            return
        else:
            # Get event message and return it
            message = self.event.wait()
            return message


def action_sleep(self, wait_time):
    """
    Eventlet Sleep for the specified number of seconds.

    :param wait_time: seconds to wait if no any control
                      event exists; if None, no sleep;
    """
    if wait_time is not None:
        LOG.debug('Action sleep for %s seconds' % wait_time)
        eventlet.sleep(wait_time)
