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
from oslo_utils import timeutils
from oslo_utils import uuidutils

from senlin import objects
from senlin.objects import base
from senlin.objects import fields
from senlin.objects import notification
from senlin.tests.unit.common import base as test_base
from senlin.tests.unit.common import utils


@base.SenlinObjectRegistry.register_if(False)
class TestObject(base.SenlinObject):
    VERSION = '1.0'
    fields = {
        'field_1': fields.StringField(),
        'field_2': fields.IntegerField(),
        'not_important_field': fields.IntegerField(),
    }


@base.SenlinObjectRegistry.register_if(False)
class TestPayload(notification.NotificationPayloadBase):
    VERSION = '1.0'

    schema = {
        'field_1': ('source_field', 'field_1'),
        'field_2': ('source_field', 'field_2'),
    }

    fields = {
        'extra_field': fields.StringField(),  # filled by ctor
        'field_1': fields.StringField(),  # filled by the schema
        'field_2': fields.IntegerField(),   # filled by the schema
    }

    def populate_schema(self, source_field):
        super(TestPayload, self).populate_schema(source_field=source_field)


@base.SenlinObjectRegistry.register_if(False)
class TestPayloadEmptySchema(notification.NotificationPayloadBase):
    VERSION = '1.0'

    fields = {
        'extra_field': fields.StringField(),  # filled by ctor
    }


@base.SenlinObjectRegistry.register_if(False)
class TestNotification(notification.NotificationBase):
    VERSION = '1.0'
    fields = {
        'payload': fields.ObjectField('TestPayload')
    }


@base.SenlinObjectRegistry.register_if(False)
class TestNotificationEmptySchema(notification.NotificationBase):
    VERSION = '1.0'
    fields = {
        'payload': fields.ObjectField('TestPayloadEmptySchema')
    }


class TestNotificationBase(test_base.SenlinTestCase):

    fake_service = {
        'created_at': timeutils.utcnow().replace(microsecond=0),
        'updated_at': None,
        'id': 123,
        'host': 'fake-host',
        'binary': 'senlin-fake',
        'topic': 'fake-service-topic',
        'disabled': False,
        'disabled_reason': None,
    }

    expected_payload = {
        'versioned_object.name': 'TestPayload',
        'versioned_object.data': {
            'extra_field': 'test string',
            'field_1': 'test1',
            'field_2': 42
        },
        'versioned_object.version': '1.0',
        'versioned_object.namespace': 'senlin'
    }

    def setUp(self):
        super(TestNotificationBase, self).setUp()
        self.ctx = utils.dummy_context()
        service_id = uuidutils.generate_uuid()
        self.service_obj = objects.Service.create(
            self.ctx, service_id,
            self.fake_service['host'],
            self.fake_service['binary'],
            self.fake_service['topic'])

        self.my_obj = TestObject(field_1='test1', field_2=42,
                                 not_important_field=13)

        self.payload = TestPayload(extra_field='test string')
        self.payload.populate_schema(source_field=self.my_obj)

        self.notification = TestNotification(
            event_type=notification.EventType(
                object='test_object',
                action=fields.NotificationAction.UPDATE,
                phase=fields.NotificationPhase.START),
            publisher=notification.NotificationPublisher.from_service_obj(
                self.service_obj),
            priority=fields.NotificationPriority.INFO,
            payload=self.payload)

    def _verify_notification(self, mock_notifier, mock_context,
                             expected_event_type, expected_payload):
        mock_notifier.prepare.assert_called_once_with(
            publisher_id='senlin-fake:fake-host')
        mock_notify = mock_notifier.prepare.return_value.info
        self.assertTrue(mock_notify.called)
        self.assertEqual(mock_notify.call_args[0][0], mock_context)
        self.assertEqual(mock_notify.call_args[1]['event_type'],
                         expected_event_type)
        actual_payload = mock_notify.call_args[1]['payload']
        self.assertJsonEqual(expected_payload, actual_payload)

    @mock.patch('senlin.common.messaging.NOTIFIER')
    def test_emit_notification(self, mock_notifier):

        mock_context = mock.Mock()
        mock_context.to_dict.return_value = {}
        self.notification.emit(mock_context)

        self._verify_notification(
            mock_notifier,
            mock_context,
            expected_event_type='test_object.update.start',
            expected_payload=self.expected_payload)

    @mock.patch('senlin.common.messaging.NOTIFIER')
    def test_emit_with_host_and_binary_as_publisher(self, mock_notifier):
        event_type = notification.EventType(
            object='test_object',
            action=fields.NotificationAction.UPDATE)
        publisher = notification.NotificationPublisher(host='fake-host',
                                                       binary='senlin-fake')

        noti = TestNotification(event_type=event_type,
                                publisher=publisher,
                                priority=fields.NotificationPriority.INFO,
                                payload=self.payload)

        mock_context = mock.Mock()
        mock_context.to_dict.return_value = {}
        noti.emit(mock_context)

        self._verify_notification(
            mock_notifier,
            mock_context,
            expected_event_type='test_object.update',
            expected_payload=self.expected_payload)

    @mock.patch('senlin.common.messaging.NOTIFIER')
    def test_emit_event_type_without_phase(self, mock_notifier):
        noti = TestNotification(
            event_type=notification.EventType(
                object='test_object',
                action=fields.NotificationAction.UPDATE),
            publisher=notification.NotificationPublisher.from_service_obj(
                self.service_obj),
            priority=fields.NotificationPriority.INFO,
            payload=self.payload)

        mock_context = mock.Mock()
        mock_context.to_dict.return_value = {}
        noti.emit(mock_context)

        self._verify_notification(
            mock_notifier,
            mock_context,
            expected_event_type='test_object.update',
            expected_payload=self.expected_payload)

    @mock.patch('senlin.common.messaging.NOTIFIER')
    def test_not_possible_to_emit_if_not_populated(self, mock_notifier):
        # create a non-populated payload
        payload = TestPayload(extra_field='test string')
        event_type = notification.EventType(
            object='test_object',
            action=fields.NotificationAction.UPDATE)
        publisher = notification.NotificationPublisher.from_service_obj(
            self.service_obj)

        noti = TestNotification(
            event_type=event_type,
            publisher=publisher,
            priority=fields.NotificationPriority.INFO,
            payload=payload)

        mock_context = mock.Mock()
        self.assertRaises(AssertionError, noti.emit, mock_context)
        self.assertFalse(mock_notifier.called)

    @mock.patch('senlin.common.messaging.NOTIFIER')
    def test_empty_schema(self, mock_notifier):
        # create a non-populated payload
        payload = TestPayloadEmptySchema(extra_field='test string')
        event_type = notification.EventType(
            object='test_object',
            action=fields.NotificationAction.UPDATE)
        publisher = notification.NotificationPublisher.from_service_obj(
            self.service_obj)

        noti = TestNotificationEmptySchema(
            event_type=event_type,
            publisher=publisher,
            priority=fields.NotificationPriority.INFO,
            payload=payload)

        mock_context = mock.Mock()
        mock_context.to_dict.return_value = {}
        noti.emit(mock_context)

        self._verify_notification(
            mock_notifier,
            mock_context,
            expected_event_type='test_object.update',
            expected_payload={
                'versioned_object.name': 'TestPayloadEmptySchema',
                'versioned_object.data': {'extra_field': u'test string'},
                'versioned_object.version': '1.0',
                'versioned_object.namespace': 'senlin'
            }
        )
