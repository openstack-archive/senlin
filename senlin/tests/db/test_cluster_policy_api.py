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

import six

from senlin.common import exception
from senlin.common.i18n import _
from senlin.db.sqlalchemy import api as db_api
from senlin.engine import parser
from senlin.tests.common import base
from senlin.tests.common import utils
from senlin.tests.db import shared


class DBAPIClusterPolicyTest(base.SenlinTestCase):
    def setUp(self):
        super(DBAPIClusterPolicyTest, self).setUp()
        self.ctx = utils.dummy_context()
        self.profile = shared.create_profile(self.ctx)
        self.cluster = shared.create_cluster(self.ctx, self.profile)

    def test_policy_attach_detach(self):
        data = parser.parse_policy(shared.sample_policy)
        policy = db_api.policy_create(self.ctx, data)

        fields = {
            'enabled': True,
            'level': 50
        }
        db_api.cluster_attach_policy(self.ctx, self.cluster.id, policy.id,
                                     fields)
        bindings = db_api.cluster_get_policies(self.ctx, self.cluster.id)
        self.assertEqual(1, len(bindings))
        self.assertEqual(True, bindings[0].enabled)

        # This will succeed
        db_api.cluster_detach_policy(self.ctx, self.cluster.id, policy.id)
        bindings = db_api.cluster_get_policies(self.ctx, self.cluster.id)
        self.assertEqual(0, len(bindings))

        # This will fail
        exc = self.assertRaises(exception.NotFound,
                                db_api.cluster_detach_policy,
                                self.ctx, self.cluster.id, 'BOGUS')
        msg = _('Failed detaching policy "BOGUS" from cluster '
                '"%s"') % self.cluster.id
        self.assertEqual(msg, six.text_type(exc))

    def test_policy_enable_disable(self):
        data = parser.parse_policy(shared.sample_policy)
        policy = db_api.policy_create(self.ctx, data)

        fields = {
            'enabled': True,
            'level': 50
        }
        db_api.cluster_attach_policy(self.ctx, self.cluster.id, policy.id,
                                     fields)
        bindings = db_api.cluster_get_policies(self.ctx, self.cluster.id)
        self.assertEqual(1, len(bindings))
        self.assertEqual(True, bindings[0].enabled)

        db_api.cluster_enable_policy(self.ctx, self.cluster.id, policy.id)
        bindings = db_api.cluster_get_policies(self.ctx, self.cluster.id)
        self.assertEqual(1, len(bindings))
        self.assertEqual(True, bindings[0].enabled)

        db_api.cluster_disable_policy(self.ctx, self.cluster.id, policy.id)
        bindings = db_api.cluster_get_policies(self.ctx, self.cluster.id)
        self.assertEqual(1, len(bindings))
        self.assertEqual(False, bindings[0].enabled)

        db_api.cluster_enable_policy(self.ctx, self.cluster.id, policy.id)
        bindings = db_api.cluster_get_policies(self.ctx, self.cluster.id)
        self.assertEqual(1, len(bindings))
        self.assertEqual(True, bindings[0].enabled)

        exc = self.assertRaises(exception.NotFound,
                                db_api.cluster_enable_policy,
                                self.ctx, self.cluster.id, 'BOGUS')
        msg = _('Failed enabling policy "BOGUS" on cluster '
                '"%s"') % self.cluster.id
        self.assertEqual(msg, six.text_type(exc))

        exc = self.assertRaises(exception.NotFound,
                                db_api.cluster_disable_policy,
                                self.ctx, self.cluster.id, 'BOGUS')
        msg = _('Failed disabling policy "BOGUS" on cluster '
                '"%s"') % self.cluster.id
        self.assertEqual(msg, six.text_type(exc))
