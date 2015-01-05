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
import os

import eventlet
from oslo.config import cfg
from osprofiler import profiler

from senlin.common import exception
from senlin.common.i18n import _
from senlin.common.i18n import _LE
from senlin.common.i18n import _LI
from senlin.common.i18n import _LW
from senlin.db import api as db_api
from senlin.openstack.common import log as logging
from senlin.openstack.common import threadgroup

LOG = logging.getLogger(__name__)


class ThreadGroupManager(object):

    def __init__(self):
        super(ThreadGroupManager, self).__init__()
        self.threads = {}
        self.events = []
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
        def release(gt, cnxt, action_id):
            """
            Callback function that will be passed to GreenThread.link().
            """
            # Remove action thread from thread list
            self.threads.pop[action_id]

        th = self.start(self.action_proc, cnxt, action, *args, **kwargs)
        th.link(release, cnxt, action.id)
        return th

    def add_timer(self, interval, func, *args, **kwargs):
        """
        Define a periodic task, to be run in a separate thread, in the target
        threadgroups.  Periodicity is cfg.CONF.periodic_interval
        """
        self.group.add_timer(cfg.CONF.periodic_interval,
                             func, *args, **kwargs)

    def add_event(self, event):
        self.events.append(event)

    def remove_event(self, gt, event):
        for e in self.events:
            if e is not event:
                self.add_event(e)

    def stop_timers(self):
        self.group.stop_timers()

    def stop(self, graceful=False):
        '''Stop any active threads belong to this threadgroup.'''
        threads = self.group.threads[:]

        group.stop(graceful)
        group.wait()

        # Wait for link()ed functions (i.e. lock release)
        links_done = dict((th, False) for th in threads)

        def mark_done(gt, th):
            alinks_done[th] = True

        for th in threads:
            th.link(mark_done, th)

        while not all(links_done.values()):
            eventlet.sleep()

    def send(self, message):
        for event in self.events:
            event.send(message)

    def action_proc(self, cnxt, action):
        '''
        Thread procedure.
        '''
        status = action.get_status()
        while status in (action.INIT, action.WAITING):
            # TODO(Qiming): Handle 'start_time' field of an action
            yield
            status = action.get_status()

        # Exit quickly if action has been taken care of or marked
        # completed or cancelled by other activities
        if status != action.READY:
            return

        done = False
        while not done:
            # Take over the action
            action.set_status(action.RUNNING)

            result = action.execute()

            if result == action.OK:
                db_api.action_mark_succeeded(cnxt, action.id)
                done = True
            elif result == action.ERROR:
                db_api.action_mark_failed(cnxt, action.id)
                done = True
            elif result == action.RETRY:
                continue 

    def start_action(self, cnxt, action_id, engine_id):
        action = db_pai.action_start_work_on(cnxt, action_id, engine_id)
        if action:
            # Lock action successfully, start a thread to run it
            # TODO(Yanyan): create and inject event into thread
            LOG.info(_LI('Successfully locked action %s.'), action_id)
            th = self.start_action_thread(cnxt, action)
            self.threads[action.id] = th
        else:
            # The action has been locked which means other
            # dispatcher has start to work on it, so just return
            LOG.info(_LI('Action %s has been locked by other dispatcher'),
                    action_id)

    def cancel_action(self, cnxt, action_id):
        # We just kill the action thread directly.
        # TODO(Yanyan): use event wait() to handle action cancelling.
        th = self.threads[action_id]
        th.kill()
        self.threads.pop(action_id)
