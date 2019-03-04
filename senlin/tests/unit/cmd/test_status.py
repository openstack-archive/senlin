# Copyright (c) 2018 NEC, Corp.
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

from oslo_upgradecheck.upgradecheck import Code

from senlin.cmd import status
from senlin.db.sqlalchemy import api as db_api
from senlin.tests.unit.common import base
from senlin.tests.unit.common import utils


class TestUpgradeChecks(base.SenlinTestCase):

    def setUp(self):
        super(TestUpgradeChecks, self).setUp()
        self.ctx = utils.dummy_context()
        self.cmd = status.Checks()

        self.healthpolv1_0_data = {
            'name': 'test_healthpolicy',
            'type': 'senlin.policy.health-1.0',
            'user': self.ctx.user_id,
            'project': self.ctx.project_id,
            'domain': self.ctx.domain_id,
            'data': None,
        }

        self.healthpolv1_1_data = {
            'name': 'test_healthpolicy',
            'type': 'senlin.policy.health-1.1',
            'user': self.ctx.user_id,
            'project': self.ctx.project_id,
            'domain': self.ctx.domain_id,
            'data': None,
        }

        self.scalepol_data = {
            'name': 'test_scalepolicy',
            'type': 'senlin.policy.scaling-1.0',
            'user': self.ctx.user_id,
            'project': self.ctx.project_id,
            'domain': self.ctx.domain_id,
            'data': None,
        }

    def test__check_healthpolicy_success(self):
        healthpolv1_1 = db_api.policy_create(self.ctx, self.healthpolv1_1_data)
        self.addCleanup(db_api.policy_delete, self.ctx, healthpolv1_1.id)

        scalepol = db_api.policy_create(self.ctx, self.scalepol_data)
        self.addCleanup(db_api.policy_delete, self.ctx, scalepol.id)

        check_result = self.cmd._check_healthpolicy()
        self.assertEqual(Code.SUCCESS, check_result.code)

    def test__check_healthpolicy_failed(self):
        healthpolv1_0 = db_api.policy_create(self.ctx, self.healthpolv1_0_data)
        self.addCleanup(db_api.policy_delete, self.ctx, healthpolv1_0.id)

        scalepol = db_api.policy_create(self.ctx, self.scalepol_data)
        self.addCleanup(db_api.policy_delete, self.ctx, scalepol.id)

        check_result = self.cmd._check_healthpolicy()
        self.assertEqual(Code.FAILURE, check_result.code)
