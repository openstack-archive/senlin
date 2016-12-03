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
from oslo_config import cfg
import testtools

from senlin.engine import event


class TestEvent(testtools.TestCase):

    @mock.patch('stevedore.named.NamedExtensionManager')
    def test_load_dispatcher(self, mock_mgr):
        cfg.CONF.set_override('dispatchers', ['foo', 'bar'], enforce_type=True)

        res = event.load_dispatcher()

        self.assertIsNone(res)
        mock_mgr.assert_called_once_with(
            namespace='senlin.dispatchers',
            names=['foo', 'bar'],
            invoke_on_load=True,
            propagate_map_exceptions=True)
