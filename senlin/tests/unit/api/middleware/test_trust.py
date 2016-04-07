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

import mock
import six

from senlin.api.middleware import trust
from senlin.common import context
from senlin.common import exception
from senlin.tests.unit.common import base
from senlin.tests.unit.common import utils


class TestTrustMiddleware(base.SenlinTestCase):

    def setUp(self):
        super(TestTrustMiddleware, self).setUp()
        self.context = utils.dummy_context()
        self.middleware = trust.TrustMiddleware(None)

    @mock.patch("senlin.rpc.client.EngineClient")
    def test__get_trust_already_exists(self, mock_rpc):
        x_cred = {'trust': 'FAKE_TRUST_ID'}
        x_rpc = mock.Mock()
        x_rpc.credential_get.return_value = x_cred
        mock_rpc.return_value = x_rpc

        result = self.middleware._get_trust(self.context)

        self.assertEqual('FAKE_TRUST_ID', result)
        mock_rpc.assert_called_once_with()
        x_rpc.credential_get.assert_called_once_with(self.context)

    @mock.patch.object(context, "get_service_context")
    @mock.patch("senlin.drivers.base.SenlinDriver")
    @mock.patch("senlin.rpc.client.EngineClient")
    def test__get_trust_bad(self, mock_rpc, mock_driver, mock_context):
        x_cred = {'foo': 'bar'}
        x_rpc = mock.Mock()
        x_rpc.credential_get.return_value = x_cred
        mock_rpc.return_value = x_rpc

        x_svc_cred = {'uid': 'FAKE_ID', 'passwd': 'FAKE_PASS'}
        mock_context.return_value = x_svc_cred
        x_admin_id = 'FAKE_ADMIN_ID'
        x_trust = mock.Mock(id='FAKE_TRUST_ID')
        mock_keystone = mock.Mock()
        mock_keystone.get_user_id.return_value = x_admin_id
        mock_keystone.trust_get_by_trustor.return_value = x_trust
        x_driver = mock.Mock()
        x_driver.identity.return_value = mock_keystone
        mock_driver.return_value = x_driver

        result = self.middleware._get_trust(self.context)

        self.assertEqual('FAKE_TRUST_ID', result)
        mock_rpc.assert_called_once_with()
        x_rpc.credential_get.assert_called_once_with(self.context)
        mock_driver.assert_called_once_with()
        x_driver.identity.assert_called_once_with({
            'auth_url': self.context.auth_url,
            'project_id': self.context.project,
            'user_id': self.context.user,
            'token': self.context.auth_token,
        })
        mock_context.assert_called_once_with()
        mock_keystone.get_user_id.assert_called_once_with(
            uid='FAKE_ID', passwd='FAKE_PASS')
        mock_keystone.trust_get_by_trustor.assert_called_once_with(
            self.context.user, 'FAKE_ADMIN_ID', self.context.project)
        x_rpc.credential_create.assert_called_once_with(
            self.context, 'FAKE_TRUST_ID')

    @mock.patch.object(context, "get_service_context")
    @mock.patch("senlin.drivers.base.SenlinDriver")
    @mock.patch("senlin.rpc.client.EngineClient")
    def test__get_trust_not_found(self, mock_rpc, mock_driver, mock_context):
        x_rpc = mock.Mock()
        x_rpc.credential_get.return_value = None
        mock_rpc.return_value = x_rpc

        x_svc_cred = {'uid': 'FAKE_ID', 'passwd': 'FAKE_PASS'}
        mock_context.return_value = x_svc_cred
        x_admin_id = 'FAKE_ADMIN_ID'
        x_trust = mock.Mock(id='FAKE_TRUST_ID')
        mock_keystone = mock.Mock()
        mock_keystone.get_user_id.return_value = x_admin_id
        mock_keystone.trust_get_by_trustor.return_value = x_trust
        x_driver = mock.Mock()
        x_driver.identity.return_value = mock_keystone
        mock_driver.return_value = x_driver

        result = self.middleware._get_trust(self.context)

        self.assertEqual('FAKE_TRUST_ID', result)
        mock_rpc.assert_called_once_with()
        x_rpc.credential_get.assert_called_once_with(self.context)
        mock_driver.assert_called_once_with()
        x_driver.identity.assert_called_once_with({
            'auth_url': self.context.auth_url,
            'project_id': self.context.project,
            'user_id': self.context.user,
            'token': self.context.auth_token,
        })
        mock_context.assert_called_once_with()
        mock_keystone.get_user_id.assert_called_once_with(
            uid='FAKE_ID', passwd='FAKE_PASS')
        mock_keystone.trust_get_by_trustor.assert_called_once_with(
            self.context.user, 'FAKE_ADMIN_ID', self.context.project)
        x_rpc.credential_create.assert_called_once_with(
            self.context, 'FAKE_TRUST_ID')

    @mock.patch.object(context, "get_service_context")
    @mock.patch("senlin.drivers.base.SenlinDriver")
    @mock.patch("senlin.rpc.client.EngineClient")
    def test__get_trust_do_create(self, mock_rpc, mock_driver, mock_context):
        x_rpc = mock.Mock()
        x_rpc.credential_get.return_value = None
        mock_rpc.return_value = x_rpc

        x_svc_cred = {'uid': 'FAKE_ID', 'passwd': 'FAKE_PASS'}
        mock_context.return_value = x_svc_cred
        x_admin_id = 'FAKE_ADMIN_ID'
        mock_keystone = mock.Mock()
        mock_keystone.get_user_id.return_value = x_admin_id
        x_trust = mock.Mock(id='FAKE_TRUST_ID')
        mock_keystone.trust_create.return_value = x_trust
        err = exception.InternalError(code=400, message='Boom')
        mock_keystone.trust_get_by_trustor.side_effect = err
        x_driver = mock.Mock()
        x_driver.identity.return_value = mock_keystone
        mock_driver.return_value = x_driver

        result = self.middleware._get_trust(self.context)

        self.assertEqual('FAKE_TRUST_ID', result)
        mock_rpc.assert_called_once_with()
        x_rpc.credential_get.assert_called_once_with(self.context)
        mock_driver.assert_called_once_with()
        x_driver.identity.assert_called_once_with({
            'auth_url': self.context.auth_url,
            'project_id': self.context.project,
            'user_id': self.context.user,
            'token': self.context.auth_token,
        })
        mock_context.assert_called_once_with()
        mock_keystone.get_user_id.assert_called_once_with(
            uid='FAKE_ID', passwd='FAKE_PASS')
        mock_keystone.trust_get_by_trustor.assert_called_once_with(
            self.context.user, 'FAKE_ADMIN_ID', self.context.project)
        mock_keystone.trust_create.assert_called_once_with(
            self.context.user, 'FAKE_ADMIN_ID', self.context.project,
            self.context.roles)
        x_rpc.credential_create.assert_called_once_with(
            self.context, 'FAKE_TRUST_ID')

    @mock.patch.object(context, "get_service_context")
    @mock.patch("senlin.drivers.base.SenlinDriver")
    @mock.patch("senlin.rpc.client.EngineClient")
    def test__get_trust_fatal(self, mock_rpc, mock_driver, mock_context):
        x_rpc = mock.Mock()
        x_rpc.credential_get.return_value = None
        mock_rpc.return_value = x_rpc

        x_svc_cred = {'uid': 'FAKE_ID', 'passwd': 'FAKE_PASS'}
        mock_context.return_value = x_svc_cred
        x_admin_id = 'FAKE_ADMIN_ID'
        mock_keystone = mock.Mock()
        mock_keystone.get_user_id.return_value = x_admin_id
        err = exception.InternalError(code=500, message='Boom')
        mock_keystone.trust_get_by_trustor.side_effect = err
        x_driver = mock.Mock()
        x_driver.identity.return_value = mock_keystone
        mock_driver.return_value = x_driver

        ex = self.assertRaises(exception.InternalError,
                               self.middleware._get_trust,
                               self.context)

        self.assertEqual('Boom', six.text_type(ex))
        mock_rpc.assert_called_once_with()
        x_rpc.credential_get.assert_called_once_with(self.context)
        mock_driver.assert_called_once_with()
        x_driver.identity.assert_called_once_with({
            'auth_url': self.context.auth_url,
            'project_id': self.context.project,
            'user_id': self.context.user,
            'token': self.context.auth_token,
        })
        mock_context.assert_called_once_with()
        mock_keystone.get_user_id.assert_called_once_with(
            uid='FAKE_ID', passwd='FAKE_PASS')
        mock_keystone.trust_get_by_trustor.assert_called_once_with(
            self.context.user, 'FAKE_ADMIN_ID', self.context.project)
