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

import mock
from oslo_config import cfg

from senlin.drivers.openstack import keystone_v3 as kv3
from senlin.drivers.openstack import sdk
from senlin.tests.unit.common import base
from senlin.tests.unit.common import utils


@mock.patch.object(sdk, 'create_connection')
class TestKeystoneV3(base.SenlinTestCase):

    def setUp(self):
        super(TestKeystoneV3, self).setUp()

        self.ctx = utils.dummy_context()
        self.conn = mock.Mock()

    def test_init(self, mock_create):
        mock_create.return_value = self.conn
        kc = kv3.KeystoneClient({'k': 'v'})

        mock_create.assert_called_once_with({'k': 'v'})
        self.assertEqual(self.conn, kc.conn)
        self.assertEqual(self.conn.session, kc.session)

    def test_trust_list(self, mock_create):
        self.conn.identity.trusts.return_value = ('foo', 'bar')
        mock_create.return_value = self.conn
        kc = kv3.KeystoneClient({'k': 'v'})

        res = kc.trust_list(p1='v1', p2='v2')

        self.assertEqual(['foo', 'bar'], res)
        self.conn.identity.trusts.assert_called_once_with(p1='v1', p2='v2')

    def test_trust_delete(self, mock_create):
        mock_create.return_value = self.conn
        kc = kv3.KeystoneClient({'k': 'v'})

        res = kc.trust_delete('value')

        self.assertIsNone(res)
        self.conn.identity.delete_trust.assert_called_once_with(
            'value', ignore_missing=True)

    def test_user_get(self, mock_create):
        self.conn.identity.find_user.return_value = 'user1'
        mock_create.return_value = self.conn
        kc = kv3.KeystoneClient({'k': 'v'})

        res = kc.user_get('user_id_or_name')

        self.assertEqual('user1', res)
        self.conn.identity.find_user.assert_called_once_with(
            'user_id_or_name', ignore_missing=False)

    def test_endpoint_get(self, mock_create):
        self.conn.identity.endpoints.return_value = ['fake_endpoint']
        mock_create.return_value = self.conn
        kc = kv3.KeystoneClient({'k': 'v'})

        res = kc.endpoint_get('FAKE_ID')

        self.assertEqual('fake_endpoint', res)
        self.conn.identity.endpoints.assert_called_once_with(
            service_id='FAKE_ID')
        self.conn.reset_mock()

        # with region
        res = kc.endpoint_get('FAKE_ID', 'FAKE_REGION')

        self.assertEqual('fake_endpoint', res)
        self.conn.identity.endpoints.assert_called_once_with(
            service_id='FAKE_ID', region='FAKE_REGION')
        self.conn.reset_mock()

        # with interface
        res = kc.endpoint_get('FAKE_ID', None, 'public')

        self.assertEqual('fake_endpoint', res)
        self.conn.identity.endpoints.assert_called_once_with(
            service_id='FAKE_ID', interface='public')
        self.conn.reset_mock()

        # returning None
        self.conn.identity.endpoints.return_value = []

        res = kc.endpoint_get('FAKE_ID')

        self.assertIsNone(res)
        self.conn.identity.endpoints.assert_called_once_with(
            service_id='FAKE_ID')

    def test_service_get(self, mock_create):
        svc = mock.Mock()
        self.conn.identity.services.return_value = svc
        mock_create.return_value = self.conn

        kc = kv3.KeystoneClient({'k': 'v'})

        res = kc.service_get('clustering')

        self.assertEqual(svc, res)
        self.conn.identity.services.assert_called_once_with(type='clustering')

    def test_trust_get_by_trustor(self, mock_create):
        trust1 = mock.Mock()
        trust1.trustee_user_id = 'USER_A_ID'
        trust1.project_id = 'PROJECT_ID_1'

        trust2 = mock.Mock()
        trust2.trustee_user_id = 'USER_B_ID'
        trust2.project_id = 'PROJECT_ID_1'

        trust3 = mock.Mock()
        trust3.trustee_user_id = 'USER_A_ID'
        trust3.project_id = 'PROJECT_ID_2'

        self.conn.identity.trusts.return_value = [trust1, trust2, trust3]
        mock_create.return_value = self.conn
        kc = kv3.KeystoneClient({'k': 'v'})

        # no trustee/projec filter, matching 1st
        res = kc.trust_get_by_trustor('USER_A')
        self.assertEqual(trust1, res)

        # trustee specified, matching 2nd
        res = kc.trust_get_by_trustor('USER_A', 'USER_B_ID')
        self.assertEqual(trust2, res)

        # project specified, matching 3rd
        res = kc.trust_get_by_trustor('USER_A', project='PROJECT_ID_2')
        self.assertEqual(trust3, res)

        # both trustee and project specified, matching 3rd
        res = kc.trust_get_by_trustor('USER_A', 'USER_A_ID', 'PROJECT_ID_2')
        self.assertEqual(trust3, res)

        # No matching record found
        res = kc.trust_get_by_trustor('USER_A', 'USER_C_ID')
        self.assertIsNone(res)

        get_calls = [mock.call(trustor_user_id='USER_A')]
        self.conn.identity.trusts.assert_has_calls(get_calls * 5)

    def test_trust_create(self, mock_create):
        self.conn.identity.create_trust.return_value = 'new_trust'
        mock_create.return_value = self.conn
        kc = kv3.KeystoneClient({'k': 'v'})

        # default
        res = kc.trust_create('ID_JOHN', 'ID_DOE', 'PROJECT_ID')

        self.assertEqual('new_trust', res)
        self.conn.identity.create_trust.assert_called_once_with(
            trustor_user_id='ID_JOHN', trustee_user_id='ID_DOE',
            project_id='PROJECT_ID', impersonation=True,
            allow_redelegation=True, roles=[])
        self.conn.reset_mock()

        # with roles
        res = kc.trust_create('ID_JOHN', 'ID_DOE', 'PROJECT_ID',
                              ['r1', 'r2'])

        self.assertEqual('new_trust', res)
        self.conn.identity.create_trust.assert_called_once_with(
            trustor_user_id='ID_JOHN', trustee_user_id='ID_DOE',
            project_id='PROJECT_ID', impersonation=True,
            allow_redelegation=True,
            roles=[{'name': 'r1'}, {'name': 'r2'}])
        self.conn.reset_mock()

        # impersonation
        res = kc.trust_create('ID_JOHN', 'ID_DOE', 'PROJECT_ID',
                              impersonation=False)

        self.assertEqual('new_trust', res)
        self.conn.identity.create_trust.assert_called_once_with(
            trustor_user_id='ID_JOHN', trustee_user_id='ID_DOE',
            project_id='PROJECT_ID', impersonation=False,
            allow_redelegation=True, roles=[])
        self.conn.reset_mock()

    def test_region_list(self, mock_create):
        self.conn.identity.regions.return_value = ['fake_region']
        mock_create.return_value = self.conn
        kc = kv3.KeystoneClient({'k': 'v'})

        res = kc.region_list(p1='v1', p2='v2')

        self.assertEqual(['fake_region'], res)
        self.conn.identity.regions.assert_called_once_with(p1='v1', p2='v2')

    @mock.patch.object(sdk, 'authenticate')
    def test_get_token(self, mock_auth, mock_create):
        access_info = {'token': '123', 'user_id': 'abc', 'project_id': 'xyz'}
        mock_auth.return_value = access_info

        token = kv3.KeystoneClient.get_token(key='value')

        mock_auth.assert_called_once_with(key='value')
        self.assertEqual('123', token)

    @mock.patch.object(sdk, 'authenticate')
    def test_get_user_id(self, mock_auth, mock_create):
        access_info = {'token': '123', 'user_id': 'abc', 'project_id': 'xyz'}
        mock_auth.return_value = access_info

        user_id = kv3.KeystoneClient.get_user_id(key='value')

        mock_auth.assert_called_once_with(key='value')
        self.assertEqual('abc', user_id)

    def test_get_service_credentials(self, mock_create):
        cfg.CONF.set_override('auth_url', 'FAKE_URL', group='authentication',
                              enforce_type=True)
        cfg.CONF.set_override('service_username', 'FAKE_USERNAME',
                              group='authentication', enforce_type=True)
        cfg.CONF.set_override('service_password', 'FAKE_PASSWORD',
                              group='authentication', enforce_type=True)
        cfg.CONF.set_override('service_project_name', 'FAKE_PROJECT',
                              group='authentication', enforce_type=True)
        cfg.CONF.set_override('service_user_domain', 'FAKE_DOMAIN_1',
                              group='authentication', enforce_type=True)
        cfg.CONF.set_override('service_project_domain', 'FAKE_DOMAIN_2',
                              group='authentication', enforce_type=True)
        expected = {
            'auth_url': 'FAKE_URL',
            'username': 'FAKE_USERNAME',
            'password': 'FAKE_PASSWORD',
            'project_name': 'FAKE_PROJECT',
            'user_domain_name': 'FAKE_DOMAIN_1',
            'project_domain_name': 'FAKE_DOMAIN_2'
        }

        actual = kv3.KeystoneClient.get_service_credentials()

        self.assertEqual(expected, actual)

        new_expected = copy.copy(expected)
        new_expected['key1'] = 'value1'
        new_expected['password'] = 'NEW_PASSWORD'

        actual = kv3.KeystoneClient.get_service_credentials(
            key1='value1', password='NEW_PASSWORD')

        self.assertEqual(new_expected, actual)

    def test_validate_regions(self, mock_create):
        self.conn.identity.regions.return_value = [
            {'id': 'R1', 'parent_region_id': None},
            {'id': 'R2', 'parent_region_id': None},
            {'id': 'R3', 'parent_region_id': 'R1'},
        ]
        mock_create.return_value = self.conn

        kc = kv3.KeystoneClient({'k': 'v'})

        res = kc.validate_regions(['R1', 'R4'])

        self.assertIn('R1', res)
        self.assertNotIn('R4', res)

        res = kc.validate_regions([])
        self.assertEqual([], res)
