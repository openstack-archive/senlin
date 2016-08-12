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
from oslo_middleware import ssl

from senlin.api import middleware as mw
from senlin.api.middleware import context
from senlin.api.middleware import fault
from senlin.api.middleware import trust
from senlin.api.middleware import version_negotiation as vn
from senlin.api.middleware import webhook
from senlin.tests.unit.common import base


class MiddlewareFilterTest(base.SenlinTestCase):

    def setUp(self):
        super(MiddlewareFilterTest, self).setUp()

        self.app = mock.Mock()
        self.conf = mock.Mock()
        self.local_conf = dict(key='value')

    @mock.patch.object(vn, 'VersionNegotiationFilter')
    def test_version_negotiation_filter(self, mock_vnf):
        exp = mock.Mock()
        mock_vnf.return_value = exp

        actual = mw.version_filter(self.app, self.conf, **self.local_conf)

        self.assertEqual(exp, actual)
        mock_vnf.assert_called_once_with(self.app, self.conf)

    @mock.patch.object(fault, 'FaultWrapper')
    def test_faultwrap_filter(self, mock_fw):
        exp = mock.Mock()
        mock_fw.return_value = exp

        actual = mw.fault_filter(self.app, self.conf, **self.local_conf)

        self.assertEqual(exp, actual)
        mock_fw.assert_called_once_with(self.app)

    @mock.patch.object(ssl, 'SSLMiddleware')
    def test_sslmiddlware_filter(self, mock_ssl):
        exp = mock.Mock()
        mock_ssl.return_value = exp

        actual = ssl.SSLMiddleware(self.app, self.conf, **self.local_conf)

        self.assertEqual(exp, actual)
        mock_ssl.assert_called_once_with(self.app, self.conf,
                                         **self.local_conf)

    @mock.patch.object(context, 'ContextMiddleware')
    def test_contextmiddlware_filter(self, mock_ctx):
        exp = mock.Mock()
        mock_ctx.return_value = exp

        actual = mw.context_filter(self.app, self.conf, **self.local_conf)

        self.assertEqual(exp, actual)
        mock_ctx.assert_called_once_with(self.app)

    @mock.patch.object(trust, 'TrustMiddleware')
    def test_trustmiddlware_filter(self, mock_trust):
        exp = mock.Mock()
        mock_trust.return_value = exp

        actual = mw.trust_filter(self.app, self.conf, **self.local_conf)

        self.assertEqual(exp, actual)
        mock_trust.assert_called_once_with(self.app)

    @mock.patch.object(webhook, 'WebhookMiddleware')
    def test_webhookmiddlware_filter(self, mock_wh):
        exp = mock.Mock()
        mock_wh.return_value = exp

        actual = mw.webhook_filter(self.app, self.conf, **self.local_conf)

        self.assertEqual(exp, actual)
        mock_wh.assert_called_once_with(self.app)
