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
from senlin.db import api as db_api
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

    @mock.patch('senlin.db.api')
    def test_get_trust_not_exists(self, mock_db_api):
        db_api.cred_get = mock.MagicMock(return_value=None)

        client = mock.MagicMock()
        client.trust_get_by_trustor = mock.MagicMock(return_value=None)
        client.get_user_id.return_value = 'FAKE_ADMIN_ID'
        test_trust = mock.MagicMock()
        test_trust.id = "FAKE_TRUST_ID"
        client.trust_create = mock.MagicMock(return_value=test_trust)
        db_api.cred_create = mock.MagicMock()

        with mock.patch(
                'senlin.drivers.openstack.keystone_v3.KeystoneClient',
                return_value=client):

            trust_id = self.middleware._get_trust(self.context)
            self.assertEqual(trust_id, test_trust.id)
            self.assertTrue(db_api.cred_get.called)
            self.assertTrue(client.get_user_id.called)
            self.assertTrue(client.trust_get_by_trustor.called)
            self.assertTrue(client.trust_create.called)
            self.assertTrue(db_api.cred_create.called)
