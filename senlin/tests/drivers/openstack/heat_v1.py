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
from senlin.tests.drivers.openstack import sdk


class HeatClient(base.DriverBase):
    '''Heat V1 driver.'''

    def __init__(self, params):
        super(HeatClient, self).__init__(params)
        self.fake_stack_create = {
            "id": "3095aefc-09fb-4bc7-b1f0-f21a304e864c",
            "links": [
                {
                    "href": " ",
                    "rel": "self"
                }
            ]
        }

        self.fake_stack_get = {
            "capabilities": [],
            "creation_time": "2014-06-03T20:59:46Z",
            "description": "sample stack",
            "disable_rollback": True,
            "id": "3095aefc-09fb-4bc7-b1f0-f21a304e864c",
            "links": [
                {
                    "href": " ",
                    "rel": "self"
                }
            ],
            "notification_topics": [],
            "outputs": [],
            "parameters": {
                "OS::project_id": "3ab5b02f-a01f-4f95-afa1-e254afc4a435",
                "OS::stack_id": "3095aefc-09fb-4bc7-b1f0-f21a304e864c",
                "OS::stack_name": "simple_stack"
            },
            "stack_name": "simple_stack",
            "stack_owner": "simple_username",
            "stack_status": "CREATE_COMPLETE",
            "stack_status_reason": "Stack CREATE completed successfully",
            "template_description": "sample stack",
            "stack_user_project_id": "65728b74-cfe7-4f17-9c15-11d4f686e591",
            "timeout_mins": "",
            "updated_time": "",
            "parent": "",
            "tags": "",
            "status": "CREATE_COMPLETE"
        }

    def stack_create(self, **params):
        return sdk.FakeResourceObject(self.fake_stack_create)

    def stack_get(self, stack_id):
        return sdk.FakeResourceObject(self.fake_stack_get)

    def stack_find(self, name_or_id):
        return sdk.FakeResourceObject(self.fake_stack_get)

    def stack_update(self, stack_id, **params):
        self.fake_stack_get["status"] = "UPDATE_COMPLETE"
        return sdk.FakeResourceObject(self.fake_stack_get)

    def stack_delete(self, stack_id, ignore_missing=True):
        return

    def wait_for_stack_delete(self, stack_id, timeout=None):
        return
