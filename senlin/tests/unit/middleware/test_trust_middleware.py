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

from senlin.api.middleware import trust
from senlin.common import context
from senlin.common import exception
from senlin.db import api as db_api
from senlin.drivers import base as driver_base
from senlin.tests.unit.common import base
from senlin.tests.unit.common import utils


class TestTrustMiddleware(base.SenlinTestCase):

    def setUp(self):
        super(TestTrustMiddleware, self).setUp()
        self.context = utils.dummy_context()
        self.middleware = trust.TrustMiddleware(None)

    @mock.patch('senlin.db.api')
    def test_get_trust_already_exists(self, mock_db_api):
        res = mock.MagicMock()
        res.cred = {}
        res.cred['openstack'] = {}
        res.cred['openstack']['trust'] = 'FAKE_TRUST_ID'
        db_api.cred_get = mock.MagicMock(return_value=res)
        trust_id = self.middleware._get_trust(self.context)
        self.assertEqual(res.cred['openstack']['trust'], trust_id)
        self.assertTrue(db_api.cred_get.called)

    @mock.patch.object(context, 'get_service_context')
    @mock.patch.object(db_api, 'cred_get')
    @mock.patch.object(db_api, 'cred_create')
    @mock.patch.object(driver_base, 'SenlinDriver')
    def test_get_trust_not_exists(self, mock_senlindriver, mock_cred_create,
                                  mock_cred_get, mock_get_service_context):
        mock_cred_get.return_value = None
        mock_get_service_context.return_value = {'k1': 'v1', 'k2': 'v2'}
        sd = mock.Mock()
        kc = mock.Mock()
        sd.identity.return_value = kc
        mock_senlindriver.return_value = sd
        kc.get_user_id.return_value = 'FAKE_ADMIN_ID'
        kc.trust_get_by_trustor.side_effect = exception.InternalError(
            code=400, message='Bad request')
        trust = mock.Mock()
        kc.trust_create.return_value = trust
        trust.id = 'FAKE_TRUST_ID'

        trust_id = self.middleware._get_trust(self.context)
        self.assertEqual(trust_id, 'FAKE_TRUST_ID')
        self.assertTrue(db_api.cred_get.called)
        self.assertTrue(kc.get_user_id.called)
        self.assertTrue(kc.trust_get_by_trustor.called)
        self.assertTrue(kc.trust_create.called)
        self.assertTrue(db_api.cred_create.called)
