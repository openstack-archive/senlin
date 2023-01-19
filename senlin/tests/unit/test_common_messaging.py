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

from unittest import mock

import oslo_messaging
import testtools

from senlin.common import consts
from senlin.common import messaging


class TestUtilFunctions(testtools.TestCase):

    @mock.patch.object(oslo_messaging, "get_rpc_server")
    @mock.patch("senlin.common.messaging.RequestContextSerializer")
    @mock.patch("senlin.common.messaging.JsonPayloadSerializer")
    def test_get_rpc_server(self, mock_json_serializer,
                            mock_context_serializer,
                            mock_get_rpc_server):
        x_target = mock.Mock()
        x_endpoint = mock.Mock()
        x_json_serializer = mock.Mock()
        mock_json_serializer.return_value = x_json_serializer
        x_context_serializer = mock.Mock()
        mock_context_serializer.return_value = x_context_serializer
        x_rpc_server = mock.Mock()
        mock_get_rpc_server.return_value = x_rpc_server

        res = messaging.get_rpc_server(x_target, x_endpoint)

        self.assertEqual(x_rpc_server, res)
        mock_json_serializer.assert_called_once_with()
        mock_context_serializer.assert_called_once_with(x_json_serializer)
        mock_get_rpc_server.assert_called_once_with(
            messaging.TRANSPORT, x_target, [x_endpoint],
            executor='eventlet', serializer=x_context_serializer)

    @mock.patch.object(oslo_messaging, "get_rpc_server")
    @mock.patch("senlin.common.messaging.RequestContextSerializer")
    @mock.patch("senlin.common.messaging.JsonPayloadSerializer")
    def test_get_rpc_server_with_serializer(self, mock_json_serializer,
                                            mock_context_serializer,
                                            mock_get_rpc_server):
        x_target = mock.Mock()
        x_endpoint = mock.Mock()
        x_serializer = mock.Mock()
        x_context_serializer = mock.Mock()
        mock_context_serializer.return_value = x_context_serializer
        x_rpc_server = mock.Mock()
        mock_get_rpc_server.return_value = x_rpc_server

        res = messaging.get_rpc_server(x_target, x_endpoint,
                                       serializer=x_serializer)

        self.assertEqual(x_rpc_server, res)
        self.assertEqual(0, mock_json_serializer.call_count)
        mock_context_serializer.assert_called_once_with(x_serializer)
        mock_get_rpc_server.assert_called_once_with(
            messaging.TRANSPORT, x_target, [x_endpoint],
            executor='eventlet', serializer=x_context_serializer)

    @mock.patch("oslo_messaging.Target")
    @mock.patch("senlin.common.messaging.RequestContextSerializer")
    @mock.patch("senlin.common.messaging.JsonPayloadSerializer")
    @mock.patch("oslo_messaging.get_rpc_client")
    def test_get_rpc_client(self, mock_rpc_client, mock_json_serializer,
                            mock_context_serializer, mock_target):
        topic = 'fake'
        client = mock.Mock()
        context = mock.Mock()
        server = mock.Mock()
        serializer = mock.Mock()
        target = mock.Mock()

        mock_context_serializer.return_value = context
        mock_json_serializer.return_value = serializer
        mock_rpc_client.return_value = client
        mock_target.return_value = target

        result = messaging.get_rpc_client(topic, server)

        mock_rpc_client.assert_called_once_with(
            None, target, serializer=context
        )
        mock_target.assert_called_once_with(
            topic=topic, server=server, version=consts.RPC_API_VERSION_BASE
        )
        mock_json_serializer.assert_called_once_with()
        mock_context_serializer.assert_called_once_with(serializer)

        self.assertEqual(client, result)

    @mock.patch("oslo_messaging.Target")
    @mock.patch("senlin.common.messaging.RequestContextSerializer")
    @mock.patch("senlin.common.messaging.JsonPayloadSerializer")
    @mock.patch("oslo_messaging.get_rpc_client")
    def test_get_rpc_client_with_serializer(self, mock_rpc_client,
                                            mock_json_serializer,
                                            mock_context_serializer,
                                            mock_target):
        topic = 'fake'
        client = mock.Mock()
        context = mock.Mock()
        custom_serializer = mock.Mock(name='custom')
        server = mock.Mock()
        target = mock.Mock()

        mock_context_serializer.return_value = context
        mock_json_serializer.return_value = custom_serializer
        mock_rpc_client.return_value = client
        mock_target.return_value = target

        result = messaging.get_rpc_client(
            topic, server, serializer=custom_serializer
        )

        mock_rpc_client.assert_called_once_with(
            None, target, serializer=context
        )
        mock_target.assert_called_once_with(
            topic=topic, server=server, version=consts.RPC_API_VERSION_BASE
        )
        mock_json_serializer.assert_not_called()
        mock_context_serializer.assert_called_once_with(custom_serializer)

        self.assertEqual(client, result)
