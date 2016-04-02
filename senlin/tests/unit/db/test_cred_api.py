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

from senlin.db.sqlalchemy import api as db_api
from senlin.tests.unit.common import base
from senlin.tests.unit.common import utils
from senlin.tests.unit.db import shared

USER_ID = shared.UUID1
PROJECT_ID = '26e4df6952b144e5823aae7ce463a240'
values = {
    'user': USER_ID,
    'project': PROJECT_ID,
    'cred': {
        'openstack': {
            'trust': '01234567890123456789012345678901',
        },
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
        self.assertEqual(USER_ID, cred.user)
        self.assertEqual(PROJECT_ID, cred.project)
        self.assertEqual(
            {'openstack': {'trust': '01234567890123456789012345678901'}},
            cred.cred)
        self.assertEqual({}, cred.data)

    def test_cred_get(self):
        cred = db_api.cred_get(self.ctx, USER_ID, PROJECT_ID)
        self.assertIsNone(cred)

        db_api.cred_create(self.ctx, values)

        cred = db_api.cred_get(self.ctx, USER_ID, PROJECT_ID)
        self.assertIsNotNone(cred)
        self.assertEqual(USER_ID, cred.user)
        self.assertEqual(PROJECT_ID, cred.project)
        self.assertEqual(
            {'openstack': {'trust': '01234567890123456789012345678901'}},
            cred.cred)
        self.assertEqual({}, cred.data)

    def test_cred_update(self):
        db_api.cred_create(self.ctx, values)
        new_values = {
            'cred': {
                'openstack': {
                    'trust': 'newtrust'
                }
            }
        }
        db_api.cred_update(self.ctx, USER_ID, PROJECT_ID, new_values)
        cred = db_api.cred_get(self.ctx, USER_ID, PROJECT_ID)
        self.assertIsNotNone(cred)
        self.assertEqual({'openstack': {'trust': 'newtrust'}},
                         cred.cred)

    def test_cred_delete(self):
        cred = db_api.cred_delete(self.ctx, USER_ID, PROJECT_ID)
        self.assertIsNone(cred)

        db_api.cred_create(self.ctx, values)
        cred = db_api.cred_delete(self.ctx, USER_ID, PROJECT_ID)
        self.assertIsNone(cred)

    def test_cred_create_update(self):
        cred = db_api.cred_create_update(self.ctx, values)
        self.assertIsNotNone(cred)
        self.assertEqual(USER_ID, cred.user)
        self.assertEqual(PROJECT_ID, cred.project)
        self.assertEqual(
            {'openstack': {'trust': '01234567890123456789012345678901'}},
            cred.cred)
        self.assertEqual({}, cred.data)

        new_values = copy.deepcopy(values)
        new_values['cred']['openstack']['trust'] = 'newtrust'
        cred = db_api.cred_create_update(self.ctx, new_values)
        self.assertEqual(USER_ID, cred.user)
        self.assertEqual(PROJECT_ID, cred.project)
        self.assertEqual(
            {'openstack': {'trust': 'newtrust'}},
            cred.cred)
