#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

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
from senlin.engine import senlin_lock
from senlin.openstack.common import log as logging
from senlin.openstack.common import threadgroup

LOG = logging.getLogger(__name__)


class ThreadGroupManager(object):

    def __init__(self):
        super(ThreadGroupManager, self).__init__()
        self.groups = {}
        self.events = collections.defaultdict(list)

        # Create dummy service task, because when there is nothing queued
        # on self.tg the process exits
        self.add_timer(cfg.CONF.periodic_interval, self._service_task)

    def _service_task(self):
        """
        This is a dummy task which gets queued on the service.Service
        threadgroup.  Without this service.Service sees nothing running
        i.e has nothing to wait() on, so the process exits..
        This could also be used to trigger periodic non-cluster-specific
        housekeeping tasks
        """
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

    def _start_with_trace(self, trace, func, *args, **kwargs):
        if trace:
            profiler.init(**trace)
        return func(*args, **kwargs)

    def start(self, target_id, func, *args, **kwargs):
        """
        Run the given method in a sub-thread.
        """
        if target_id not in self.groups:
            self.groups[target_id] = threadgroup.ThreadGroup()
        return self.groups[target_id].add_thread(self._start_with_trace,
                                                self._serialize_profile_info(),
                                                func, *args, **kwargs)

    def start_with_lock(self, cnxt, target, target_type, engine_id,
                        func, *args, **kwargs):
        """
        Try to acquire a lock for operated target and, if successful,
        run the given method in a sub-thread.  Release the lock when
        the thread finishes.

        :param cnxt: RPC context
        :param target: Target to be operated on
        :param target_type: Type of operated target, e.g. cluster, node, etc.
        :param engine_id: The ID of the engine/worker acquiring the lock
        :param func: Callable to be invoked in sub-thread
        :type func: function or instancemethod
        :param args: Args to be passed to func
        :param kwargs: Keyword-args to be passed to func.
        """
        # TODO: add more target_type support
        # TODO: Reimplement this using __new__ method
        if target_type == 'cluster':
            lock = senlin_lock.ClusterLock(cnxt, target, engine_id)
        elif target_type == 'node':
            lock = senlin_lock.NodeLock(cnxt, target, engine_id)
        with lock.thread_lock(target.id):
            th = self.start_with_acquired_lock(target, lock,
                                               func, *args, **kwargs)
            return th

    def start_with_acquired_lock(self, target, lock, func, *args, **kwargs):
        """
        Run the given method in a sub-thread and release the provided lock
        when the thread finishes.

        :param target: Target to be operated on
        :type target: senlin.engine.parser.Stack
        :param lock: The acquired target lock
        :param func: Callable to be invoked in sub-thread
        :type func: function or instancemethod
        :param args: Args to be passed to func
        :param kwargs: Keyword-args to be passed to func

        """
        def release(gt, *args):
            """
            Callback function that will be passed to GreenThread.link().
            """
            lock.release(*args)

        th = self.start(target.id, func, *args, **kwargs)
        th.link(release, target.id)
        return th

    def add_timer(self, target_id, func, *args, **kwargs):
        """
        Define a periodic task, to be run in a separate thread, in the target
        threadgroups.  Periodicity is cfg.CONF.periodic_interval
        """
        if target_id not in self.groups:
            self.groups[target_id] = threadgroup.ThreadGroup()
        self.groups[target_id].add_timer(cfg.CONF.periodic_interval,
                                        func, *args, **kwargs)

    def add_event(self, target_id, event):
        self.events[target_id].append(event)

    def remove_event(self, gt, target_id, event):
        for e in self.events.pop(target_id, []):
            if e is not event:
                self.add_event(target_id, e)

    def stop_timers(self, target_id):
        if target_id in self.groups:
            self.groups[target_id].stop_timers()

    def stop(self, target_id, graceful=False):
        '''Stop any active threads on a target.'''
        if target_id in self.groups:
            self.events.pop(target_id, None)
            threadgroup = self.groups.pop(target_id)
            threads = threadgroup.threads[:]

            threadgroup.stop(graceful)
            threadgroup.wait()

            # Wait for link()ed functions (i.e. lock release)
            links_done = dict((th, False) for th in threads)

            def mark_done(gt, th):
                links_done[th] = True

            for th in threads:
                th.link(mark_done, th)
            while not all(links_done.values()):
                eventlet.sleep()

    def send(self, target_id, message):
        for event in self.events.pop(target_id, []):
            event.send(message)
