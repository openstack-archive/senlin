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
from senlin.api.openstack.v1 import events
from senlin.common import exception as senlin_exc
from senlin.common import policy
from senlin.objects.requests import events as vore
from senlin.rpc import client as rpc_client
from senlin.tests.unit.api import shared
from senlin.tests.unit.common import base


@mock.patch.object(policy, 'enforce')
class EventControllerTest(shared.ControllerTest, base.SenlinTestCase):
    '''Tests the API class which acts as the WSGI controller.'''

    def setUp(self):
        super(EventControllerTest, self).setUp()
        # Create WSGI controller instance

        class DummyConfig(object):
            bind_port = 8778

        cfgopts = DummyConfig()
        self.controller = events.EventController(options=cfgopts)

    def test_event_index(self, mock_enforce):
        self._mock_enforce_setup(mock_enforce, 'index', True)
        req = self._get('/events')

        engine_resp = [
            {
                "action": "create",
                "cluster_id": None,
                "id": "2d255b9c-8f36-41a2-a137-c0175ccc29c3",
                "level": "20",
                "oid": "0df0931b-e251-4f2e-8719-4ebfda3627ba",
                "oname": "node009",
                "otype": "NODE",
                "project": "6e18cc2bdbeb48a5b3cad2dc499f6804",
                "status": "CREATING",
                "status_reason": "Initializing",
                "timestamp": "2015-03-05T08:53:15.000000",
                "user": "a21ded6060534d99840658a777c2af5a"
            }
        ]

        mock_call = self.patchobject(rpc_client.EngineClient, 'call2',
                                     return_value=engine_resp)

        result = self.controller.index(req)

        expected = {'events': engine_resp}
        self.assertEqual(expected, result)
        mock_call.assert_called_with(req.context,
                                     'event_list2', mock.ANY)

        request = mock_call.call_args[0][2]
        self.assertIsInstance(request, vore.EventListRequest)
        self.assertTrue(request.project_safe)

    @mock.patch.object(rpc_client.EngineClient, 'call2')
    def test_event_index_whitelists_params(self, mock_call, mock_enforce):
        self._mock_enforce_setup(mock_enforce, 'index', True)
        marker_uuid = '8216a86c-1bdc-442e-b493-329385d37cbd'
        params = {
            'otype': 'NODE',
            'oname': 'mynode1',
            'action': 'NODE_CREATE',
            'level': 'ERROR',
            'limit': 10,
            'marker': marker_uuid,
            'sort': 'timestamp',
            'global_project': False,
        }

        req = self._get('/events', params=params)

        mock_call.return_value = []

        result = self.controller.index(req)
        expected = {'events': []}
        self.assertEqual(expected, result)
        mock_call.assert_called_with(req.context,
                                     'event_list2', mock.ANY)
        request = mock_call.call_args[0][2]
        self.assertIsInstance(request, vore.EventListRequest)
        self.assertEqual(['NODE'], request.otype)
        self.assertEqual(['mynode1'], request.oname)
        self.assertEqual(['NODE_CREATE'], request.action)
        self.assertEqual(['ERROR'], request.level)
        self.assertEqual(10, request.limit)
        self.assertEqual(marker_uuid, request.marker)
        self.assertEqual('timestamp', request.sort)
        self.assertTrue(request.project_safe)

    @mock.patch.object(rpc_client.EngineClient, 'call2')
    def test_event_index_whitelists_invalid_params(self, mock_call,
                                                   mock_enforce):
        self._mock_enforce_setup(mock_enforce, 'index', True)
        params = {
            'balrog': 'you shall not pass!',
        }
        req = self._get('/events', params=params)
        ex = self.assertRaises(exc.HTTPBadRequest,
                               self.controller.index, req)

        self.assertEqual("Invalid parameter balrog",
                         str(ex))
        self.assertFalse(mock_call.called)

    @mock.patch.object(rpc_client.EngineClient, 'call2')
    def test_event_index_with_bad_schema(self, mock_call, mock_enforce):
        self._mock_enforce_setup(mock_enforce, 'index', True)
        params = {'level': 'fake'}
        req = self._get('/events', params=params)

        ex = self.assertRaises(exc.HTTPBadRequest,
                               self.controller.index,
                               req)

        self.assertEqual("Field value fake is invalid",
                         six.text_type(ex))
        self.assertEqual(0, mock_call.call_count)

    @mock.patch.object(rpc_client.EngineClient, 'call2')
    def test_event_index_limit_not_int(self, mock_call, mock_enforce):
        self._mock_enforce_setup(mock_enforce, 'index', True)
        params = {'limit': 'not-int'}
        req = self._get('/event', params=params)

        ex = self.assertRaises(exc.HTTPBadRequest,
                               self.controller.index, req)

        self.assertEqual("invalid literal for int() with base 10: 'not-int'",
                         six.text_type(ex))
        self.assertFalse(mock_call.called)

    @mock.patch.object(rpc_client.EngineClient, 'call2')
    def test_event_index_global_project_true(self, mock_call, mock_enforce):
        self._mock_enforce_setup(mock_enforce, 'index', True)
        params = {'global_project': 'True'}
        req = self._get('/events', params=params)

        self.controller.index(req)

        request = mock_call.call_args[0][2]
        self.assertFalse(request.project_safe)

    @mock.patch.object(rpc_client.EngineClient, 'call2')
    def test_events_index_global_project_false(self, mock_call, mock_enforce):
        self._mock_enforce_setup(mock_enforce, 'index', True)
        params = {'global_project': 'False'}
        req = self._get('/events', params=params)

        self.controller.index(req)

        request = mock_call.call_args[0][2]
        self.assertTrue(request.project_safe)

    @mock.patch.object(rpc_client.EngineClient, 'call2')
    def test_event_index_global_project_not_bool(self, mock_call,
                                                 mock_enforce):
        self._mock_enforce_setup(mock_enforce, 'index', True)
        params = {'global_project': 'No'}
        req = self._get('/events', params=params)

        ex = self.assertRaises(exc.HTTPBadRequest,
                               self.controller.index, req)

        self.assertEqual("Invalid value 'No' specified for 'global_project'",
                         six.text_type(ex))
        self.assertFalse(mock_call.called)

    def test_index_denied_policy(self, mock_enforce):
        self._mock_enforce_setup(mock_enforce, 'index', False)
        req = self._get('/events')

        resp = shared.request_with_middleware(fault.FaultWrapper,
                                              self.controller.index,
                                              req)
        self.assertEqual(403, resp.status_int)
        self.assertIn('403 Forbidden', six.text_type(resp))

    def test_event_get_success(self, mock_enforce):
        self._mock_enforce_setup(mock_enforce, 'get', True)
        event_id = "2d255b9c-8f36-41a2-a137-c0175ccc29c3"
        req = self._get('/events/%(event_id)s' % {'event_id': event_id})

        engine_resp = {
            "action": "create",
            "cluster_id": None,
            "id": "2d255b9c-8f36-41a2-a137-c0175ccc29c3",
            "level": "20",
            "oid": "0df0931b-e251-4f2e-8719-4ebfda3627ba",
            "oname": "node009",
            "otype": "NODE",
            "project": "6e18cc2bdbeb48a5b3cad2dc499f6804",
            "status": "CREATING",
            "status_reason": "Initializing",
            "timestamp": "2015-03-05T08:53:15.000000",
            "user": "a21ded6060534d99840658a777c2af5a"
        }

        mock_call = self.patchobject(rpc_client.EngineClient, 'call2',
                                     return_value=engine_resp)
        response = self.controller.get(req, event_id=event_id)
        expected = {'event': engine_resp}
        self.assertEqual(expected, response)

        mock_call.assert_called_once_with(
            req.context, 'event_get2', mock.ANY)
        request = mock_call.call_args[0][2]
        self.assertIsInstance(request, vore.EventGetRequest)
        self.assertEqual(event_id, request.identity)

    def test_event_get_not_found(self, mock_enforce):
        self._mock_enforce_setup(mock_enforce, 'get', True)
        event_id = 'non-existent-event'
        req = self._get('/events/%(event_id)s' % {'event_id': event_id})

        error = senlin_exc.ResourceNotFound(type='event', id=event_id)
        mock_call = self.patchobject(rpc_client.EngineClient, 'call2')
        mock_call.side_effect = shared.to_remote_error(error)

        resp = shared.request_with_middleware(fault.FaultWrapper,
                                              self.controller.get,
                                              req, event_id=event_id)

        self.assertEqual(404, resp.json['code'])
        self.assertEqual('ResourceNotFound', resp.json['error']['type'])

    def test_event_get_denied_policy(self, mock_enforce):
        self._mock_enforce_setup(mock_enforce, 'get', False)
        event_id = 'non-existent-event'
        req = self._get('/events/%(event_id)s' % {'event_id': event_id})

        resp = shared.request_with_middleware(fault.FaultWrapper,
                                              self.controller.get,
                                              req, event_id=event_id)

        self.assertEqual(403, resp.status_int)
        self.assertIn('403 Forbidden', six.text_type(resp))
