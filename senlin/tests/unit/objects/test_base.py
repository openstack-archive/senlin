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

from senlin.objects import base as obj_base
from senlin.tests.unit.common import base


class TestBaseObject(base.SenlinTestCase):

    def test_base_class(self):
        obj = obj_base.SenlinObject()
        self.assertEqual(obj_base.SenlinObject.OBJ_PROJECT_NAMESPACE,
                         obj.OBJ_PROJECT_NAMESPACE)
        self.assertEqual(obj_base.SenlinObject.VERSION,
                         obj.VERSION)
