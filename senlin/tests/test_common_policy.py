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

import os.path

from oslo_config import cfg

from senlin.common import exception
from senlin.common import policy
from senlin.openstack.common import policy as base_policy
from senlin.tests.common import base 
from senlin.tests.common import utils

policy_path = os.path.dirname(os.path.realpath(__file__)) + "/policy/"


class TestPolicyEnforcer(base.SenlinTestCase):
    cluster_requests = ("index", "create", "delete", "update",
                        "get", "action")

    def setUp(self):
        super(TestPolicyEnforcer, self).setUp()
        opts = [
            cfg.StrOpt('config_dir', default=policy_path),
            cfg.StrOpt('config_file', default='foo'),
            cfg.StrOpt('project', default='senlin'),
        ]
        cfg.CONF.register_opts(opts)

    def get_policy_file(self, filename):
        return policy_path + filename

    def test_policy_clusters_notallowed(self):
        enforcer = policy.Enforcer(
            scope='clusters',
            policy_file=self.get_policy_file('notallowed.json'))

        ctx = utils.dummy_context(roles=[])
        for request in self.cluster_requests:
            # Everything should raise the default exception.Forbidden
            self.assertRaises(exception.Forbidden, enforcer.enforce, ctx,
                              request, {})

    def test_set_rules_overwrite_true(self):
        enforcer = policy.Enforcer(
            policy_file=self.get_policy_file('notallowed.json'))
        enforcer.load_rules(True)
        enforcer.set_rules({'test_rule_1': 1}, True)
        self.assertEqual({'test_rule_1': 1}, enforcer.enforcer.rules)

    def test_set_rules_overwrite_false(self):
        enforcer = policy.Enforcer(
            policy_file=self.get_policy_file('notallowed.json'))
        enforcer.load_rules(True)
        enforcer.load_rules(True)
        enforcer.set_rules({'test_rule_1': 1}, False)
        self.assertIn('test_rule_1', enforcer.enforcer.rules)

    def test_load_rules_force_reload_true(self):
        enforcer = policy.Enforcer(
            policy_file=self.get_policy_file('notallowed.json'))
        enforcer.load_rules(True)
        enforcer.set_rules({'test_rule_1': 'test'})
        enforcer.load_rules(True)
        self.assertNotIn({'test_rule_1': 'test'}, enforcer.enforcer.rules)

    def test_load_rules_force_reload_false(self):
        enforcer = policy.Enforcer(
            policy_file=self.get_policy_file('notallowed.json'))
        enforcer.load_rules(True)
        enforcer.load_rules(True)
        enforcer.set_rules({'test_rule_1': 'test'})
        enforcer.load_rules(False)
        self.assertIn('test_rule_1', enforcer.enforcer.rules)

    def test_default_rule(self):
        ctx = utils.dummy_context(roles=['some_unknown_user'])
        default_rule = base_policy.FalseCheck()
        enforcer = policy.Enforcer(
            scope='clusters',
            policy_file=self.get_policy_file('notallowed.json'),
            exc=None, default_rule=default_rule)
        request = 'some_unknown_request'
        self.assertFalse(enforcer.enforce(ctx, request))

    def test_check_admin(self):
        enforcer = policy.Enforcer(
            policy_file=self.get_policy_file('check_admin.json'))

        ctx = utils.dummy_context(roles=[])
        self.assertFalse(enforcer.check_is_admin(ctx))

        ctx = utils.dummy_context(roles=['not_admin'])
        self.assertFalse(enforcer.check_is_admin(ctx))

        ctx = utils.dummy_context(roles=['admin'])
        self.assertTrue(enforcer.check_is_admin(ctx))

    def test_enforce_creds(self):
        enforcer = policy.Enforcer()
        ctx = utils.dummy_context(roles=['admin'])
        self.patchobject(base_policy.Enforcer, 'enforce')
        base_policy.Enforcer.enforce('context_is_admin', {}, ctx.to_dict(),
                                     False, exc=None).AndReturn(True)
        self.assertTrue(enforcer.check_is_admin(ctx))
