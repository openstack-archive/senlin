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
import six
from webob import exc

from senlin.api.middleware import fault
from senlin.api.openstack.v1 import cluster_policies as cp_mod
from senlin.common import exception as senlin_exc
from senlin.common import policy
from senlin.rpc import client as rpc_client
from senlin.tests.unit.api import shared
from senlin.tests.unit.common import base


@mock.patch.object(policy, 'enforce')
class ClusterPolicyControllerTest(shared.ControllerTest, base.SenlinTestCase):
    '''Tests the API class which acts as the WSGI controller.'''

    def setUp(self):
        super(ClusterPolicyControllerTest, self).setUp()

        # Create WSGI controller instance
        class DummyConfig(object):
            bind_port = 8778

        cfgopts = DummyConfig()
        self.controller = cp_mod.ClusterPolicyController(options=cfgopts)

    def test_cluster_policy_index(self, mock_enforce):
        self._mock_enforce_setup(mock_enforce, 'index', True)
        cid = 'test_cluster'
        req = self._get('/cluster_policies/%s' % cid)

        engine_resp = [
            {
                'id': 'fake_id',
                'cluster_id': 'fake cluster id',
                'policy_id': 'fake policy id',
                'enabled': True,
                'data': {},
                'cluster_name': 'test_cluster',
                'policy_name': 'test_policy',
                'policy_type': 'ScalingPolicy',
            }
        ]

        mock_call = self.patchobject(rpc_client.EngineClient, 'call',
                                     return_value=engine_resp)

        result = self.controller.index(req, cluster_id=cid)

        default_args = {'sort': None, 'filters': None, 'identity': cid}
        mock_call.assert_called_with(req.context,
                                     ('cluster_policy_list', default_args))

        expected = {'cluster_policies': engine_resp}
        self.assertEqual(expected, result)

    @mock.patch.object(rpc_client.EngineClient, 'call')
    def test_cluster_policy_index_valid_filter_params(self, mock_call,
                                                      mock_enforce):
        self._mock_enforce_setup(mock_enforce, 'index', True)
        cid = 'FAKE_CLUSTER'
        params = {
            'sort': 'fake sorting string',
            'enabled': 'True',
        }
        req = self._get('/cluster_policies/%s' % cid, params=params)
        mock_call.return_value = []

        self.controller.index(req, cluster_id=cid)

        rpc_call_args, _ = mock_call.call_args
        engine_args = rpc_call_args[1][1]

        self.assertEqual(3, len(engine_args))
        self.assertIn('sort', engine_args)
        self.assertIn('filters', engine_args)
        self.assertNotIn('balrog', engine_args)

    @mock.patch.object(rpc_client.EngineClient, 'call')
    def test_cluster_policy_index_invalid_params(self, mock_call,
                                                 mock_enforce):
        self._mock_enforce_setup(mock_enforce, 'index', True)
        cid = 'FAKE_CLUSTER'
        params = {
            'enabled': 'True',
            'balrog': 'you shall not pass!'
        }
        req = self._get('/cluster_policies/%s' % cid, params=params)
        mock_call.return_value = []

        ex = self.assertRaises(exc.HTTPBadRequest, self.controller.index,
                               req, cluster_id=cid)
        self.assertEqual('Invalid parameter balrog',
                         six.text_type(ex))

    def test_cluster_policy_index_denied_policy(self, mock_enforce):
        self._mock_enforce_setup(mock_enforce, 'index', False)
        cid = 'FAKE_CLUSTER'
        req = self._get('/cluster_policy/%s' % cid)

        resp = shared.request_with_middleware(fault.FaultWrapper,
                                              self.controller.index,
                                              req, cluster_id=cid)

        self.assertEqual(403, resp.status_int)
        self.assertIn('403 Forbidden', six.text_type(resp))

    def test_cluster_policy_get_success(self, mock_enforce):
        self._mock_enforce_setup(mock_enforce, 'get', True)
        cid = 'FAKE_CLUSTER'
        pid = 'FAKE_POLICY'
        req = self._get('/cluster_policies/%(cid)s/%(pid)s'
                        '' % {'cid': cid, 'pid': pid})

        engine_resp = {
            'id': 'fake_id',
            'cluster_id': cid,
            'policy_id': pid,
            'enabled': True,
            'data': {},
            'cluster_name': 'test_cluster',
            'policy_name': 'test_policy',
            'policy_type': 'ScalingPolicy',
        }

        mock_call = self.patchobject(rpc_client.EngineClient, 'call',
                                     return_value=engine_resp)
        response = self.controller.get(req, cluster_id=cid, policy_id=pid)

        mock_call.assert_called_once_with(
            req.context, ('cluster_policy_get',
                          {'identity': cid, 'policy_id': pid}))

        self.assertEqual({'cluster_policy': engine_resp}, response)

    def test_cluster_policy_get_not_found(self, mock_enforce):
        self._mock_enforce_setup(mock_enforce, 'get', True)
        cid = 'FAKE_CLUSTER'
        pid = 'FAKE_POLICY'
        req = self._get('/cluster_policies/%(cid)s/%(pid)s'
                        '' % {'cid': cid, 'pid': pid})

        error = senlin_exc.PolicyBindingNotFound(policy=pid, identity=cid)
        mock_call = self.patchobject(rpc_client.EngineClient, 'call')
        mock_call.side_effect = shared.to_remote_error(error)

        resp = shared.request_with_middleware(fault.FaultWrapper,
                                              self.controller.get,
                                              req, cluster_id=cid,
                                              policy_id=pid)

        self.assertEqual(404, resp.json['code'])
        self.assertEqual('PolicyBindingNotFound', resp.json['error']['type'])

    def test_action_get_denied_policy(self, mock_enforce):
        self._mock_enforce_setup(mock_enforce, 'get', False)
        cid = 'FAKE_CLUSTER'
        pid = 'FAKE_POLICY'
        req = self._get('/cluster_policies/%(cid)s/%(pid)s'
                        '' % {'cid': cid, 'pid': pid})

        resp = shared.request_with_middleware(fault.FaultWrapper,
                                              self.controller.get,
                                              req, cluster_id=cid,
                                              policy_id=pid)

        self.assertEqual(403, resp.status_int)
        self.assertIn('403 Forbidden', six.text_type(resp))
