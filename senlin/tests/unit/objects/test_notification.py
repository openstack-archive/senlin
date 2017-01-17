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

import mock
from oslo_utils import timeutils
from oslo_utils import uuidutils
import testtools

from senlin.common import consts
from senlin.common import exception
from senlin.engine.actions import base as action_base
from senlin.engine import cluster
from senlin.engine import node
from senlin import objects
from senlin.objects import base as vo_base
from senlin.objects import fields
from senlin.objects import notification as base
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
        'extra_field': fields.StringField(),
        'field_1': fields.StringField(),
        'field_2': fields.IntegerField(),
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


class TestNotificationBase(testtools.TestCase):

    fake_service = {
        'created_at': timeutils.utcnow(True),
        'updated_at': timeutils.utcnow(True),
        'id': uuidutils.generate_uuid(),
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
        self.service_obj = objects.Service(**self.fake_service)

        self.my_obj = TestObject(field_1='test1', field_2=42,
                                 not_important_field=13)

        self.payload = TestPayload(field_1='test1', field_2=42,
                                   extra_field='test string')

        self.notification = TestNotification(
            event_type=base.EventType(
                object='test_object',
                action='update',
                phase=consts.PHASE_START),
            publisher=base.NotificationPublisher.from_service(
                self.service_obj),
            priority=consts.PRIO_INFO,
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
        self.assertEqual(expected_payload, actual_payload)

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
            action='update')
        publisher = base.NotificationPublisher(host='fake-host',
                                               binary='senlin-fake')

        noti = TestNotification(event_type=event_type,
                                publisher=publisher,
                                priority=consts.PRIO_INFO,
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
                action='update'),
            publisher=base.NotificationPublisher.from_service(
                self.service_obj),
            priority=consts.PRIO_INFO,
            payload=self.payload)

        mock_context = mock.Mock()
        mock_context.to_dict.return_value = {}
        noti.emit(mock_context)

        self._verify_notification(
            mock_notifier,
            mock_context,
            expected_event_type='test_object.update',
            expected_payload=self.expected_payload)


class TestExceptionPayload(testtools.TestCase):

    def test_create(self):
        ex = base.ExceptionPayload(
            module='fake_module',
            function='fake_function',
            exception='fake_exception',
            message='fake_message')

        self.assertEqual('fake_module', ex.module)
        self.assertEqual('fake_function', ex.function)
        self.assertEqual('fake_exception', ex.exception)
        self.assertEqual('fake_message', ex.message)

    def test_create_from_exception(self):
        ex = None
        pload = None

        try:
            {}['key']
        except Exception:
            ex = exception.BadRequest(msg="It is really bad.")
            pload = base.ExceptionPayload.from_exception(ex)

        self.assertIsNotNone(ex)
        self.assertIsNotNone(pload)

        # 'senlin.tests.unit.objects.notifications.test_exception',
        self.assertEqual(self.__module__, pload.module)
        self.assertEqual('test_create_from_exception', pload.function)
        self.assertEqual('BadRequest', pload.exception)
        self.assertEqual("It is really bad.", pload.message)

    def test_create_from_none(self):
        pload = base.ExceptionPayload.from_exception(None)
        self.assertIsNone(pload)


class TestClusterPayload(testtools.TestCase):

    def setUp(self):
        super(TestClusterPayload, self).setUp()

        uuid = uuidutils.generate_uuid()
        prof_uuid = uuidutils.generate_uuid()
        dt = timeutils.utcnow(True)
        self.params = {
            'id': uuid,
            'name': 'fake_name',
            'profile_id': prof_uuid,
            'init_at': dt,
            'created_at': dt,
            'updated_at': dt,
            'min_size': 1,
            'max_size': 10,
            'desired_capacity': 5,
            'timeout': 4,
            'status': 'ACTIVE',
            'status_reason': 'Good',
            'metadata': {'foo': 'bar'},
            'data': {'key': 'value'},
            'user': 'user1',
            'project': 'project1',
            'domain': 'domain1',
            'dependents': {'zoo': {'lion', 'deer'}}
        }

    def _verify_equality(self, obj, params):
        for k, v in params.items():
            self.assertTrue(obj.obj_attr_is_set(k))
            self.assertEqual(v, getattr(obj, k))

    def test_create(self):
        sot = base.ClusterPayload(**self.params)
        self._verify_equality(sot, self.params)

    def test_create_with_required_fields(self):
        params = {
            'id': uuidutils.generate_uuid(),
            'name': 'fake_name',
            'profile_id': uuidutils.generate_uuid(),
            'init_at': timeutils.utcnow(True),
            'min_size': 1,
            'max_size': 10,
            'desired_capacity': 5,
            'timeout': 4,
            'status': 'ACTIVE',
            'status_reason': 'Good',
            'user': 'user1',
            'project': 'project1',
        }

        sot = base.ClusterPayload(**params)

        self._verify_equality(sot, params)

    def test_create_with_obj(self):
        params = copy.deepcopy(self.params)
        name = params.pop('name')
        desired_capacity = params.pop('desired_capacity')
        profile_id = params.pop('profile_id')
        c1 = cluster.Cluster(name, desired_capacity, profile_id, **params)

        sot = base.ClusterPayload.from_cluster(c1)

        self._verify_equality(sot, self.params)


class TestNodePayload(testtools.TestCase):

    def setUp(self):
        super(TestNodePayload, self).setUp()

        uuid = uuidutils.generate_uuid()
        prof_uuid = uuidutils.generate_uuid()
        cluster_uuid = uuidutils.generate_uuid()
        physical_uuid = uuidutils.generate_uuid()
        dt = timeutils.utcnow(True)
        self.params = {
            'id': uuid,
            'name': 'fake_name',
            'profile_id': prof_uuid,
            'cluster_id': cluster_uuid,
            'physical_id': physical_uuid,
            'index': 3,
            'role': 'master',
            'init_at': dt,
            'created_at': dt,
            'updated_at': dt,
            'status': 'ACTIVE',
            'status_reason': 'Good',
            'metadata': {'foo': 'bar'},
            'data': {'key': 'value'},
            'user': 'user1',
            'project': 'project1',
            'domain': 'domain1',
            'dependents': {'zoo': {'lion', 'deer'}}
        }

    def _verify_equality(self, obj, params):
        for k, v in params.items():
            self.assertTrue(obj.obj_attr_is_set(k))
            self.assertEqual(v, getattr(obj, k))

    def test_create(self):
        sot = base.NodePayload(**self.params)
        self._verify_equality(sot, self.params)

    def test_create_with_required_fields(self):
        params = {
            'id': uuidutils.generate_uuid(),
            'name': 'fake_name',
            'profile_id': uuidutils.generate_uuid(),
            'cluster_id': '',
            'index': -1,
            'init_at': timeutils.utcnow(True),
            'status': 'ACTIVE',
            'status_reason': 'Good',
            'user': 'user1',
            'project': 'project1',
        }

        sot = base.NodePayload(**params)

        self._verify_equality(sot, params)

    def test_create_with_obj(self):
        params = copy.deepcopy(self.params)
        name = params.pop('name')
        profile_id = params.pop('profile_id')
        n1 = node.Node(name, profile_id, **params)

        sot = base.NodePayload.from_node(n1)

        self._verify_equality(sot, self.params)


class TestActionPayload(testtools.TestCase):

    def setUp(self):
        super(TestActionPayload, self).setUp()

        uuid = uuidutils.generate_uuid()
        target_uuid = uuidutils.generate_uuid()
        dt = timeutils.utcnow(True)
        self.params = {
            'id': uuid,
            'name': 'fake_name',
            'created_at': dt,
            'target': target_uuid,
            'action': 'CLUSTER_CREATE',
            'start_time': 1.23,
            'end_time': 4.56,
            'timeout': 78,
            'status': 'RUNNING',
            'status_reason': 'Clear',
            'inputs': {'key': 'value'},
            'outputs': {'foo': 'bar'},
            'data': {'zoo': 'nar'},
            'user': 'user1',
            'project': 'project1',
        }

    def _verify_equality(self, obj, params):
        for k, v in params.items():
            self.assertTrue(obj.obj_attr_is_set(k))
            self.assertEqual(v, getattr(obj, k))

    def test_create(self):
        sot = base.ActionPayload(**self.params)
        self._verify_equality(sot, self.params)

    def test_create_with_required_fields(self):
        params = {
            'id': uuidutils.generate_uuid(),
            'name': 'fake_name',
            'target': uuidutils.generate_uuid(),
            'action': 'CLUSTER_CREATE',
            'start_time': 1.23,
            'status': 'RUNNING',
            'status_reason': 'Good',
            'user': 'user1',
            'project': 'project1',
        }

        sot = base.ActionPayload(**params)

        self._verify_equality(sot, params)

    def test_create_with_obj(self):
        a1 = objects.Action(**self.params)

        sot = base.ActionPayload.from_action(a1)

        self._verify_equality(sot, self.params)


class TestClusterActionPayload(testtools.TestCase):

    def setUp(self):
        super(TestClusterActionPayload, self).setUp()
        ctx = utils.dummy_context()
        cluster_params = {
            'id': uuidutils.generate_uuid(),
            'init_at': timeutils.utcnow(True),
            'min_size': 1,
            'max_size': 10,
            'timeout': 4,
            'status': 'ACTIVE',
            'status_reason': 'Good',
            'user': 'user1',
            'project': 'project1',
        }
        self.cluster = cluster.Cluster('CC', 5, uuidutils.generate_uuid(),
                                       **cluster_params)
        action_params = {
            'id': uuidutils.generate_uuid(),
            'name': 'fake_name',
            'start_time': 1.23,
            'status': 'RUNNING',
            'status_reason': 'Good',
            'user': 'user1',
            'project': 'project1',
        }
        self.action = action_base.Action(uuidutils.generate_uuid(),
                                         'CLUSTER_CREATE', ctx,
                                         **action_params)

    def test_create(self):
        exobj = None
        try:
            {}['key']
        except Exception:
            ex = exception.InvalidSpec(message='boom')
            exobj = base.ExceptionPayload.from_exception(ex)

        sot = base.ClusterActionPayload(cluster=self.cluster,
                                        action=self.action,
                                        exception=exobj)

        self.assertTrue(sot.obj_attr_is_set('cluster'))
        self.assertTrue(sot.obj_attr_is_set('action'))
        self.assertTrue(sot.obj_attr_is_set('exception'))
        self.assertIsNotNone(sot.exception)

    def test_create_with_no_exc(self):
        ex = None
        sot = base.ClusterActionPayload(cluster=self.cluster,
                                        action=self.action,
                                        exception=ex)

        self.assertTrue(sot.obj_attr_is_set('cluster'))
        self.assertTrue(sot.obj_attr_is_set('action'))
        self.assertTrue(sot.obj_attr_is_set('exception'))
        self.assertIsNone(sot.exception)


class TestNodeActionPayload(testtools.TestCase):

    def setUp(self):
        super(TestNodeActionPayload, self).setUp()
        ctx = utils.dummy_context()
        node_params = {
            'id': uuidutils.generate_uuid(),
            'cluster_id': '',
            'index': -1,
            'init_at': timeutils.utcnow(True),
            'status': 'ACTIVE',
            'status_reason': 'Good',
        }
        self.node = node.Node('NN', uuidutils.generate_uuid(), **node_params)
        action_params = {

            'id': uuidutils.generate_uuid(),
            'name': 'fake_name',
            'start_time': 1.23,
            'status': 'RUNNING',
            'status_reason': 'Good',
            'user': 'user1',
            'project': 'project1',
        }
        self.action = action_base.Action(uuidutils.generate_uuid(),
                                         'NODE_CREATE', ctx, **action_params)

    def test_create(self):
        exobj = None
        try:
            {}['key']
        except Exception:
            ex = exception.InvalidSpec(message='boom')
            exobj = base.ExceptionPayload.from_exception(ex)

        sot = base.NodeActionPayload(node=self.node,
                                     action=self.action,
                                     exception=exobj)

        self.assertTrue(sot.obj_attr_is_set('node'))
        self.assertTrue(sot.obj_attr_is_set('action'))
        self.assertTrue(sot.obj_attr_is_set('exception'))
        self.assertIsNotNone(sot.exception)

    def test_create_with_no_exc(self):
        sot = base.NodeActionPayload(node=self.node, action=self.action)

        self.assertTrue(sot.obj_attr_is_set('node'))
        self.assertTrue(sot.obj_attr_is_set('action'))
        self.assertTrue(sot.obj_attr_is_set('exception'))
        self.assertIsNone(sot.exception)


class TestClusterActionNotification(testtools.TestCase):

    def setUp(self):
        super(TestClusterActionNotification, self).setUp()
        ctx = utils.dummy_context()
        cluster_params = {
            'id': uuidutils.generate_uuid(),
            'init_at': timeutils.utcnow(True),
            'min_size': 1,
            'max_size': 10,
            'timeout': 4,
            'status': 'ACTIVE',
            'status_reason': 'Good',
            'user': 'user1',
            'project': 'project1',
        }
        self.cluster = cluster.Cluster('CC', 5, uuidutils.generate_uuid(),
                                       **cluster_params)
        action_params = {
            'id': uuidutils.generate_uuid(),
            'name': 'fake_name',
            'start_time': 1.23,
            'status': 'RUNNING',
            'status_reason': 'Good',
            'user': 'user1',
            'project': 'project1',
        }
        self.action = action_base.Action(uuidutils.generate_uuid(),
                                         'CLUSTER_CREATE', ctx,
                                         **action_params)

    def test_create(self):
        payload = base.ClusterActionPayload(cluster=self.cluster,
                                            action=self.action)

        sot = base.ClusterActionNotification(payload=payload)

        self.assertTrue(sot.obj_attr_is_set('payload'))


class TestNodeActionNotification(testtools.TestCase):

    def setUp(self):
        super(TestNodeActionNotification, self).setUp()
        ctx = utils.dummy_context()
        node_params = {
            'id': uuidutils.generate_uuid(),
            'cluster_id': '',
            'index': -1,
            'init_at': timeutils.utcnow(True),
            'status': 'ACTIVE',
            'status_reason': 'Good',
            'user': 'user1',
            'project': 'project1',
        }
        self.node = node.Node('NN', uuidutils.generate_uuid(), **node_params)
        action_params = {

            'id': uuidutils.generate_uuid(),
            'name': 'fake_name',
            'start_time': 1.23,
            'status': 'RUNNING',
            'status_reason': 'Good',
            'user': 'user1',
            'project': 'project1',
        }
        self.action = action_base.Action(uuidutils.generate_uuid(),
                                         'NODE_CREATE', ctx, **action_params)

    def test_create(self):
        payload = base.NodeActionPayload(node=self.node, action=self.action)

        sot = base.NodeActionNotification(payload=payload)

        self.assertTrue(sot.obj_attr_is_set('payload'))
