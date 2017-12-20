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


from oslo_log import log as logging
from senlin import objects

LOG = logging.getLogger(__name__)


class Endpoints(object):

    def __init__(self, project_id, engine_id, recover_action):
        self.engine_id = engine_id
        self.project_id = project_id
        self.recover_action = recover_action

    def info(self, ctxt, publisher_id, event_type, payload, metadata):
        raise NotImplementedError

    def _check_registry_status(self, ctx, engine_id, cluster_id):
        registry = objects.HealthRegistry.get_by_engine(ctx, engine_id,
                                                        cluster_id)

        if registry is None:
            return False

        if registry.enabled is True:
            return True

        return False
