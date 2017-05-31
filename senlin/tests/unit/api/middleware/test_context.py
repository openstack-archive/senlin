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
from oslo_config import fixture
from oslo_middleware import request_id
from oslo_policy import opts as policy_opts
import webob

from senlin.api.common import version_request as vr
from senlin.api.middleware import context
from senlin.common import exception
from senlin.tests.unit.common import base

policy_path = os.path.dirname(os.path.realpath(__file__)) + "/policy/"


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
                'auth_url': '',
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
        self.fixture = self.useFixture(fixture.Config())
        self.fixture.conf(args=['--config-dir', policy_path])
        policy_opts.set_defaults(cfg.CONF)
        cfg.CONF.set_override('policy_file', 'check_admin.json',
                              group='oslo_policy')

    def test_context_middleware(self):
        avr = vr.APIVersionRequest('1.0')
        middleware = context.ContextMiddleware(None)
        request = webob.Request.blank('/clusters', headers=self.headers,
                                      environ=self.environ)
        request.version_request = avr
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
        avr = vr.APIVersionRequest('1.0')
        middleware = context.ContextMiddleware(None)
        request = webob.Request.blank('/clusters', headers=self.headers,
                                      environ=self.environ)
        req_id = 'req-5a63f0d7-1b69-447b-b621-4ea87cc7186d'
        request.environ[request_id.ENV_REQUEST_ID] = req_id
        request.version_request = avr
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
