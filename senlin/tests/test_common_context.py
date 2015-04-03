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

import os
from oslo_config import cfg
from oslo_middleware import request_id
import webob

from senlin.common import context
from senlin.common import exception
from senlin.tests.common import base

policy_path = os.path.dirname(os.path.realpath(__file__)) + "/policy/"


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
        self.assertEqual(self.ctx, ctx_dict)

    def test_request_context_from_dict(self):
        ctx = context.RequestContext.from_dict(self.ctx)
        ctx_dict = ctx.to_dict()
        del(ctx_dict['request_id'])
        self.assertEqual(self.ctx, ctx_dict)

    def test_request_context_update(self):
        ctx = context.RequestContext.from_dict(self.ctx)

        for k in self.ctx:
            self.assertEqual(self.ctx.get(k), ctx.to_dict().get(k))
            override = '%s_override' % k
            setattr(ctx, k, override)
            self.assertEqual(override, ctx.to_dict().get(k))


class RequestContextMiddlewareTest(base.SenlinTestCase):

    scenarios = [(
        'empty_headers',
        dict(
            environ=None,
            headers={},
            expected_exception=None,
            context_dict={
                'auth_token': None,
                'auth_token_info': None,
                'auth_url': None,
                'is_admin': False,
                'password': None,
                'roles': [],
                'show_deleted': False,
                'project': None,
                'user': None,
                'user_name': None
            })
    ), (
        'token_creds',
        dict(
            environ={'keystone.token_info': {'info': 123}},
            headers={
                'X-User-Id': '7a87ff18-31c6-45ce-a186-ec7987f488c3',
                'X-Auth-Token': 'atoken2',
                'X-Project-Name': 'my_project2',
                'X-Project-Id': 'bb9108c8-62d0-4d92-898c-d644a6af20e9',
                'X-Auth-Url': 'http://192.0.2.1:5000/v1',
                'X-Roles': 'role1,role2,role3',
            },
            expected_exception=None,
            context_dict={
                'auth_token': 'atoken2',
                'auth_token_info': {'info': 123},
                'auth_url': 'http://192.0.2.1:5000/v1',
                'is_admin': False,
                'password': None,
                'roles': ['role1', 'role2', 'role3'],
                'show_deleted': False,
                'project': 'bb9108c8-62d0-4d92-898c-d644a6af20e9',
                'user': '7a87ff18-31c6-45ce-a186-ec7987f488c3',
                'user_name': None
            })
    ), (
        'malformed_roles',
        dict(
            environ=None,
            headers={
                'X-Roles': [],
            },
            expected_exception=exception.NotAuthenticated)
    )]

    def setUp(self):
        super(RequestContextMiddlewareTest, self).setUp()
        opts = [
            cfg.StrOpt('config_dir', default=policy_path),
            cfg.StrOpt('config_file', default='foo'),
            cfg.StrOpt('project', default='senlin'),
        ]
        cfg.CONF.register_opts(opts)
        cfg.CONF.set_override('policy_file', 'check_admin.json')

    def test_context_middleware(self):

        middleware = context.ContextMiddleware(None, None)
        request = webob.Request.blank('/clusters', headers=self.headers,
                                      environ=self.environ)
        if self.expected_exception:
            self.assertRaises(
                self.expected_exception, middleware.process_request, request)
        else:
            self.assertIsNone(middleware.process_request(request))
            ctx = request.context.to_dict()
            for k, v in self.context_dict.items():
                self.assertEqual(v, ctx[k], 'Key %s values do not match' % k)
            self.assertIsNotNone(ctx.get('request_id'))

    def test_context_middleware_with_requestid(self):

        middleware = context.ContextMiddleware(None, None)
        request = webob.Request.blank('/clusters', headers=self.headers,
                                      environ=self.environ)
        req_id = 'req-5a63f0d7-1b69-447b-b621-4ea87cc7186d'
        request.environ[request_id.ENV_REQUEST_ID] = req_id
        if self.expected_exception:
            self.assertRaises(
                self.expected_exception, middleware.process_request, request)
        else:
            self.assertIsNone(middleware.process_request(request))
            ctx = request.context.to_dict()
            for k, v in self.context_dict.items():
                self.assertEqual(v, ctx[k], 'Key %s values do not match' % k)
            self.assertEqual(
                ctx.get('request_id'), req_id,
                'Key request_id values do not match')
