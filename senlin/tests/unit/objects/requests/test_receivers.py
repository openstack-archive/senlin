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
import six

from oslo_config import cfg

from senlin.common import consts
from senlin.objects.requests import receivers
from senlin.tests.unit.common import base as test_base

CONF = cfg.CONF
CONF.import_opt('default_action_timeout', 'senlin.common.config')


class TestReceiverCreate(test_base.SenlinTestCase):

    body = {
        'name': 'test-receiver',
        'type': 'message',
    }

    def test_receiver_create_request_body(self):
        sot = receivers.ReceiverCreateRequestBody(**self.body)
        self.assertEqual('test-receiver', sot.name)
        self.assertEqual('message', sot.type)

        sot.obj_set_defaults()

        self.assertEqual({}, sot.actor)
        self.assertEqual({}, sot.params)
        self.assertFalse(sot.obj_attr_is_set('action'))
        self.assertFalse(sot.obj_attr_is_set('cluster_id'))

    def test_receiver_create_request_body_full(self):
        body = copy.deepcopy(self.body)
        body['type'] = 'webhook'
        body['cluster_id'] = 'cluster-01'
        body['action'] = consts.CLUSTER_SCALE_OUT
        body['actor'] = {'user': 'user1', 'password': 'pass1'}
        body['params'] = {'count': '1'}
        sot = receivers.ReceiverCreateRequestBody(**body)
        self.assertEqual('test-receiver', sot.name)
        self.assertEqual('webhook', sot.type)
        self.assertEqual('cluster-01', sot.cluster_id)
        self.assertEqual(consts.CLUSTER_SCALE_OUT, sot.action)
        self.assertEqual({'user': 'user1', 'password': 'pass1'}, sot.actor)
        self.assertEqual({'count': '1'}, sot.params)

    def test_receiver_create_request_body_invalid_type(self):
        body = copy.deepcopy(self.body)
        body['type'] = 'Bogus'
        ex = self.assertRaises(ValueError, receivers.ReceiverCreateRequestBody,
                               **body)
        self.assertEqual("Value 'Bogus' is not acceptable for field 'type'.",
                         six.text_type(ex))

    def test_receiver_create_request_body_invalid_action(self):
        body = copy.deepcopy(self.body)
        body['type'] = 'webhook'
        body['cluster_id'] = 'cluster-01'
        body['action'] = 'Foo'

        ex = self.assertRaises(ValueError, receivers.ReceiverCreateRequestBody,
                               **body)
        self.assertEqual("Value 'Foo' is not acceptable for field 'action'.",
                         six.text_type(ex))

    def test_receiver_create_request(self):
        body = receivers.ReceiverCreateRequestBody(**self.body)
        request = {'receiver': body}
        sot = receivers.ReceiverCreateRequest(**request)
        self.assertIsInstance(sot.receiver,
                              receivers.ReceiverCreateRequestBody)
        self.assertEqual('test-receiver', sot.receiver.name)
        self.assertEqual('message', sot.receiver.type)
