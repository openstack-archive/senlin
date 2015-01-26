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

import time

import eventlet
from oslo_config import cfg
import six

from senlin.common.i18n import _LI
from senlin.db import api as db_api
from senlin.openstack.common import log as logging
from senlin.openstack.common import threadgroup

LOG = logging.getLogger(__name__)

wallclock = time.time

ACTION_CONTROL_REQUEST = (
    ACTION_CANCEL, ACTION_SUSPEND, ACTION_RESUME, ACTION_TIMEOUT,
) = (
    'cancel', 'suspend', 'resume', 'timeout',
)


class ThreadGroupManager(object):
    """
    """
    def __init__(self):
        super(ThreadGroupManager, self).__init__()
        self.threads = {}
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

    def start_action_thread(self, cnxt, action, *args, **kwargs):
        """
        Run the given action in a sub-thread and release the action lock
        when the thread finishes.

        :param cnxt: The context of rpc request
        :param action: The action to run in thread

        """
        def release(gt, cnxt, action):
            """
            Callback function that will be passed to GreenThread.link().
            """
            # Remove action thread from thread list
            self.threads.pop(action.id)

        action_proc = ActionProc(cnxt, action)
        th = self.start(action_proc, *args, **kwargs)
        self.threads[action.id] = th
        th.link(release, cnxt, action)
        return th

    def add_timer(self, interval, func, *args, **kwargs):
        """
        Define a periodic task, to be run in a separate thread, in the target
        threadgroups.  Periodicity is cfg.CONF.periodic_interval
        """
        self.group.add_timer(cfg.CONF.periodic_interval,
                             func, *args, **kwargs)

    def stop_timers(self):
        self.group.stop_timers()

    def stop(self, graceful=False):
        '''Stop any active threads belong to this threadgroup.'''
        # Try to stop all threads gracefully
        self.group.stop(graceful)
        self.group.wait()

        # Wait for link()ed functions (i.e. lock release)
        threads = self.group.threads[:]
        links_done = dict((th, False) for th in threads)

        def mark_done(gt, th):
            links_done[th] = True

        for th in threads:
            th.link(mark_done, th)

        while not all(links_done.values()):
            eventlet.sleep()


class ActionProc(object):
    """
    Wrapper for a resumable task(co-routine) for action execution
    """
    def __init__(self, cnxt, action):
        self.cnxt = cnxt
        self.action = action

    def __call__(self, wait_time=1):
        """
        Start and run action progress.

        Action progress will sleep for `wait_time` seconds between
        each step. To avoid sleeping, pass `None` for `wait_time`.
        """
        status = self.action.get_status()
        while status in (self.action.INIT, self.action.WAITING):
            # TODO(Qiming): Handle 'start_time' field of an action
            reschedule(self.action, sleep=self.wait_time)
            status = self.action.get_status()

        # Exit quickly if action has been taken care of or marked
        # completed or cancelled by other activities
        if status != self.action.READY:
            return

        # Do the first step
        LOG.debug('%s starting' % six.text_type(self))

        # Start action execute
        self.action.set_status(self.action.RUNNING)
        self.action.start_time = wallclock()

        result = self.action.execute()

        self.action.end_time = wallclock()

        if result == self.action.ERROR:
            # Error happened during the start,
            # mark entire action as failed and return
            LOG.info(_LI('Successfully run action %s.'), self.action.id)
            db_api.action_mark_failed(self.cnxt, self.action.id)
        elif result == self.action.OK:
            LOG.info(_LI('Action %s run failed.'), self.action.id)
            db_api.action_mark_succeeded(self.cnxt, self.action.id)
        else:
            # TODO(Yanyan): handle action retry scenario.
            pass


def start_action(cnxt, action_id, engine_id, tgm):
    """
    Start an action execution progress using given ThreadGroupManager

    :param cnxt: The context of rpc request
    :param action_id: The id of action to run in thread
    :param engine_id: The id of engine try to lock the action
    :param tgm: The ThreadGroupManager of the engine
    """
    action = db_api.action_start_work_on(cnxt, action_id, engine_id)
    if action:
        # Lock action successfully, start a thread to run it
        LOG.info(_LI('Successfully locked action %s.'), action_id)
        th = tgm.start_action_thread(cnxt, action)
        if th is None:
            LOG.debug('Action start failed, unlock action.')
            # TODO(anyone): need db_api support
            db_api.action_unlock(cnxt, action_id, engine_id)
        else:
            return True
    else:
        # The action has been locked which means other
        # dispatcher has start to work on it, so just return
        LOG.info(_LI('Action %s has been locked by other dispatcher'),
                 action_id)


def suspend_action(cnxt, action_id):
    """
    Try to suspend an action execution progress

    :param cnxt: The context of rpc request
    :param action_id: The id of action to run in thread
    """
    # Set action control flag to suspend
    # TODO(anyone): need db_api support
    db_api.action_control(cnxt, action_id, ACTION_SUSPEND)


def resume_action(cnxt, action_id):
    """
    Try to resume an action execution progress

    :param cnxt: The context of rpc request
    :param action_id: The id of action to run in thread
    """
    # Set action control flag to suspend
    # TODO(anyone): need db_api support
    db_api.action_control(cnxt, action_id, ACTION_RESUME)


def cancel_action(cnxt, action_id):
    """
    Try to cancel an action execution progress

    :param cnxt: The context of rpc request
    :param action_id: The id of action to run in thread
    """
    # Set action control flag to cancel
    # TODO(anyone): need db_api support
    db_api.action_control(cnxt, action_id, ACTION_CANCEL)


def action_control_flag(action):
    """
    Check whether there are some action control requests
    need to be handled.
    """
    # Check timeout first, if true, return timeout message
    if action.timeout is not None and action_timeout(action):
        LOG.debug('Action %s run timeout' % action.id)
        return ACTION_TIMEOUT

    # Check if action control flag is set
    result = db_api.action_control_check(action.context, action.id)
    LOG.debug('Action %s control flag is %s', (action.id, result))
    return result


def action_cancelled(action):
    """
    Check whether an action's control flag is set to cancel
    """
    if action_control_flag(action) == ACTION_CANCEL:
        return True
    else:
        return False


def action_suspended(action):
    """
    Check whether an action's control flag is set to suspend
    """
    if action_control_flag(action) == ACTION_SUSPEND:
        return True
    else:
        return False


def action_resumed(action):
    """
    Check whether an action's control flag is set to suspend
    """
    if action_control_flag(action) == ACTION_RESUME:
        return True
    else:
        return False


def action_timeout(action):
    """
    Return True if an action has run timeout, False otherwise.
    """
    time_lapse = wallclock() - action.start_time

    if time_lapse > action.timeout:
        return True
    else:
        return False


def reschedule(action, sleep_time=1):
    """
    Eventlet Sleep for the specified number of seconds.

    :param sleep_time: seconds to sleep; if None, no sleep;
    """
    if sleep_time is not None:
        LOG.debug('Action %s sleep for %s seconds' % (
            action.id, sleep_time))
        eventlet.sleep(sleep_time)


def action_wait(action):
    """
    Keep waiting util action resume control flag is set
    """
    while not action_resumed(action):
        reschedule(action, sleep_time=1)
        continue


def sleep(sleep_time):
    '''
    Interface for sleeping.
    '''
    eventlet.sleep(sleep_time)
