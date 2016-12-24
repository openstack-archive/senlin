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

from senlin.objects.requests import profile_type as vorp
from senlin.tests.unit.common import base as test_base


class TestProfileTypeGet(test_base.SenlinTestCase):

    def test_profile_type_get(self):
        sot = vorp.ProfileTypeGetRequest(type_name='foo')

        self.assertEqual('foo', sot.type_name)

    def test_profile_type_to_primitive(self):
        sot = vorp.ProfileTypeGetRequest(type_name='foo')
        res = sot.obj_to_primitive()

        self.assertIn('type_name', res['senlin_object.changes'])
        self.assertEqual(u'foo', res['senlin_object.data']['type_name'])
        self.assertEqual('ProfileTypeGetRequest', res['senlin_object.name'])
        self.assertEqual('senlin', res['senlin_object.namespace'])
        self.assertEqual('1.0', res['senlin_object.version'])


class TestProfileTypeList(test_base.SenlinTestCase):

    def test_profile_type_list_to_primitive(self):
        sot = vorp.ProfileTypeListRequest()
        res = sot.obj_to_primitive()

        self.assertEqual({}, res['senlin_object.data'])
        self.assertEqual('ProfileTypeListRequest', res['senlin_object.name'])
        self.assertEqual('senlin', res['senlin_object.namespace'])
        self.assertEqual('1.0', res['senlin_object.version'])


class TestProfileTypeOpList(test_base.SenlinTestCase):

    def test_profile_type_get(self):
        sot = vorp.ProfileTypeOpListRequest(type_name='foo')

        self.assertEqual('foo', sot.type_name)

    def test_profile_type_op_list_to_primitive(self):
        sot = vorp.ProfileTypeOpListRequest(type_name='foo')
        res = sot.obj_to_primitive()

        self.assertIn('type_name', res['senlin_object.changes'])
        self.assertEqual(u'foo', res['senlin_object.data']['type_name'])
        self.assertEqual('ProfileTypeOpListRequest', res['senlin_object.name'])
        self.assertEqual('senlin', res['senlin_object.namespace'])
        self.assertEqual('1.0', res['senlin_object.version'])
