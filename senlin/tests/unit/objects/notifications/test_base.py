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
from senlin.objects import base as vo_base
from senlin.objects import fields
from senlin.objects.notifications import base
from senlin.tests.unit.common import base as test_base
from senlin.tests.unit.common import utils


@vo_base.SenlinObjectRegistry.register_if(False)
class TestObject(vo_base.SenlinObject):
    VERSION = '1.0'
    fields = {
        'field_1': fields.StringField(),
        'field_2': fields.IntegerField(),
        'not_important_field': fields.IntegerField(),
    }


@vo_base.SenlinObjectRegistry.register_if(False)
class TestPayload(base.NotificationObject):
    VERSION = '1.0'

    fields = {
        'extra_field': fields.StringField(),  # filled by ctor
        'field_1': fields.StringField(),  # filled by the schema
        'field_2': fields.IntegerField(),   # filled by the schema
    }


@vo_base.SenlinObjectRegistry.register_if(False)
class TestNotification(base.NotificationBase):
    VERSION = '1.0'
    fields = {
        'payload': fields.ObjectField('TestPayload')
    }


@vo_base.SenlinObjectRegistry.register_if(False)
class TestNotificationEmptySchema(base.NotificationBase):
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
        'senlin_object.name': 'TestPayload',
        'senlin_object.data': {
            'field_1': 'test1',
            'field_2': 42,
            'extra_field': 'test string',
        },
        'senlin_object.version': '1.0',
        'senlin_object.namespace': 'senlin'
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

        self.payload = TestPayload(field_1='test1', field_2=42,
                                   extra_field='test string')

        self.notification = TestNotification(
            event_type=base.EventType(
                object='test_object',
                action=fields.NotificationAction.CLUSTER_UPDATE,
                phase=fields.NotificationPhase.START),
            publisher=base.NotificationPublisher.from_service(
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
        self.assertEqual(mock_notify.call_args[0][1],
                         expected_event_type)
        actual_payload = mock_notify.call_args[0][2]
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
        event_type = base.EventType(
            object='test_object',
            action=fields.NotificationAction.CLUSTER_UPDATE)
        publisher = base.NotificationPublisher(host='fake-host',
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
            event_type=base.EventType(
                object='test_object',
                action=fields.NotificationAction.CLUSTER_UPDATE),
            publisher=base.NotificationPublisher.from_service(
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
