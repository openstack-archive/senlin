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


from senlin.db.sqlalchemy import api as db_api
from senlin.tests.common import base
from senlin.tests.common import utils
from senlin.tests.db import shared

UUID1 = shared.UUID1
values = {
    'user': UUID1,
    'cred': {
        'trust': '01234567890123456789012345678901',
    },
    'data': {}
}


class DBAPICredentialTest(base.SenlinTestCase):

    def setUp(self):
        super(DBAPICredentialTest, self).setUp()
        self.ctx = utils.dummy_context()

    def test_cred_create(self):
        cred = db_api.cred_create(self.ctx, values)
        self.assertIsNotNone(cred)
        self.assertEqual(UUID1, cred.user)
        self.assertEqual({'trust': '01234567890123456789012345678901'},
                         cred.cred)
        self.assertEqual({}, cred.data)

    def test_cred_get(self):
        cred = db_api.cred_get(self.ctx, UUID1)
        self.assertIsNone(cred)

        db_api.cred_create(self.ctx, values)

        cred = db_api.cred_get(self.ctx, UUID1)
        self.assertIsNotNone(cred)
        self.assertEqual(UUID1, cred.user)
        self.assertEqual({'trust': '01234567890123456789012345678901'},
                         cred.cred)
        self.assertEqual({}, cred.data)

    def test_cred_delete(self):
        cred = db_api.cred_delete(self.ctx, UUID1)
        self.assertIsNone(cred)

        db_api.cred_create(self.ctx, values)
        cred = db_api.cred_delete(self.ctx, UUID1)
        self.assertIsNone(cred)
