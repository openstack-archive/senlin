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

    body = {
        'name': 'test-profile',
        'spec': spec,
        'metadata': {"x": "y"}
    }

    def test_profile_create_spec(self):
        properties = {
            'name': 'FAKE_SERVER_NAME',
            'flavor': 'FAKE_FLAVOR',
            'image': 'FAKE_IMAGE',
            'key_name': 'FAKE_KEYNAME',
            'networks': [{'network': 'FAKE_NET'}],
            'user_data': 'FAKE_USER_DATA'
        }
        sot = profiles.ProfileSpec(**self.spec)
        self.assertEqual(properties, sot.properties)
        self.assertEqual('os.nova.server', sot.type)
        self.assertEqual('1.0', sot.version)

    def test_profile_create_body(self):
        spec = profiles.ProfileSpec(**self.spec)
        body = {
            'name': 'foo',
            'spec': spec,
            'metadata': {'x': 'y'},
        }
        sot = profiles.ProfileCreateRequestBody(**body)
        self.assertIsInstance(sot.spec, profiles.ProfileSpec)
        self.assertEqual('foo', sot.name)
        self.assertEqual({'x': 'y'}, sot.metadata)

    def test_profile_create_request(self):
        spec = profiles.ProfileSpec(**self.spec)
        body = {
            'name': 'foo',
            'spec': spec,
            'metadata': {'x': 'y'},
        }
        profile = profiles.ProfileCreateRequestBody(**body)
        request = {'profile': profile}
        sot = profiles.ProfileCreateRequest(**request)
        self.assertIsInstance(sot.profile, profiles.ProfileCreateRequestBody)

    def test_request_spec_to_primitice(self):
        spec = copy.deepcopy(self.spec)
        sot = profiles.ProfileSpec(**spec)
        res = sot.obj_to_primitive()
        data = res['senlin_object.data']

        self.assertEqual('ProfileSpec', res['senlin_object.name'])
        self.assertEqual('senlin', res['senlin_object.namespace'])
        self.assertEqual('1.0', res['senlin_object.version'])

        self.assertIn('version', res['senlin_object.changes'])
        self.assertIn('type', res['senlin_object.changes'])
        self.assertIn('properties', res['senlin_object.changes'])

        properties = jsonutils.loads(data['properties'])
        self.assertEqual(u'os.nova.server', data['type'])
        self.assertEqual(u'1.0', data['version'])
        self.assertEqual('FAKE_SERVER_NAME', properties['name'])
        self.assertEqual('FAKE_FLAVOR', properties['flavor'])
        self.assertEqual('FAKE_IMAGE', properties['image'])
        self.assertEqual('FAKE_KEYNAME', properties['key_name'])
        self.assertEqual([{'network': 'FAKE_NET'}], properties['networks'])
        self.assertEqual('FAKE_USER_DATA', properties['user_data'])

    def test_request_body_to_primitive(self):
        spec = profiles.ProfileSpec(**self.spec)
        request = {
            'name': 'test-profile',
            'spec': spec,
            'metadata': {'x': 'y'}
        }
        sot = profiles.ProfileCreateRequestBody(**request)
        self.assertEqual('test-profile', sot.name)
        self.assertEqual({'x': 'y'}, sot.metadata)
        self.assertIsInstance(sot.spec, profiles.ProfileSpec)

        res = sot.obj_to_primitive()
        data = res['senlin_object.data']['spec']
        spec_data = data['senlin_object.data']
        # request body
        self.assertEqual('ProfileCreateRequestBody', res['senlin_object.name'])
        self.assertEqual('1.0', res['senlin_object.version'])
        self.assertEqual('senlin', res['senlin_object.namespace'])
        self.assertEqual(u'test-profile', res['senlin_object.data']['name'])
        self.assertEqual(u'{"x": "y"}', res['senlin_object.data']['metadata'])
        self.assertIn('name', res['senlin_object.changes'])
        self.assertIn('spec', res['senlin_object.changes'])
        self.assertIn('metadata', res['senlin_object.changes'])
        # spec
        self.assertEqual('ProfileSpec', data['senlin_object.name'])
        self.assertEqual('1.0', data['senlin_object.version'])
        self.assertEqual('senlin', data['senlin_object.namespace'])
        self.assertIn('version', data['senlin_object.changes'])
        self.assertIn('type', data['senlin_object.changes'])
        self.assertIn('properties', data['senlin_object.changes'])
        # spec data
        self.assertEqual(u'os.nova.server', spec_data['type'])
        self.assertEqual(u'1.0', spec_data['version'])

    def test_request_to_primitive(self):
        spec = profiles.ProfileSpec(**self.spec)
        body = {
            'name': 'test-profile',
            'spec': spec,
            'metadata': {'x': 'y'}
        }
        body = profiles.ProfileCreateRequestBody(**body)
        request = {'profile': body}
        sot = profiles.ProfileCreateRequest(**request)
        self.assertIsInstance(sot.profile, profiles.ProfileCreateRequestBody)
        self.assertEqual('test-profile', sot.profile.name)

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

        pd = data['senlin_object.data']
        self.assertEqual(u'test-profile', pd['name'])

        pd_spec = pd['spec']
        self.assertIn('version', pd_spec['senlin_object.changes'])
        self.assertIn('type', pd_spec['senlin_object.changes'])
        self.assertIn('properties', pd_spec['senlin_object.changes'])
        self.assertEqual('ProfileSpec', pd_spec['senlin_object.name'])
        self.assertEqual('senlin', pd_spec['senlin_object.namespace'])
        self.assertEqual('1.0', pd_spec['senlin_object.version'])

        spec_data = pd_spec['senlin_object.data']
        self.assertEqual(u'os.nova.server', spec_data['type'])
        self.assertEqual(u'1.0', spec_data['version'])


class TestProfileList(test_base.SenlinTestCase):

    def test_profile_list_request_body_full(self):
        params = {
            'name': ['p1'],
            'type': ['os.nova.server-1.0'],
            'limit': 2,
            'marker': 'FAKE_ID',
            'sort': 'name:asc',
            'project_safe': False
        }
        sot = profiles.ProfileListRequest(**params)
        self.assertEqual(['p1'], sot.name)
        self.assertEqual(['os.nova.server-1.0'], sot.type)
        self.assertEqual(2, sot.limit)
        self.assertEqual('FAKE_ID', sot.marker)
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
        sot = profiles.ProfileSpec(**spec)

        self.assertEqual('os.nova.server', sot.type)
        self.assertEqual('1.0', sot.version)

    def test_validate_request(self):
        spec = copy.deepcopy(self.spec)
        profile = profiles.ProfileSpec(**spec)

        request = {'profile': profile}
        sot = profiles.ProfileValidateRequest(**request)
        self.assertIsInstance(sot.profile, profiles.ProfileSpec)

    def test_request_body_to_primitive(self):
        spec = copy.deepcopy(self.spec)
        sot = profiles.ProfileSpec(**spec)
        res = sot.obj_to_primitive()

        changes = res['senlin_object.changes']
        self.assertIn('version', changes)
        self.assertIn('type', changes)
        self.assertIn('properties', changes)
        self.assertEqual('ProfileSpec', res['senlin_object.name'])
        self.assertEqual('senlin', res['senlin_object.namespace'])
        self.assertEqual('1.0', res['senlin_object.version'])

        data = res['senlin_object.data']
        self.assertEqual(u'os.nova.server', data['type'])
        self.assertEqual(u'1.0', data['version'])

    def test_request_to_primitive(self):
        spec = copy.deepcopy(self.spec)
        profile = profiles.ProfileSpec(**spec)

        request = {'profile': profile}
        sot = profiles.ProfileValidateRequest(**request)
        res = sot.obj_to_primitive()

        self.assertIn('profile', res['senlin_object.changes'])
        self.assertEqual('ProfileValidateRequest', res['senlin_object.name'])
        self.assertEqual('senlin', res['senlin_object.namespace'])
        self.assertEqual('1.0', res['senlin_object.version'])

        pd = res['senlin_object.data']['profile']
        pd_change = pd['senlin_object.changes']
        self.assertIn('version', pd_change)
        self.assertIn('type', pd_change)
        self.assertIn('properties', pd_change)

        self.assertEqual('ProfileSpec', pd['senlin_object.name'])
        self.assertEqual('senlin', pd['senlin_object.namespace'])
        self.assertEqual('1.0', pd['senlin_object.version'])

        pd_data = pd['senlin_object.data']
        self.assertEqual(u'os.nova.server', pd_data['type'])
        self.assertEqual(u'1.0', pd_data['version'])


class TestProfileDelete(test_base.SenlinTestCase):

    def test_profile_delete(self):
        sot = profiles.ProfileDeleteRequest(identity='FAKE_ID')

        self.assertEqual('FAKE_ID', sot.identity)
