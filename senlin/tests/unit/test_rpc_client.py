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

"""
Unit Tests for senlin.rpc.client
"""
import mock

from senlin.common import messaging
from senlin.rpc import client as rpc_client
from senlin.tests.unit.common import base
from senlin.tests.unit.common import utils


class EngineRpcAPITestCase(base.SenlinTestCase):

    def setUp(self):
        messaging.setup("fake://", optional=True)
        self.addCleanup(messaging.cleanup)
        self.context = utils.dummy_context()

        # self.stubs = stubout.StubOutForTesting()
        self.rpcapi = rpc_client.EngineClient()
        super(EngineRpcAPITestCase, self).setUp()

    @mock.patch.object(messaging, 'get_rpc_client')
    def test_call(self, mock_client):
        client = mock.Mock()
        mock_client.return_value = client

        method = 'fake_method'
        req = mock.Mock()
        rpcapi = rpc_client.EngineClient()

        # with no version
        res = rpcapi.call(self.context, method, req)

        self.assertEqual(client, rpcapi._client)
        client.call.assert_called_once_with(self.context, 'fake_method',
                                            req=req)
        self.assertEqual(res, client.call.return_value)

    @mock.patch.object(messaging, 'get_rpc_client')
    def test_call_with_version(self, mock_client):
        client = mock.Mock()
        mock_client.return_value = client

        method = 'fake_method'
        req = mock.Mock()
        rpcapi = rpc_client.EngineClient()

        # with version
        res = rpcapi.call(self.context, method, req, version='123')

        rpcapi._client.prepare.assert_called_once_with(version='123')
        new_client = client.prepare.return_value
        new_client.call.assert_called_once_with(self.context, 'fake_method',
                                                req=req)
        self.assertEqual(res, new_client.call.return_value)

    @mock.patch.object(messaging, 'get_rpc_client')
    def test_cast(self, mock_client):
        client = mock.Mock()
        mock_client.return_value = client

        method = 'fake_method'
        kwargs = {'key': 'value'}
        rpcapi = rpc_client.EngineClient()
        msg = rpcapi.make_msg(method, **kwargs)

        # with no version
        res = rpcapi.cast(self.context, msg)

        self.assertEqual(client, rpcapi._client)
        client.cast.assert_called_once_with(self.context, 'fake_method',
                                            key='value')
        self.assertEqual(res, client.cast.return_value)

        # with version
        res = rpcapi.cast(self.context, msg, version='123')
        client.prepare.assert_called_once_with(version='123')
        new_client = client.prepare.return_value
        new_client.cast.assert_called_once_with(self.context, 'fake_method',
                                                key='value')
        self.assertEqual(res, new_client.cast.return_value)

    def _test_engine_api(self, method, rpc_method, **kwargs):
        ctxt = utils.dummy_context()
        expected_retval = 'foo' if method == 'call' else None

        kwargs.pop('version', None)

        if 'expected_message' in kwargs:
            expected_message = kwargs['expected_message']
            del kwargs['expected_message']
        else:
            expected_message = self.rpcapi.make_msg(method, **kwargs)

        cast_and_call = [
            'profile_delete',
            'policy_delete',
            'cluster_delete',
            'node_delete',
            'receiver_delete',
            'webhook_delete',
        ]

        if rpc_method == 'call' and method in cast_and_call:
            kwargs['cast'] = False

        mock_rpc_method = self.patchobject(self.rpcapi, rpc_method,
                                           return_value=expected_retval)

        retval = getattr(self.rpcapi, method)(ctxt, **kwargs)

        self.assertEqual(expected_retval, retval)
        expected_args = [ctxt, expected_message, mock.ANY]
        actual_args, _ = mock_rpc_method.call_args
        for expected_arg, actual_arg in zip(expected_args, actual_args):
            self.assertEqual(expected_arg, actual_arg)
