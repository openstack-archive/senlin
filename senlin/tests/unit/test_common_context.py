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

from senlin.common import context
from senlin.tests.unit.common import base


class TestRequestContext(base.SenlinTestCase):

    def setUp(self):
        self.ctx = {
            'auth_url': 'http://xyz',
            'auth_token_info': {'123info': 'woop'},
            'user_name': 'mick',
            'user_domain_name': 'user-domain-name',
            'project_id': 'project-id',
            'project_name': 'a project',
            'project_domain_name': 'a project domain',
            'domain_name': 'this domain',
            'trusts': None,
            'region_name': 'regionOne',
            'password': 'foo',
            'is_admin': False  # needed for tests to work
        }

        super(TestRequestContext, self).setUp()

    def test_request_context_init(self):
        ctx = context.RequestContext(
            auth_url=self.ctx.get('auth_url'),
            auth_token_info=self.ctx.get('auth_token_info'),
            user_name=self.ctx.get('user_name'),
            user_domain_name=self.ctx.get('user_domain_name'),
            project_id=self.ctx.get('project_id'),
            project_name=self.ctx.get('project_name'),
            project_domain_name=self.ctx.get('project_domain_name'),
            domain_name=self.ctx.get('domain_name'),
            trusts=self.ctx.get('trusts'),
            region_name=self.ctx.get('region_name'),
            password=self.ctx.get('password'),
            is_admin=self.ctx.get('is_admin'))  # need for tests to work

        ctx_dict = ctx.to_dict()
        for k, v in self.ctx.items():
            self.assertEqual(v, ctx_dict.get(k))

    def test_request_context_from_dict(self):
        ctx = context.RequestContext.from_dict(self.ctx)

        ctx_dict = ctx.to_dict()
        for k, v in self.ctx.items():
            self.assertEqual(v, ctx_dict.get(k))

    def test_request_context_update(self):
        ctx = context.RequestContext.from_dict(self.ctx)

        for k in self.ctx:
            self.assertEqual(self.ctx.get(k), ctx.to_dict().get(k))
            override = '%s_override' % k
            setattr(ctx, k, override)
            self.assertEqual(override, ctx.to_dict().get(k))

    def test_get_admin_context(self):
        ctx1 = context.get_admin_context()
        self.assertTrue(ctx1.is_admin)
