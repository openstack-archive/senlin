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

from senlin.drivers import base
from senlin.drivers import sdk


class MistralClient(base.DriverBase):
    '''Fake Mistral V2 driver.'''

    def __init__(self, params):
        self.fake_workflow = {}
        self.fake_execution = {}

    def workflow_create(self, definition, scope):
        return sdk.FakeResourceObject(self.fake_workflow)

    def workflow_delete(self, workflow, ignore_missing=True):
        return None

    def workflow_find(self, name_or_id, ignore_missing=True):
        return sdk.FakeResourceObject(self.fake_workflow)

    def execution_create(self, name, inputs):
        return sdk.FakeResourceObject(self.fake_execution)

    def execution_delete(self, execution, ignore_missing=True):
        return None

    def wait_for_execution(self, execution, status='SUCCESS',
                           failures=['ERROR'], interval=2,
                           timeout=None):
        return None
