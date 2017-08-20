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
from oslo_context import context as oslo_context
from oslo_log import log as logging
from oslo_service import threadgroup
from osprofiler import profiler

from senlin.common import context
from senlin.common.i18n import _
from senlin.engine.actions import base as action_mod
from senlin.objects import action as ao

LOG = logging.getLogger(__name__)

wallclock = time.time


class ThreadGroupManager(object):
    '''Thread group manager.'''

    def __init__(self):
        super(ThreadGroupManager, self).__init__()
        self.workers = {}
        self.group = threadgroup.ThreadGroup()

        # Create dummy service task, because when there is nothing queued
        # on self.tg the process exits
        self.add_timer(cfg.CONF.periodic_interval, self._service_task)

        # TODO(Yanyan Hu): Build a DB session with full privilege
        # for DB accessing in scheduler module
        self.db_session = context.RequestContext(is_admin=True)

    def _service_task(self):
        '''Dummy task which gets queued on the service.Service threadgroup.

        Without this service.Service sees nothing running i.e has nothing to
        wait() on, so the process exits..
        This could also be used to trigger periodic non-cluster-specific
        housekeeping tasks

        (Yanyan)Not sure this is still necessary, just keep it temporarily.
        '''
        # TODO(Yanyan): have this task call dbapi purge events
        pass

    def _serialize_profile_info(self):
        prof = profiler.get()
        trace_info = None
        if prof:
            trace_info = {
                "hmac_key": prof.hmac_key,
                "base_id": prof.get_base_id(),
                "parent_id": prof.get_id()
            }
        return trace_info

    def _start_with_trace(self, cnxt, trace, func, *args, **kwargs):
        if trace:
            profiler.init(**trace)
        if cnxt is not None:
            cnxt.update_store()
        return func(*args, **kwargs)

    def start(self, func, *args, **kwargs):
        '''Run the given method in a thread.'''

        req_cnxt = oslo_context.get_current()
        return self.group.add_thread(self._start_with_trace, req_cnxt,
                                     self._serialize_profile_info(),
                                     func, *args, **kwargs)

    def start_action(self, worker_id, action_id=None):
        '''Run action(s) in sub-thread(s).

        :param worker_id: ID of the worker thread; we fake workers using
                          senlin engines at the moment.
        :param action_id: ID of the action to be executed. None means all
                          ready actions will be acquired and scheduled to run.
        '''
        def launch(action_id):
            '''Launch a sub-thread to run given action.'''
            th = self.start(action_mod.ActionProc, self.db_session, action_id)
            self.workers[action_id] = th
            th.link(release, action_id)
            return th

        def release(thread, action_id):
            '''Callback function that will be passed to GreenThread.link().'''
            # Remove action thread from thread list
            self.workers.pop(action_id)

        actions_launched = 0
        if action_id is not None:
            timestamp = wallclock()
            action = ao.Action.acquire(self.db_session, action_id, worker_id,
                                       timestamp)
            if action:
                launch(action.id)
                actions_launched += 1

        batch_size = cfg.CONF.max_actions_per_batch
        batch_interval = cfg.CONF.batch_interval
        while True:
            timestamp = wallclock()
            action = ao.Action.acquire_first_ready(self.db_session, worker_id,
                                                   timestamp)
            if action:
                if batch_size > 0 and 'NODE' in action.action:
                    if actions_launched < batch_size:
                        launch(action.id)
                        actions_launched += 1
                    else:
                        msg = _('Engine %(id)s has launched %(num)s node '
                                'actions consecutively, stop scheduling '
                                'node action for %(interval)s second...'
                                ) % {'id': worker_id, 'num': batch_size,
                                     'interval': batch_interval}
                        LOG.debug(msg)
                        sleep(batch_interval)
                        launch(action.id)
                        actions_launched = 1
                else:
                    launch(action.id)
            else:
                break

    def cancel_action(self, action_id):
        '''Cancel an action execution progress.'''
        action = action_mod.Action.load(self.db_session, action_id,
                                        project_safe=False)
        action.signal(action.SIG_CANCEL)

    def suspend_action(self, action_id):
        '''Suspend an action execution progress.'''
        action = action_mod.Action.load(self.db_session, action_id,
                                        project_safe=False)
        action.signal(action.SIG_SUSPEND)

    def resume_action(self, action_id):
        '''Resume an action execution progress.'''
        action = action_mod.Action.load(self.db_session, action_id,
                                        project_safe=False)
        action.signal(action.SIG_RESUME)

    def add_timer(self, interval, func, *args, **kwargs):
        '''Define a periodic task to be run in the thread group.

        The task will be executed in a separate green thread.
        Interval is from cfg.CONF.periodic_interval
        '''
        timer = self.group.add_timer(interval, func, *args, **kwargs)
        return timer

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


def reschedule(action_id, sleep_time=1):
    '''Eventlet Sleep for the specified number of seconds.

    :param action_id: the action to put into sleep.
    :param sleep_time: seconds to sleep; if None, no sleep;
    '''
    if sleep_time is not None:
        LOG.debug('Action %s sleep for %s seconds' % (action_id, sleep_time))
        eventlet.sleep(sleep_time)


def sleep(sleep_time):
    '''Interface for sleeping.'''

    eventlet.sleep(sleep_time)
