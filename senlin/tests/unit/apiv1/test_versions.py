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

import json
import mock
from oslo_utils import encodeutils
from six.moves import http_client
import webob

from senlin.api.openstack import versions
from senlin.common import wsgi
from senlin.tests.unit.common import base


class VersionControllerTest(base.SenlinTestCase):

    def test_init(self):
        conf = mock.Mock()

        controller = versions.Controller(conf)

        self.assertIsNotNone(controller)
        self.assertEqual(conf, controller.conf)

    def test_call(self):
        conf = mock.Mock()
        controller = versions.Controller(conf)
        environ = {
            'REQUEST_METHOD': 'GET',
            'SERVER_NAME': 'host',
            'SERVER_PORT': 8778,
            'SCRIPT_NAME': '/v1',
            'PATH_INFO': '/tenant_id/versions',
            'wsgi.url_scheme': 'http',
        }
        req = wsgi.Request(environ)
        expected_dict = {
            'versions': [{
                'id': 'v1.0',
                'status': 'CURRENT',
                'links': [{
                    'rel': 'self',
                    'href': 'http://host:8778/v1/'
                }]
            }]
        }
        expected_body = json.dumps(expected_dict)

        resp = controller(req)

        self.assertIsInstance(resp, webob.Response)
        self.assertEqual(expected_body, encodeutils.safe_decode(resp.body))
        self.assertEqual(http_client.MULTIPLE_CHOICES, resp.status_code)
        self.assertEqual('application/json', resp.content_type)

    def test_get_href(self):
        controller = versions.Controller(mock.Mock())
        req = mock.Mock()
        req.host_url = 'FAKE_URL'

        res = controller.get_href(req)

        self.assertEqual('FAKE_URL/v1/', res)
