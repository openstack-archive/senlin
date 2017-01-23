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
import copy

from oslo_serialization import jsonutils
from senlin.objects.requests import profiles
from senlin.tests.unit.common import base as test_base


class TestProfileCreate(test_base.SenlinTestCase):

    spec = {
        'type': 'os.nova.server',
        'version': '1.0',
        'properties': {
            'name': 'FAKE_SERVER_NAME',
            'flavor': 'FAKE_FLAVOR',
            'image': 'FAKE_IMAGE',
            'key_name': 'FAKE_KEYNAME',
            'networks': [{'network': 'FAKE_NET'}],
            'user_data': 'FAKE_USER_DATA'
        }
    }

    def test_profile_create_body(self):
        spec = copy.deepcopy(self.spec)
        sot = profiles.ProfileCreateRequestBody(name='foo', spec=spec,
                                                metadata={'x': 'y'})
        self.assertEqual('foo', sot.name)
        self.assertEqual({'x': 'y'}, sot.metadata)
        self.assertEqual(u'os.nova.server', sot.spec['type'])
        self.assertEqual(u'1.0', sot.spec['version'])

    def test_profile_create_request(self):
        spec = copy.deepcopy(self.spec)
        body = profiles.ProfileCreateRequestBody(name='foo', spec=spec,
                                                 metadata={'x': 'y'})
        sot = profiles.ProfileCreateRequest(profile=body)
        self.assertIsInstance(sot.profile, profiles.ProfileCreateRequestBody)

    def test_request_body_to_primitive(self):
        spec = copy.deepcopy(self.spec)
        sot = profiles.ProfileCreateRequestBody(name='test-profile',
                                                spec=spec,
                                                metadata={'x': 'y'})
        self.assertEqual('test-profile', sot.name)
        self.assertEqual({'x': 'y'}, sot.metadata)

        res = sot.obj_to_primitive()
        # request body
        self.assertEqual('ProfileCreateRequestBody', res['senlin_object.name'])
        self.assertEqual('1.0', res['senlin_object.version'])
        self.assertEqual('senlin', res['senlin_object.namespace'])
        self.assertIn('name', res['senlin_object.changes'])
        self.assertIn('spec', res['senlin_object.changes'])
        self.assertIn('metadata', res['senlin_object.changes'])
        # spec
        data = res['senlin_object.data']
        self.assertEqual(u'test-profile', data['name'])
        self.assertEqual(u'{"x": "y"}', data['metadata'])
        # spec data
        spec_data = jsonutils.loads(data['spec'])
        self.assertEqual(u'os.nova.server', spec_data['type'])
        self.assertEqual(u'1.0', spec_data['version'])

    def test_request_to_primitive(self):
        spec = copy.deepcopy(self.spec)
        body = profiles.ProfileCreateRequestBody(name='test-profile',
                                                 spec=spec,
                                                 metadata={'x': 'y'})
        sot = profiles.ProfileCreateRequest(profile=body)
        self.assertIsInstance(sot.profile, profiles.ProfileCreateRequestBody)
        self.assertEqual('test-profile', sot.profile.name)
        self.assertEqual({'x': 'y'}, sot.profile.metadata)

        # request
        res = sot.obj_to_primitive()
        self.assertIn('profile', res['senlin_object.changes'])
        self.assertEqual('ProfileCreateRequest', res['senlin_object.name'])
        self.assertEqual('senlin', res['senlin_object.namespace'])
        self.assertEqual('1.0', res['senlin_object.version'])

        # request body
        data = res['senlin_object.data']['profile']
        self.assertEqual('ProfileCreateRequestBody',
                         data['senlin_object.name'])
        self.assertEqual('senlin', data['senlin_object.namespace'])
        self.assertEqual('1.0', data['senlin_object.version'])
        self.assertIn('name', data['senlin_object.changes'])
        self.assertIn('spec', data['senlin_object.changes'])
        self.assertIn('metadata', data['senlin_object.changes'])

        # spec
        pd = data['senlin_object.data']
        self.assertEqual(u'test-profile', pd['name'])

        spec_data = jsonutils.loads(pd['spec'])
        self.assertEqual(u'os.nova.server', spec_data['type'])
        self.assertEqual(u'1.0', spec_data['version'])


class TestProfileList(test_base.SenlinTestCase):

    def test_profile_list_request_body_full(self):
        params = {
            'name': ['p1'],
            'type': ['os.nova.server-1.0'],
            'limit': 2,
            'marker': 'd8d7dd1e-afd8-4921-83b2-c4ce73b1cb22',
            'sort': 'name:asc',
            'project_safe': False
        }
        sot = profiles.ProfileListRequest(**params)
        self.assertEqual(['p1'], sot.name)
        self.assertEqual(['os.nova.server-1.0'], sot.type)
        self.assertEqual(2, sot.limit)
        self.assertEqual('d8d7dd1e-afd8-4921-83b2-c4ce73b1cb22',
                         sot.marker)
        self.assertEqual('name:asc', sot.sort)
        self.assertFalse(sot.project_safe)


class TestProfileGet(test_base.SenlinTestCase):

    def test_profile_get(self):
        sot = profiles.ProfileGetRequest(identity='FAKE_ID')
        self.assertEqual('FAKE_ID', sot.identity)


class TestProfileUpdate(test_base.SenlinTestCase):

    def test_profile_update_body(self):
        data = {'name': 'foo', 'metadata': {'aaa': 'bbb'}}
        sot = profiles.ProfileUpdateRequestBody(**data)
        self.assertEqual('foo', sot.name)
        self.assertEqual({'aaa': 'bbb'}, sot.metadata)

    def test_profile_update(self):
        data = {'name': 'foo', 'metadata': {'aaa': 'bbb'}}
        body = profiles.ProfileUpdateRequestBody(**data)

        request = {
            'identity': 'pid',
            'profile': body
        }
        sot = profiles.ProfileUpdateRequest(**request)
        self.assertEqual('pid', sot.identity)
        self.assertIsInstance(sot.profile, profiles.ProfileUpdateRequestBody)

    def test_profile_data_to_primitive(self):
        data = {'name': 'foo', 'metadata': {'aaa': 'bbb'}}
        sot = profiles.ProfileUpdateRequestBody(**data)
        res = sot.obj_to_primitive()

        self.assertIn('name', res['senlin_object.changes'])
        self.assertIn('metadata', res['senlin_object.changes'])
        self.assertEqual('foo', res['senlin_object.data']['name'])
        self.assertEqual('{"aaa": "bbb"}',
                         res['senlin_object.data']['metadata'])
        self.assertEqual('ProfileUpdateRequestBody', res['senlin_object.name'])
        self.assertEqual('senlin', res['senlin_object.namespace'])
        self.assertEqual('1.0', res['senlin_object.version'])

    def test_request_to_primitive(self):
        data = {'name': 'foo', 'metadata': {'aaa': 'bbb'}}
        body = profiles.ProfileUpdateRequestBody(**data)

        request = {
            'identity': 'pid',
            'profile': body
        }
        sot = profiles.ProfileUpdateRequest(**request)
        res = sot.obj_to_primitive()

        self.assertIn('identity', res['senlin_object.changes'])
        self.assertEqual(u'pid', res['senlin_object.data']['identity'])
        self.assertEqual('ProfileUpdateRequest', res['senlin_object.name'])
        self.assertEqual('senlin', res['senlin_object.namespace'])
        self.assertEqual('1.0', res['senlin_object.version'])


class TestProfileValidate(test_base.SenlinTestCase):
    spec = {
        'type': 'os.nova.server',
        'version': '1.0',
        'properties': {
            'name': 'FAKE_SERVER_NAME',
            'flavor': 'FAKE_FLAVOR',
            'image': 'FAKE_IMAGE',
            'key_name': 'FAKE_KEYNAME',
            'networks': [{'network': 'FAKE_NET'}],
            'user_data': 'FAKE_USER_DATA'
        }
    }

    def test_validate_request_body(self):
        spec = copy.deepcopy(self.spec)
        body = profiles.ProfileValidateRequestBody(spec=spec)

        self.assertEqual('os.nova.server', body.spec['type'])
        self.assertEqual('1.0', body.spec['version'])

    def test_validate_request(self):
        spec = copy.deepcopy(self.spec)
        body = profiles.ProfileValidateRequestBody(spec=spec)

        sot = profiles.ProfileValidateRequest(profile=body)
        self.assertIsInstance(sot.profile, profiles.ProfileValidateRequestBody)

    def test_request_body_to_primitive(self):
        spec = copy.deepcopy(self.spec)
        body = profiles.ProfileValidateRequestBody(spec=spec)
        res = body.obj_to_primitive()

        self.assertIn('spec', res['senlin_object.changes'])
        self.assertEqual(
            'ProfileValidateRequestBody', res['senlin_object.name'])
        self.assertEqual('senlin', res['senlin_object.namespace'])
        self.assertEqual('1.0', res['senlin_object.version'])

        data = jsonutils.loads(res['senlin_object.data']['spec'])
        self.assertEqual(u'os.nova.server', data['type'])
        self.assertEqual(u'1.0', data['version'])

    def test_request_to_primitive(self):
        spec = copy.deepcopy(self.spec)
        body = profiles.ProfileValidateRequestBody(spec=spec)

        sot = profiles.ProfileValidateRequest(profile=body)
        res = sot.obj_to_primitive()

        self.assertIn('profile', res['senlin_object.changes'])
        self.assertEqual('ProfileValidateRequest', res['senlin_object.name'])
        self.assertEqual('senlin', res['senlin_object.namespace'])
        self.assertEqual('1.0', res['senlin_object.version'])

        profile_body = res['senlin_object.data']['profile']
        self.assertIn('spec', profile_body['senlin_object.changes'])

        self.assertEqual(
            'ProfileValidateRequestBody', profile_body['senlin_object.name'])
        self.assertEqual('senlin', profile_body['senlin_object.namespace'])
        self.assertEqual('1.0', profile_body['senlin_object.version'])

        data = jsonutils.loads(profile_body['senlin_object.data']['spec'])
        self.assertEqual(u'os.nova.server', data['type'])
        self.assertEqual(u'1.0', data['version'])


class TestProfileDelete(test_base.SenlinTestCase):

    def test_profile_delete(self):
        sot = profiles.ProfileDeleteRequest(identity='FAKE_ID')

        self.assertEqual('FAKE_ID', sot.identity)
