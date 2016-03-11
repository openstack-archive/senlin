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
import copy
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
        kwargs = {'key': 'value'}
        rpcapi = rpc_client.EngineClient()
        msg = rpcapi.make_msg(method, **kwargs)

        # with no version
        res = rpcapi.call(self.context, msg)

        self.assertEqual(client, rpcapi._client)
        client.call.assert_called_once_with(self.context, 'fake_method',
                                            key='value')
        self.assertEqual(res, client.call.return_value)

        # with version
        res = rpcapi.call(self.context, msg, version='123')
        client.prepare.assert_called_once_with(version='123')
        new_client = client.prepare.return_value
        new_client.call.assert_called_once_with(self.context, 'fake_method',
                                                key='value')
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

    def test_credential_create(self):
        self._test_engine_api('credential_create', 'call',
                              cred='cred', attrs='foo')

    def test_credential_get(self):
        self._test_engine_api('credential_get', 'call', query=mock.ANY)

    def test_credential_update(self):
        self._test_engine_api('credential_update', 'call',
                              cred=mock.ANY, attrs=mock.ANY)

    def test_profile_type_list(self):
        self._test_engine_api('profile_type_list', 'call')

    def test_profile_type_get(self):
        self._test_engine_api('profile_type_get', 'call',
                              type_name='a-profile-type')

    def test_profile_list(self):
        default_args = {
            'limit': mock.ANY,
            'marker': mock.ANY,
            'sort': mock.ANY,
            'filters': mock.ANY,
            'project_safe': mock.ANY,
        }
        self._test_engine_api('profile_list', 'call', **default_args)

    def test_profile_create(self):
        default_args = {
            'name': mock.ANY,
            'spec': mock.ANY,
            'metadata': mock.ANY,
        }
        self._test_engine_api('profile_create', 'call', **default_args)

    def test_profile_get(self):
        self._test_engine_api('profile_get', 'call', identity='a-profile')

    def test_profile_update(self):
        default_args = {
            'profile_id': 'aaaa-bbbb-cccc',
            'name': mock.ANY,
            'metadata': mock.ANY,
        }
        self._test_engine_api('profile_update', 'call', **default_args)

    def test_profile_delete_cast(self):
        self._test_engine_api('profile_delete', 'cast', identity='a-profile')

    def test_profile_delete_call(self):
        self._test_engine_api('profile_delete', 'call', identity='a-profile')

    def test_policy_type_list(self):
        self._test_engine_api('policy_type_list', 'call')

    def test_policy_type_get(self):
        self._test_engine_api('policy_type_get', 'call',
                              type_name='a-profile-type')

    def test_policy_list(self):
        default_args = {
            'limit': mock.ANY,
            'marker': mock.ANY,
            'sort': mock.ANY,
            'filters': mock.ANY,
            'project_safe': mock.ANY,
        }
        self._test_engine_api('policy_list', 'call', **default_args)

    def test_policy_create(self):
        default_args = {
            'name': mock.ANY,
            'spec': mock.ANY,
        }
        self._test_engine_api('policy_create', 'call', **default_args)

    def test_policy_get(self):
        self._test_engine_api('policy_get', 'call', identity='a-policy')

    def test_policy_update(self):
        default_args = {
            'identity': 'aaaa-bbbb-cccc',
            'name': mock.ANY,
        }
        self._test_engine_api('policy_update', 'call', **default_args)

    def test_policy_delete_cast(self):
        self._test_engine_api('policy_delete', 'cast', identity='a-policy')

    def test_policy_delete_call(self):
        self._test_engine_api('policy_delete', 'call', identity='a-policy')

    def test_cluster_list(self):
        default_args = {
            'limit': mock.ANY,
            'marker': mock.ANY,
            'sort': mock.ANY,
            'filters': mock.ANY,
            'project_safe': mock.ANY,
        }
        self._test_engine_api('cluster_list', 'call', **default_args)

    def test_cluster_create(self):
        kwargs = {
            'name': 'mycluster',
            'desired_capacity': 0,
            'profile_id': 'aaaa-bbbb-cccc',
            'min_size': 0,
            'max_size': 0,
            'metadata': None,
            'timeout': None
        }

        self._test_engine_api('cluster_create', 'call', **kwargs)

    def test_cluster_get(self):
        self._test_engine_api('cluster_get', 'call', identity='a-cluster')

    def test_cluster_add_nodes(self):
        self._test_engine_api('cluster_add_nodes', 'call',
                              identity='a-cluster',
                              nodes=['node1', 'node2'])

    def test_cluster_del_nodes(self):
        self._test_engine_api('cluster_del_nodes', 'call',
                              identity='a-cluster',
                              nodes=['node3', 'node4'])

    def test_cluster_scale_out(self):
        self._test_engine_api('cluster_scale_out', 'call',
                              identity='a-cluster',
                              count=1)

    def test_cluster_scale_in(self):
        self._test_engine_api('cluster_scale_in', 'call',
                              identity='a-cluster',
                              count=1)

    def test_cluster_update(self):
        kwargs = {
            'identity': 'a-cluster',
            'name': 'new-name',
            'profile_id': 'new_profile',
            'metadata': {'key': 'value'},
            'timeout': 120
        }
        self._test_engine_api('cluster_update', 'call', **kwargs)

    def test_cluster_delete_cast(self):
        self._test_engine_api('cluster_delete', 'cast', identity='a-cluster')

    def test_cluster_delete_call(self):
        self._test_engine_api('cluster_delete', 'call', identity='a-cluster')

    def test_cluster_check(self):
        self._test_engine_api('cluster_check', 'call', identity='a-cluster',
                              params=None)

    def test_cluster_recover(self):
        self._test_engine_api('cluster_recover', 'call', identity='a-cluster',
                              params=None)

    def test_cluster_recover_with_params(self):
        params = {'operation': 'REBUILD'}
        self._test_engine_api('cluster_recover', 'call', identity='a-cluster',
                              params=params)

    def test_node_list(self):
        default_args = {
            'cluster_id': mock.ANY,
            'limit': mock.ANY,
            'marker': mock.ANY,
            'sort': mock.ANY,
            'filters': mock.ANY,
            'project_safe': mock.ANY,
        }
        self._test_engine_api('node_list', 'call', **default_args)

    def test_node_create(self):
        kwargs = {
            'name': 'mynode',
            'profile_id': 'aaaa-bbbb-cccc',
            'cluster_id': 'xxxx-yyyy-zzzz',
            'role': None,
            'metadata': None
        }

        self._test_engine_api('node_create', 'call', **kwargs)

    def test_node_get(self):
        self._test_engine_api('node_get', 'call', identity='a-node',
                              show_details=mock.ANY)

    def test_node_update(self):
        kwargs = {
            'identity': 'a-cluster',
            'name': 'new-name',
            'profile_id': 'new_profile',
            'role': 'master',
            'metadata': {'key': 'value'}
        }
        self._test_engine_api('node_update', 'call', **kwargs)

    def test_node_delete_cast(self):
        self._test_engine_api('node_delete', 'cast', identity='a-node')

    def test_node_delete_call(self):
        self._test_engine_api('node_delete', 'call', identity='a-node')

    def test_node_check(self):
        self._test_engine_api('node_check', 'call', identity='a-node',
                              params=None)

    def test_node_recover(self):
        self._test_engine_api('node_recover', 'call', identity='a-node',
                              params=None)

    def test_node_recover_with_params(self):
        params = {'operation': 'REBUILD'}
        self._test_engine_api('node_recover', 'call', identity='a-cluster',
                              params=params)

    def test_action_list(self):
        default_args = {
            'filters': mock.ANY,
            'limit': mock.ANY,
            'marker': mock.ANY,
            'sort': mock.ANY,
            'project_safe': mock.ANY,
        }
        self._test_engine_api('action_list', 'call', **default_args)

    def test_cluster_policy_list(self):
        kwargs = {
            'cluster_id': 'a-cluster',
            'filters': mock.ANY,
            'sort': mock.ANY,
        }
        call_kwargs = copy.deepcopy(kwargs)
        call_kwargs['identity'] = 'a-cluster'
        del call_kwargs['cluster_id']
        expected_message = self.rpcapi.make_msg('cluster_policy_list',
                                                **call_kwargs)
        kwargs['expected_message'] = expected_message
        self._test_engine_api('cluster_policy_list', 'call', **kwargs)

    def test_cluster_policy_attach(self):
        kwargs = {
            'cluster_id': 'a-cluster',
            'policy_id': 'a-policy',
            'enabled': mock.ANY,
        }

        call_kwargs = {
            'identity': 'a-cluster',
            'policy': 'a-policy',
            'enabled': mock.ANY,
        }
        expected_message = self.rpcapi.make_msg('cluster_policy_attach',
                                                **call_kwargs)
        kwargs['expected_message'] = expected_message
        self._test_engine_api('cluster_policy_attach', 'call', **kwargs)

    def test_cluster_policy_detach(self):
        kwargs = {
            'cluster_id': 'a-cluster',
            'policy_id': 'a-policy',
        }

        call_kwargs = {
            'identity': 'a-cluster',
            'policy': 'a-policy',
        }
        expected_message = self.rpcapi.make_msg('cluster_policy_detach',
                                                **call_kwargs)
        kwargs['expected_message'] = expected_message
        self._test_engine_api('cluster_policy_detach', 'call', **kwargs)

    def test_cluster_policy_get(self):
        kwargs = {
            'cluster_id': 'a-cluster',
            'policy_id': 'a-policy',
        }

        call_kwargs = {
            'identity': 'a-cluster',
            'policy_id': 'a-policy',
        }
        expected_message = self.rpcapi.make_msg('cluster_policy_get',
                                                **call_kwargs)
        kwargs['expected_message'] = expected_message
        self._test_engine_api('cluster_policy_get', 'call', **kwargs)

    def test_cluster_policy_update(self):
        kwargs = {
            'cluster_id': 'a-cluster',
            'policy_id': 'a-policy',
            'enabled': True
        }

        call_kwargs = copy.deepcopy(kwargs)
        call_kwargs['identity'] = 'a-cluster'
        call_kwargs['policy'] = 'a-policy'
        del call_kwargs['cluster_id']
        del call_kwargs['policy_id']
        expected_message = self.rpcapi.make_msg('cluster_policy_update',
                                                **call_kwargs)
        kwargs['expected_message'] = expected_message
        self._test_engine_api('cluster_policy_update', 'call', **kwargs)

    def test_action_create(self):
        kwargs = {
            'name': 'myaction',
            'cluster': 'aaaa-bbbb-cccc',
            'action': 'this is a script',
            'params': None,
        }

        self._test_engine_api('action_create', 'call', **kwargs)

    def test_action_get(self):
        self._test_engine_api('action_get', 'call', identity='an-action')

    def test_receiver_list(self):
        default_args = {
            'limit': mock.ANY,
            'marker': mock.ANY,
            'sort': mock.ANY,
            'filters': mock.ANY,
            'project_safe': mock.ANY,
        }
        self._test_engine_api('receiver_list', 'call', **default_args)

    def test_receiver_create(self):
        kwargs = {
            'name': 'myreceiver',
            'type_name': 'webhook',
            'cluster_id': 'fake cluster',
            'action': 'sing_a_song',
            'actor': {'key': 'value'},
            'params': {'pname': 'pvalue'},
        }

        self._test_engine_api('receiver_create', 'call', **kwargs)

    def test_receiver_get(self):
        self._test_engine_api('receiver_get', 'call',
                              identity='wh_name', project_safe=True)

    def test_receiver_delete_cast(self):
        self._test_engine_api('receiver_delete', 'cast', identity='wh_name')

    def test_receiver_delete_call(self):
        self._test_engine_api('receiver_delete', 'call', identity='wh_name')

    def test_webhook_trigger(self):
        self._test_engine_api('webhook_trigger', 'call', identity='wh_name',
                              params={'pname': 'pvalue'})

    def test_event_list(self):
        default_args = {
            'filters': mock.ANY,
            'limit': mock.ANY,
            'marker': mock.ANY,
            'sort': mock.ANY,
            'project_safe': mock.ANY,
        }
        self._test_engine_api('event_list', 'call', **default_args)

    def test_get_revision(self):
        self._test_engine_api('get_revision', 'call')
