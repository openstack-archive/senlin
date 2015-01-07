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
import types

import eventlet
from oslo.config import cfg
import six

from senlin.common.i18n import _LI
from senlin.db import api as db_api
from senlin.openstack.common import log as logging
from senlin.openstack.common import threadgroup

LOG = logging.getLogger(__name__)


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

    def cancel_action(self, cnxt, action_id):
        # We just kill the action thread directly.
        # TODO(Yanyan): use event to handle action cancelling,
        # something like this :
        #     self.send('cancel', action_id)
        th = self.threads[action_id]
        th.kill()
        self.threads.pop(action_id)


class ActionProc(object):
    """
    Wrapper for a resumable task(co-routine) for action execution
    """
    def __init__(self, cnxt, action, event=None):
        self.cnxt = cnxt
        self.action = action
        self.event = event
        self.done = False

    def _sleep(self, wait_time):
        """Sleep for the specified number of seconds."""
        if ENABLE_SLEEP and wait_time is not None:
            LOG.debug('%s sleeping' % six.text_type(self))
            eventlet.sleep(wait_time)

    def __call__(self,  wait_time=1):
        """
        Start and run action progress.

        Action progress will sleep for `wait_time` seconds between 
        each step. To avoid sleeping, pass `None` for `wait_time`.
        """
        status = self.action.get_status()
        while status in (self.action.INIT, self.action.WAITING):
            # TODO(Qiming): Handle 'start_time' field of an action
            yield
            status = self.action.get_status()

        # Exit quickly if action has been taken care of or marked
        # completed or cancelled by other activities
        if status != self.action.READY:
            return

        # Do the first step
        result = self.start(timeout=self.action.timeout)
        if result == self.action.ERROR:
            # Error happened during the start,
            # mark entire action as failed and return
            db_api.action_mark_failed(self.cnxt, self.action.id)
            return

        # Do remaining steps
        while not self.done:
            # move one step each time, and then wait for
            # a while for possible control ops, e.g. 
            # canceling, suspend, resume
            result = self.step()
            if event is None or not event.ready():
                self._sleep(wait_time)
            else:
                msg = self.event.wait()
                if msg == 'cancel':
                    self.cancel()
                else:
                    pass

        if result == self.action.ERROR:
            # Error happened during remaining steps,
            # mark action as failed and return
            db_api.action_mark_failed(self.cnxt, self.action.id)
            return

        # Action executing has completed, mark its status to OK
        db_api.action_mark_succeeded(self.cnxt, self.action.id)
        LOG.info(_LI('Successfully run action %s.'), self.action.id)

    def start(self, timeout=None):
        """
        Initialise the task and run its first step.

        If a timeout is specified, any attempt to step the task after that
        number of seconds has elapsed will result in a Timeout being
        raised inside the task.
        """
        assert self.execution is None, "Action already started"
        assert not self.done, "Action already cancelled"

        LOG.debug('%s starting' % six.text_type(self))

        if timeout is not None:
            self._timeout = Timeout(self, timeout)

        self.action.set_status(self.action.RUNNING)
        result = self.action.execute()
        # Mark action status to RUNNING
        if isinstance(result, types.GeneratorType):
            # If the execute() of action is a generator
            # run its first step.
            self.execution = result
            self.step()
        else:
            # if not, the execute() progress should have done,
            # return execute result
            self.execution = False
            self.done = True
            LOG.debug('%s done (not resumable)' % six.text_type(self))
            return result

    def step(self):
        """
        Run one step of the action. If error happened during
        this step, return action.Error. If not, return True if
        the task is complete, false otherwise.
        """
        if not self.done:
            assert self.execution is not None, "Action not started"

            if self._timeout is not None and self._timeout.expired():
                LOG.info(_LI('%s timed out'), six.text_type(self))
                self.done = True

                # Trigger the timeout of action execution
                self._timeout.trigger(self.execution)
            else:
                LOG.debug('%s running' % six.text_type(self))

                try:
                    result = next(self.execution)
                except StopIteration:
                    self.done = True
                    LOG.debug('%s complete' % six.text_type(self))

        if result == self.action.ERROR:
            # Error happened during this step, cancel
            # this action execution, mark it as one
            # and return action.ERROR flag
            LOG.info(_LI('Error happened during action %s running.'),
                     self.action.id)
            self.cancel()
            self.done = True
            return result
        else:
            # No error happened, return current done status
            return self.done

    def cancel(self, grace_period=None):
        """Cancel the task and mark it as done."""
        if self.done:
            return

        if not self.started() or grace_period is None:
            LOG.debug('%s cancelled' % six.text_type(self))
            self.done = True
            if self.started():
                self.execution.close()
        else:
            timeout = Timeout(self, grace_period, True)
            if self._timeout is None or timeout < self._timeout:
                self._timeout = timeout

    def started(self):
        """Return True if the task has been started."""
        return self.execution is not None


class Timeout(BaseException):
    """
    Timeout exception, raised within an action when it has exceeded 
    its allotted(wallclock) running time.
    """

    def __init__(self, action_proc, timeout, enforce=False):
        """
        Initialise with the TaskRunner and a timeout period in seconds.
        """
        self.enforce = enforce
        message = _('%s Timed out') % six.text_type(action_proc)
        super(Timeout, self).__init__(message)

        self._endtime = wallclock() + timeout

    def expired(self):
        return wallclock() > self._endtime

    def trigger(self, generator):
        """Trigger the timeout on a given generator."""
        if enforce:
            generator.close()
            return False
        try:
            generator.throw(self)
        except StopIteration:
            return True
        else:
            # Clean up in case task swallows exception without exiting
            generator.close()
            return False

    def __cmp__(self, other):
        if not isinstance(other, Timeout):
            return NotImplemented
        return cmp(self._endtime, other._endtime)
