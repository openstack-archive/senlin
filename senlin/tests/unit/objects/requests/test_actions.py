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

from senlin.objects.requests import actions
from senlin.tests.unit.common import base as test_base


class TestActionList(test_base.SenlinTestCase):

    def test_action_list_request_body_full(self):
        params = {
            'name': ['node_create_12345678'],
            'action': ['NODE_CREATE'],
            'target': ['0df0931b-e251-4f2e-8719-4effda3627bb'],
            'status': ['READY'],
            'limit': 5,
            'marker': 'f1ed0d50-7651-4599-a8cb-c86e9c7123f6',
            'sort': 'name:asc',
            'project_safe': False,
        }
        sot = actions.ActionListRequest(**params)
        self.assertEqual(['node_create_12345678'], sot.name)
        self.assertEqual(['NODE_CREATE'], sot.action)
        self.assertEqual(['0df0931b-e251-4f2e-8719-4effda3627bb'], sot.target)
        self.assertEqual(['READY'], sot.status)
        self.assertEqual(5, sot.limit)
        self.assertEqual('f1ed0d50-7651-4599-a8cb-c86e9c7123f6', sot.marker)
        self.assertEqual('name:asc', sot.sort)
        self.assertFalse(sot.project_safe)

    def test_action_list_request_body_default(self):
        sot = actions.ActionListRequest()
        sot.obj_set_defaults()
        self.assertTrue(sot.project_safe)


class TestActionGet(test_base.SenlinTestCase):

    body = {
        'identity': 'test-action'
    }

    def test_action_get_request(self):
        sot = actions.ActionGetRequest(**self.body)
        self.assertEqual('test-action', sot.identity)
