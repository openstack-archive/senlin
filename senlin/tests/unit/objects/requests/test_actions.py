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
import copy

from senlin.objects.requests import actions
from senlin.tests.unit.common import base as test_base


class TestActionCreate(test_base.SenlinTestCase):

    body = {
        'name': 'test-action',
        'cluster_id': 'test-cluster',
        'action': 'CLUSTER_CREATE',
    }

    def test_action_create_request_body(self):
        sot = actions.ActionCreateRequestBody(**self.body)
        self.assertEqual('test-action', sot.name)
        self.assertEqual('test-cluster', sot.cluster_id)
        self.assertEqual('CLUSTER_CREATE', sot.action)

        sot.obj_set_defaults()

        self.assertEqual({}, sot.inputs)

    def test_action_create_request_body_full(self):
        body = copy.deepcopy(self.body)
        body['inputs'] = {'foo': 'bar'}
        sot = actions.ActionCreateRequestBody(**body)
        self.assertEqual('test-action', sot.name)
        self.assertEqual('test-cluster', sot.cluster_id)
        self.assertEqual('CLUSTER_CREATE', sot.action)
        self.assertEqual({'foo': 'bar'}, sot.inputs)

    def test_action_create_request_body_to_primitive(self):
        sot = actions.ActionCreateRequestBody(**self.body)
        res = sot.obj_to_primitive()
        self.assertEqual(
            {
                'name': u'test-action',
                'cluster_id': u'test-cluster',
                'action': u'CLUSTER_CREATE',
            },
            res['senlin_object.data']
        )
        self.assertEqual('ActionCreateRequestBody',
                         res['senlin_object.name'])
        self.assertEqual('senlin', res['senlin_object.namespace'])
        self.assertEqual('1.0', res['senlin_object.version'])
        self.assertIn('name', res['senlin_object.changes'])
        self.assertIn('cluster_id', res['senlin_object.changes'])

    def test_action_create_request_to_primitive(self):
        body = actions.ActionCreateRequestBody(**self.body)
        request = {'action': body}
        sot = actions.ActionCreateRequest(**request)
        self.assertIsInstance(sot.action, actions.ActionCreateRequestBody)

        self.assertEqual('test-action', sot.action.name)
        self.assertEqual('test-cluster', sot.action.cluster_id)

        res = sot.obj_to_primitive()
        self.assertEqual(['action'], res['senlin_object.changes'])
        self.assertEqual('ActionCreateRequest', res['senlin_object.name'])
        self.assertEqual('senlin', res['senlin_object.namespace'])
        self.assertEqual('1.0', res['senlin_object.version'])
        data = res['senlin_object.data']['action']
        self.assertIn('cluster_id', data['senlin_object.changes'])
        self.assertIn('name', data['senlin_object.changes'])
        self.assertEqual('ActionCreateRequestBody',
                         data['senlin_object.name'])
        self.assertEqual('senlin', data['senlin_object.namespace'])
        self.assertEqual('1.0', data['senlin_object.version'])

        self.assertEqual(
            {
                'name': u'test-action',
                'cluster_id': u'test-cluster',
                'action': u'CLUSTER_CREATE',
            },
            data['senlin_object.data']
        )


class TestActionList(test_base.SenlinTestCase):
    def test_action_list_request_body_full(self):
        params = {
            'name': ['node_create_12345678'],
            'action': ['NODE_CREATE'],
            'target': ['0df0931b-e251-4f2e-8719-4effda3627bb'],
            'status': ['READY'],
            'limit': 5,
            'marker': 'f1ed0d50-7651-4599-a8cb-c86e9c7123f6',
            'sort': 'name:asc',
            'project_safe': False,
        }
        sot = actions.ActionListRequest(**params)
        self.assertEqual(['node_create_12345678'], sot.name)
        self.assertEqual(['NODE_CREATE'], sot.action)
        self.assertEqual(['0df0931b-e251-4f2e-8719-4effda3627bb'], sot.target)
        self.assertEqual(['READY'], sot.status)
        self.assertEqual(5, sot.limit)
        self.assertEqual('f1ed0d50-7651-4599-a8cb-c86e9c7123f6', sot.marker)
        self.assertEqual('name:asc', sot.sort)
        self.assertFalse(sot.project_safe)

    def test_action_list_request_body_default(self):
        sot = actions.ActionListRequest()
        sot.obj_set_defaults()
        self.assertTrue(sot.project_safe)


class TestActionGet(test_base.SenlinTestCase):

    body = {
        'identity': 'test-action'
    }

    def test_action_get_request(self):
        sot = actions.ActionGetRequest(**self.body)
        self.assertEqual('test-action', sot.identity)


class TestActionDelete(test_base.SenlinTestCase):

    body = {
        'identity': 'test-action'
    }

    def test_action_get_request(self):
        sot = actions.ActionDeleteRequest(**self.body)
        self.assertEqual('test-action', sot.identity)
