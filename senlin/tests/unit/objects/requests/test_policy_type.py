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

from senlin.objects.requests import policy_type
from senlin.tests.unit.common import base as test_base


class TestPolicyTypeGet(test_base.SenlinTestCase):

    def test_policy_type_get(self):
        sot = policy_type.PolicyTypeGetRequest(type_name='Fake')

        self.assertEqual('Fake', sot.type_name)

    def test_policy_type_to_primitive(self):
        sot = policy_type.PolicyTypeGetRequest(type_name='Fake')

        res = sot.obj_to_primitive()

        self.assertIn('type_name', res['senlin_object.changes'])
        self.assertEqual(u'Fake', res['senlin_object.data']['type_name'])
        self.assertEqual('PolicyTypeGetRequest', res['senlin_object.name'])
        self.assertEqual('senlin', res['senlin_object.namespace'])
        self.assertEqual('1.0', res['senlin_object.version'])


class TestPolicyTypeList(test_base.SenlinTestCase):

    def test_policy_type_list_to_primitive(self):
        sot = policy_type.PolicyTypeListRequest()
        res = sot.obj_to_primitive()

        self.assertEqual({}, res['senlin_object.data'])
        self.assertEqual('PolicyTypeListRequest', res['senlin_object.name'])
        self.assertEqual('senlin', res['senlin_object.namespace'])
        self.assertEqual('1.0', res['senlin_object.version'])
