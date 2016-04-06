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
            'auth_token': '123',
            'auth_token_info': {'123info': 'woop'},
            'user': 'fooUser',
            'user_name': 'mick',
            'user_domain': 'user-domain',
            'user_domain_name': 'user-domain-name',
            'domain': 'domain-id',
            'domain_name': 'this domain',
            'project': 'project-id',
            'project_name': 'a project',
            'project_domain': 'project-domain-id',
            'project_domain_name': 'a project domain',
            'is_admin': False,
            'password': 'foo',
            'show_deleted': False,
            'read_only': False,
            'roles': ['arole', 'notadmin'],
            'auth_url': 'http://xyz',
            'trusts': None,
            'region_name': 'regionOne'
        }

        super(TestRequestContext, self).setUp()

    def test_request_context_init(self):
        ctx = context.RequestContext(
            auth_token=self.ctx.get('auth_token'),
            auth_token_info=self.ctx.get('auth_token_info'),
            user=self.ctx.get('user'),
            user_name=self.ctx.get('user_name'),
            user_domain=self.ctx.get('user_domain'),
            user_domain_name=self.ctx.get('user_domain_name'),
            domain=self.ctx.get('domain'),
            domain_name=self.ctx.get('domain_name'),
            project_domain=self.ctx.get('project_domain'),
            project_domain_name=self.ctx.get('project_domain_name'),
            project=self.ctx.get('project'),
            project_name=self.ctx.get('project_name'),
            is_admin=self.ctx.get('is_admin'),
            password=self.ctx.get('password'),
            show_deleted=self.ctx.get('show_deleted'),
            roles=self.ctx.get('roles'),
            auth_url=self.ctx.get('auth_url'),
            trusts=self.ctx.get('trusts'),
            region_name=self.ctx.get('region_name'))

        ctx_dict = ctx.to_dict()
        del(ctx_dict['request_id'])
        del(ctx_dict['user_identity'])
        del(ctx_dict['resource_uuid'])
        del(ctx_dict['tenant'])
        self.assertEqual(self.ctx, ctx_dict)

    def test_request_context_from_dict(self):
        ctx = context.RequestContext.from_dict(self.ctx)
        ctx_dict = ctx.to_dict()
        del(ctx_dict['request_id'])
        del(ctx_dict['user_identity'])
        del(ctx_dict['resource_uuid'])
        del(ctx_dict['tenant'])
        self.assertEqual(self.ctx, ctx_dict)

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
