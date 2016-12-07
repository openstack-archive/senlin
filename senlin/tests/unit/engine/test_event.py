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
from oslo_log import log as logging
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

    def test__event_data(self):
        entity = mock.Mock(id='ENTITY_ID')
        entity.name = 'FAKE_ENTITY'
        action = mock.Mock(action='ACTION', entity=entity)

        res = event._event_data(action)

        self.assertEqual({'name': 'FAKE_ENTITY', 'id': 'ENTITY_I',
                          'action': 'ACTION', 'phase': None, 'reason': None},
                         res)

    def test__event_data_with_phase_reason(self):
        entity = mock.Mock(id='ENTITY_ID')
        entity.name = 'FAKE_ENTITY'
        action = mock.Mock(action='ACTION', entity=entity)

        res = event._event_data(action, phase='PHASE1', reason='REASON1')

        self.assertEqual({'name': 'FAKE_ENTITY', 'id': 'ENTITY_I',
                          'action': 'ACTION', 'phase': 'PHASE1',
                          'reason': 'REASON1'},
                         res)

    def test__dump(self):
        saved_dispathers = event.dispatchers
        event.dispatchers = mock.Mock()
        action = mock.Mock()
        try:
            event._dump('LEVEL', action, 'Phase1', 'Reason1', 'Timestamp1')
            event.dispatchers.map_method.assert_called_once_with(
                'dump', 'LEVEL', action,
                phase='Phase1', reason='Reason1', timestamp='Timestamp1')
        finally:
            event.dispatchers = saved_dispathers

    def test__dump_with_exception(self):
        saved_dispathers = event.dispatchers
        event.dispatchers = mock.Mock()
        event.dispatchers.map_method.side_effect = Exception()
        action = mock.Mock()
        try:
            res = event._dump('LEVEL', action, 'Phase1', 'Reason1', 'TS1')

            self.assertIsNone(res)  # exception logged only
            event.dispatchers.map_method.assert_called_once_with(
                'dump', 'LEVEL', action,
                phase='Phase1', reason='Reason1', timestamp='TS1')
        finally:
            event.dispatchers = saved_dispathers


@mock.patch.object(event, '_event_data')
@mock.patch.object(event, '_dump')
class TestLogMethods(testtools.TestCase):

    def test_critical(self, mock_dump, mock_data):
        action = mock.Mock()

        res = event.critical(action, 'P1', 'R1', 'TS1')

        self.assertIsNone(res)
        mock_dump.assert_called_once_with(logging.CRITICAL, action,
                                          'P1', 'R1', 'TS1')
        mock_data.assert_called_once_with(action, 'P1', 'R1')

    def test_error(self, mock_dump, mock_data):
        action = mock.Mock()

        res = event.error(action, 'P1', 'R1', 'TS1')

        self.assertIsNone(res)
        mock_dump.assert_called_once_with(logging.ERROR, action,
                                          'P1', 'R1', 'TS1')
        mock_data.assert_called_once_with(action, 'P1', 'R1')

    def test_warning(self, mock_dump, mock_data):
        action = mock.Mock()

        res = event.warning(action, 'P1', 'R1', 'TS1')

        self.assertIsNone(res)
        mock_dump.assert_called_once_with(logging.WARNING, action,
                                          'P1', 'R1', 'TS1')
        mock_data.assert_called_once_with(action, 'P1', 'R1')

    def test_info(self, mock_dump, mock_data):
        action = mock.Mock()

        res = event.info(action, 'P1', 'R1', 'TS1')

        self.assertIsNone(res)
        mock_dump.assert_called_once_with(logging.INFO, action,
                                          'P1', 'R1', 'TS1')
        mock_data.assert_called_once_with(action, 'P1', 'R1')

    def test_debug(self, mock_dump, mock_data):
        action = mock.Mock()

        res = event.debug(action, 'P1', 'R1', 'TS1')

        self.assertIsNone(res)
        mock_dump.assert_called_once_with(logging.DEBUG, action,
                                          'P1', 'R1', 'TS1')
        mock_data.assert_called_once_with(action, 'P1', 'R1')
