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

from oslo_messaging.rpc import dispatcher as rpc

from senlin.common import exception
from senlin.engine import environment
from senlin.engine import service
from senlin.tests.unit.common import base
from senlin.tests.unit.common import utils
from senlin.tests.unit import fakes


class PolicyTypeTest(base.SenlinTestCase):

    def setUp(self):
        super(PolicyTypeTest, self).setUp()
        self.ctx = utils.dummy_context(project='policy_type_test_project')
        self.eng = service.EngineService('host-a', 'topic-a')
        self.eng.init_tgm()
        environment.global_env().register_policy('TestPolicy',
                                                 fakes.TestPolicy)

    def test_policy_type_list(self):
        types = self.eng.policy_type_list(self.ctx)
        self.assertIsInstance(types, list)
        self.assertIn({'name': 'TestPolicy'}, types)
        self.assertNotIn({'name': 'some-weird-stuff'}, types)

    def test_policy_type_schema(self):
        type_name = 'TestPolicy'
        expected = {
            'spec': {
                'KEY1': {
                    'type': 'String',
                    'readonly': False,
                    'required': False,
                    'description': 'key1',
                    'default': 'default1',
                },
                'KEY2': {
                    'type': 'Integer',
                    'readonly': False,
                    'required': True,
                    'description': 'key2',
                },
            }
        }

        schema = self.eng.policy_type_schema(self.ctx, type_name=type_name)
        self.assertEqual(expected, schema)

    def test_policy_type_schema_nonexist(self):
        ex = self.assertRaises(rpc.ExpectedException,
                               self.eng.policy_type_schema,
                               self.ctx, type_name='Bogus')
        self.assertEqual(exception.PolicyTypeNotFound, ex.exc_info[0])
