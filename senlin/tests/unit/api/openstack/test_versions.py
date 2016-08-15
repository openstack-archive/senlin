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

import mock
from oslo_serialization import jsonutils
from oslo_utils import encodeutils
from six.moves import http_client
import webob

from senlin.api.common import wsgi
from senlin.api.openstack.v1 import version as v1_controller
from senlin.api.openstack import versions
from senlin.tests.unit.common import base


class VersionControllerTest(base.SenlinTestCase):

    def test_init(self):
        conf = mock.Mock()

        controller = versions.Controller(conf)

        self.assertIsNotNone(controller)
        self.assertEqual(conf, controller.conf)

    @mock.patch.object(v1_controller.VersionController, 'version_info')
    def test_call(self, mock_v1):
        mock_v1.return_value = {'foo': 'bar'}
        conf = mock.Mock()
        controller = versions.Controller(conf)
        environ = {
            'REQUEST_METHOD': 'GET',
            'SERVER_NAME': 'host',
            'SERVER_PORT': 8778,
            'SCRIPT_NAME': '/',
            'PATH_INFO': '/',
            'wsgi.url_scheme': 'http',
        }
        req = wsgi.Request(environ)
        expected_dict = {
            'versions': [{'foo': 'bar'}]
        }
        expected_body = jsonutils.dumps(expected_dict)

        resp = controller(req)

        self.assertIsInstance(resp, webob.Response)
        self.assertEqual(expected_body, encodeutils.safe_decode(resp.body))
        self.assertEqual(http_client.MULTIPLE_CHOICES, resp.status_code)
        self.assertEqual('application/json', resp.content_type)
