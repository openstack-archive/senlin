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


from senlin.engine.actions import custom_action as ca
from senlin.tests.unit.common import base
from senlin.tests.unit.common import utils


class CustomActionTest(base.SenlinTestCase):

    def setUp(self):
        super(CustomActionTest, self).setUp()
        self.ctx = utils.dummy_context()

    def test_init(self):
        obj = ca.CustomAction('OBJID', 'OBJECT_ACTION', self.ctx)
        self.assertIsNotNone(obj)

    def test_execute(self):
        obj = ca.CustomAction('OBJID', 'OBJECT_ACTION', self.ctx)

        params = {'key': 'value'}
        res = obj.execute(**params)

        self.assertEqual(obj.RES_OK, res[0])
        self.assertEqual('', res[1])
