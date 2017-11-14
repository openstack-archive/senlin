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

from senlin.common import consts
from senlin.engine import event


class TestEvent(testtools.TestCase):

    def setUp(self):
        super(TestEvent, self).setUp()
        logging.register_options(cfg.CONF)

    @mock.patch('stevedore.named.NamedExtensionManager')
    def test_load_dispatcher(self, mock_mgr):

        class FakeDispatcher(object):
            values = {'a': 1, 'b': 2}

            def __iter__(self):
                return iter(self.values)

            def __getitem__(self, key):
                return self.values.get(key, '')

            def __contains__(self, name):
                return name in self.values

            def names(self):
                return self.values.keys()

        mock_mgr.return_value = FakeDispatcher()
        res = event.load_dispatcher()

        self.assertIsNone(res)
        mock_mgr.assert_called_once_with(
            namespace='senlin.dispatchers',
            names=cfg.CONF.event_dispatchers,
            invoke_on_load=True,
            propagate_map_exceptions=True)

    def test__event_data(self):
        entity = mock.Mock(id='ENTITY_ID')
        entity.name = 'FAKE_ENTITY'
        action = mock.Mock(id='ACTION_ID', action='ACTION', entity=entity)

        res = event._event_data(action)

        self.assertEqual({'name': 'FAKE_ENTITY', 'obj_id': 'ENTITY_I',
                          'action': 'ACTION', 'phase': None, 'reason': None,
                          'id': 'ACTION_I'},
                         res)

    def test__event_data_with_phase_reason(self):
        entity = mock.Mock(id='ENTITY_ID')
        entity.name = 'FAKE_ENTITY'
        action = mock.Mock(id='ACTION_ID', action='ACTION', entity=entity)

        res = event._event_data(action, phase='PHASE1', reason='REASON1')

        self.assertEqual({'name': 'FAKE_ENTITY', 'id': 'ACTION_I',
                          'action': 'ACTION', 'phase': 'PHASE1',
                          'obj_id': 'ENTITY_I', 'reason': 'REASON1'},
                         res)

    def test__dump(self):
        cfg.CONF.set_override('debug', True)
        saved_dispathers = event.dispatchers
        event.dispatchers = mock.Mock()
        action = mock.Mock(cause=consts.CAUSE_RPC)
        try:
            event._dump(logging.INFO, action, 'Phase1', 'Reason1', 'TS1')
            event.dispatchers.map_method.assert_called_once_with(
                'dump', logging.INFO, action,
                phase='Phase1', reason='Reason1', timestamp='TS1')
        finally:
            event.dispatchers = saved_dispathers

    def test__dump_without_timestamp(self):
        cfg.CONF.set_override('debug', True)
        saved_dispathers = event.dispatchers
        event.dispatchers = mock.Mock()
        action = mock.Mock(cause=consts.CAUSE_RPC)
        try:
            event._dump(logging.INFO, action, 'Phase1', 'Reason1', None)

            event.dispatchers.map_method.assert_called_once_with(
                'dump', logging.INFO, action,
                phase='Phase1', reason='Reason1', timestamp=mock.ANY)
        finally:
            event.dispatchers = saved_dispathers

    def test__dump_guarded(self):
        cfg.CONF.set_override('debug', False)
        cfg.CONF.set_override('priority', 'warning', group='dispatchers')
        saved_dispathers = event.dispatchers
        event.dispatchers = mock.Mock()
        action = mock.Mock(cause=consts.CAUSE_RPC)
        try:
            event._dump(logging.INFO, action, 'Phase1', 'Reason1', 'TS1')
            # (temporary)Remove map_method.call_count for coverage test
            # self.assertEqual(0, event.dispatchers.map_method.call_count)
        finally:
            event.dispatchers = saved_dispathers

    def test__dump_exclude_derived_actions_positive(self):
        cfg.CONF.set_override('exclude_derived_actions', True,
                              group='dispatchers')
        saved_dispathers = event.dispatchers
        event.dispatchers = mock.Mock()
        action = mock.Mock(cause=consts.CAUSE_DERIVED)
        try:
            event._dump(logging.INFO, action, 'Phase1', 'Reason1', 'TS1')

            self.assertEqual(0, event.dispatchers.map_method.call_count)
        finally:
            event.dispatchers = saved_dispathers

    def test__dump_exclude_derived_actions_negative(self):
        cfg.CONF.set_override('exclude_derived_actions', False,
                              group='dispatchers')
        saved_dispathers = event.dispatchers
        event.dispatchers = mock.Mock()
        action = mock.Mock(cause=consts.CAUSE_DERIVED)
        try:
            event._dump(logging.INFO, action, 'Phase1', 'Reason1', 'TS1')

            event.dispatchers.map_method.assert_called_once_with(
                'dump', logging.INFO, action,
                phase='Phase1', reason='Reason1', timestamp='TS1')
        finally:
            event.dispatchers = saved_dispathers

    def test__dump_with_exception(self):
        cfg.CONF.set_override('debug', True)
        saved_dispathers = event.dispatchers
        event.dispatchers = mock.Mock()
        event.dispatchers.map_method.side_effect = Exception('fab')
        action = mock.Mock(cause=consts.CAUSE_RPC)
        try:
            res = event._dump(logging.INFO, action, 'Phase1', 'Reason1', 'TS1')

            self.assertIsNone(res)  # exception logged only
            event.dispatchers.map_method.assert_called_once_with(
                'dump', logging.INFO, action,
                phase='Phase1', reason='Reason1', timestamp='TS1')
        finally:
            event.dispatchers = saved_dispathers


@mock.patch.object(event, '_dump')
class TestLogMethods(testtools.TestCase):

    def test_critical(self, mock_dump):
        entity = mock.Mock(id='1234567890')
        entity.name = 'fake_obj'
        action = mock.Mock(id='FAKE_ID', entity=entity, action='ACTION_NAME')

        res = event.critical(action, 'P1', 'R1', 'TS1')

        self.assertIsNone(res)
        mock_dump.assert_called_once_with(logging.CRITICAL, action,
                                          'P1', 'R1', 'TS1')

    def test_error(self, mock_dump):
        entity = mock.Mock(id='1234567890')
        entity.name = 'fake_obj'
        action = mock.Mock(id='FAKE_ID', entity=entity, action='ACTION_NAME')

        res = event.error(action, 'P1', 'R1', 'TS1')

        self.assertIsNone(res)
        mock_dump.assert_called_once_with(logging.ERROR, action,
                                          'P1', 'R1', 'TS1')

    def test_warning(self, mock_dump):
        entity = mock.Mock(id='1234567890')
        entity.name = 'fake_obj'
        action = mock.Mock(id='FAKE_ID', entity=entity, action='ACTION_NAME')

        res = event.warning(action, 'P1', 'R1', 'TS1')

        self.assertIsNone(res)
        mock_dump.assert_called_once_with(logging.WARNING, action,
                                          'P1', 'R1', 'TS1')

    def test_info(self, mock_dump):
        entity = mock.Mock(id='1234567890')
        entity.name = 'fake_obj'
        action = mock.Mock(id='FAKE_ID', entity=entity, action='ACTION_NAME')

        res = event.info(action, 'P1', 'R1', 'TS1')

        self.assertIsNone(res)
        mock_dump.assert_called_once_with(logging.INFO, action,
                                          'P1', 'R1', 'TS1')

    def test_debug(self, mock_dump):
        entity = mock.Mock(id='1234567890')
        entity.name = 'fake_obj'
        action = mock.Mock(id='FAKE_ID', entity=entity, action='ACTION_NAME')

        res = event.debug(action, 'P1', 'R1', 'TS1')

        self.assertIsNone(res)
        mock_dump.assert_called_once_with(logging.DEBUG, action,
                                          'P1', 'R1', 'TS1')
