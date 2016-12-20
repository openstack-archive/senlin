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

from senlin.objects.requests import credentials
from senlin.tests.unit.common import base as test_base


class TestCredentialCreate(test_base.SenlinTestCase):

    body = {
        'cred': {
            'openstack': {
                'trust': 'f49419fd-e48b-4e8c-a201-30eb4560acf4'
            }
        }
    }

    def test_credential_create_request(self):
        sot = credentials.CredentialCreateRequest(**self.body)
        self.assertEqual(self.body['cred'], sot.cred)
        sot.obj_set_defaults()
        self.assertEqual({}, sot.attrs)

    def test_credential_create_request_full(self):
        body = copy.deepcopy(self.body)
        body['attrs'] = {'foo': 'bar'}
        sot = credentials.CredentialCreateRequest(**body)
        self.assertEqual(body['cred'], sot.cred)
        self.assertEqual(body['attrs'], sot.attrs)


class TestCredentialGet(test_base.SenlinTestCase):

    body = {
        'user': 'test-user',
        'project': 'test-project'
    }

    def test_credential_get_request(self):
        sot = credentials.CredentialGetRequest(**self.body)
        self.assertEqual('test-user', sot.user)
        self.assertEqual('test-project', sot.project)
        sot.obj_set_defaults()
        self.assertEqual({}, sot.query)

    def test_credential_get_request_full(self):
        body = copy.deepcopy(self.body)
        body['query'] = {'foo': 'bar'}
        sot = credentials.CredentialGetRequest(**body)
        self.assertEqual('test-user', sot.user)
        self.assertEqual('test-project', sot.project)
        self.assertEqual({'foo': 'bar'}, sot.query)


class TestCredentialUpdate(test_base.SenlinTestCase):

    body = {
        'cred': {
            'openstack': {
                'trust': 'f49419fd-e48b-4e8c-a201-30eb4560acf4'
            }
        }
    }

    def test_credential_update_request(self):
        sot = credentials.CredentialUpdateRequest(**self.body)
        self.assertEqual(self.body['cred'], sot.cred)
        sot.obj_set_defaults()
        self.assertEqual({}, sot.attrs)
