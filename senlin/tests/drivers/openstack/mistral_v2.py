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


from oslo_utils import uuidutils

from senlin.drivers import base
from senlin.tests.drivers.openstack import sdk


class MistralClient(base.DriverBase):
    '''Fake mistral V2 driver for test.'''

    def __init__(self, ctx):

        self.fake_workflow = {
            'created_at': '1970-01-01T00:00:00.000000',
            'definition': 'workflow_def',
            'id': 'ffaed25e-46f5-4089-8e20-b3b4722fd597',
            'input': {
                'cluster_id': '8c74607c-5a74-4490-9414-a3475b1926c2',
                'node_id': 'fba2cc5d-706f-4631-9577-3956048d13a2',
                'flavor_id': '1'
            },
            'name': "cluster-coldmigration",
            'project_id': 'a7eb669e9819420ea4bd1453e672c0a7',
            'scope': 'private',
            'tags': [
                'large',
                'expensive'
            ],
            'updated_at': '1970-01-01T00:00:00.000000',
        }

        self.fake_workflow_create = {
            'scope': 'private',
            'id': 'ffaed25e-46f5-4089-8e20-b3b4722fd597',
            'definition': 'workflow_def',
        }

        self.fake_execution_create = {
            'id': 'ffaed25e-46f5-4089-8e20-b3b4722fd597',
            'workflow_name': 'cluster-coldmigration',
            'input': {
                'cluster_id': '8c74607c-5a74-4490-9414-a3475b1926c2',
                'node_id': 'fba2cc5d-706f-4631-9577-3956048d13a2',
                'flavor_id': '1'
            }
        }

    def wait_for_execution(self, execution, status='SUCCESS',
                           failures=['ERROR'], interval=2,
                           timeout=None):
        return

    def workflow_find(self, name_or_id, ignore_missing=True):
        return sdk.FakeResourceObject(self.fake_workflow)

    def workflow_delete(self, workflow, ignore_missing=True):
        return

    def execution_delete(self, execution, ignore_missing=True):
        return

    def workflow_create(self, definition, scope):
        self.fake_workflow_create['id'] = uuidutils.generate_uuid()
        return sdk.FakeResourceObject(self.fake_workflow_create)

    def execution_create(self, name, inputs):
        self.fake_execution_create['id'] = uuidutils.generate_uuid()
        return sdk.FakeResourceObject(self.fake_execution_create)
