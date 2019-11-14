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
import oslo_messaging
from oslo_utils import uuidutils
from osprofiler import profiler

from senlin.common import consts
from senlin.common import context
from senlin.common import context as senlin_context
from senlin.common import messaging
from senlin.common import service
from senlin.engine.actions import base as action_mod
from senlin.engine import event as EVENT
from senlin.objects import action as ao
from senlin.objects import service as service_obj

LOG = logging.getLogger(__name__)
CONF = cfg.CONF

wallclock = time.time


@profiler.trace_cls("rpc")
class EngineService(service.Service):
    """RPC server for dispatching actions.

    Receive notification from dispatcher services and schedule actions.
    """

    def __init__(self, host, topic):
        super(EngineService, self).__init__(
            self.service_name, host, topic,
            threads=CONF.engine.threads
        )
        self.version = consts.RPC_API_VERSION

        self.server = None
        self.service_id = None
        self.target = None

        # TODO(Yanyan Hu): Build a DB session with full privilege
        # for DB accessing in scheduler module
        self.db_session = context.RequestContext(is_admin=True)

        # Initialize the global environment
        EVENT.load_dispatcher()

    @property
    def service_name(self):
        return 'senlin-engine'

    def start(self):
        """Start the engine.

        Note that the engine is an internal server, we are not using
        versioned object for parameter passing.
        """
        super(EngineService, self).start()
        self.service_id = uuidutils.generate_uuid()

        self.target = oslo_messaging.Target(server=self.service_id,
                                            topic=self.topic,
                                            version=self.version)

        self.server = messaging.get_rpc_server(self.target, self)
        self.server.start()

        # create service record
        ctx = senlin_context.get_admin_context()
        service_obj.Service.create(ctx, self.service_id, self.host,
                                   self.service_name, self.topic)

        self.tg.add_timer(CONF.periodic_interval, self.service_manage_report)

    def stop(self, graceful=True):
        if self.server:
            self.server.stop()
            self.server.wait()

        service_obj.Service.delete(self.service_id)
        LOG.info('Engine %s deleted', self.service_id)

        super(EngineService, self).stop(graceful)

    def service_manage_report(self):
        try:
            ctx = senlin_context.get_admin_context()
            service_obj.Service.update(ctx, self.service_id)
        except Exception as ex:
            LOG.error('Error while updating dispatcher service: %s', ex)

    def execute(self, func, *args, **kwargs):
        """Run the given method in a thread."""
        req_cnxt = oslo_context.get_current()
        self.tg.add_thread(
            self._start_with_trace, req_cnxt,
            self._serialize_profile_info(),
            func, *args, **kwargs
        )

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

    def listening(self, ctxt):
        """Respond affirmatively to confirm that engine is still alive."""
        return True

    def start_action(self, ctxt, action_id=None):
        """Run action(s) in sub-thread(s).

        :param action_id: ID of the action to be executed. None means all
                          ready actions will be acquired and scheduled to run.
        """
        actions_launched = 0
        max_batch_size = cfg.CONF.max_actions_per_batch
        batch_interval = cfg.CONF.batch_interval

        if action_id is not None:
            timestamp = wallclock()
            action = ao.Action.acquire(self.db_session, action_id,
                                       self.service_id,
                                       timestamp)
            if action:
                self.execute(action_mod.ActionProc, self.db_session, action.id)
                actions_launched += 1

        while True:
            timestamp = wallclock()
            action = ao.Action.acquire_first_ready(self.db_session,
                                                   self.service_id,
                                                   timestamp)
            if not action:
                break

            if max_batch_size == 0 or 'NODE' not in action.action:
                self.execute(action_mod.ActionProc, self.db_session, action.id)
                continue

            if max_batch_size > actions_launched:
                self.execute(action_mod.ActionProc, self.db_session, action.id)
                actions_launched += 1
                continue

            self.execute(action_mod.ActionProc, self.db_session, action.id)

            LOG.debug(
                'Engine %(id)s has launched %(num)s node actions '
                'consecutively, stop scheduling node action for '
                '%(interval)s second...',
                {
                    'id': self.service_id,
                    'num': max_batch_size,
                    'interval': batch_interval
                })

            sleep(batch_interval)
            actions_launched = 1

    def cancel_action(self, ctxt, action_id):
        """Cancel an action execution progress."""
        action = action_mod.Action.load(self.db_session, action_id,
                                        project_safe=False)
        action.signal(action.SIG_CANCEL)

    def suspend_action(self, ctxt, action_id):
        """Suspend an action execution progress."""
        action = action_mod.Action.load(self.db_session, action_id,
                                        project_safe=False)
        action.signal(action.SIG_SUSPEND)

    def resume_action(self, ctxt, action_id):
        """Resume an action execution progress."""
        action = action_mod.Action.load(self.db_session, action_id,
                                        project_safe=False)
        action.signal(action.SIG_RESUME)


def sleep(sleep_time):
    """Interface for sleeping."""

    eventlet.sleep(sleep_time)
