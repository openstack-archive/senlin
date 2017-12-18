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
from oslo_messaging.rpc import dispatcher as rpc
import six

from senlin.common import consts
from senlin.common import exception as exc
from senlin.engine.receivers import base as rb
from senlin.engine import service
from senlin.objects import cluster as co
from senlin.objects import receiver as ro
from senlin.objects.requests import receivers as orro
from senlin.tests.unit.common import base
from senlin.tests.unit.common import utils


class ReceiverTest(base.SenlinTestCase):

    def setUp(self):
        super(ReceiverTest, self).setUp()
        self.ctx = utils.dummy_context(project='receiver_test_project')
        self.eng = service.EngineService('host-a', 'topic-a')

    @mock.patch.object(ro.Receiver, 'get_all')
    def test_receiver_list(self, mock_get):
        fake_obj = mock.Mock()
        fake_obj.to_dict.return_value = {'FOO': 'BAR'}
        mock_get.return_value = [fake_obj]

        req = orro.ReceiverListRequest()
        result = self.eng.receiver_list(self.ctx, req.obj_to_primitive())

        self.assertIsInstance(result, list)
        self.assertEqual([{'FOO': 'BAR'}], result)
        mock_get.assert_called_once_with(self.ctx, project_safe=True)

    @mock.patch.object(ro.Receiver, 'get_all')
    def test_receiver_list_with_params(self, mock_get):
        fake_obj = mock.Mock()
        fake_obj.to_dict.return_value = {'FOO': 'BAR'}
        mock_get.return_value = [fake_obj]

        marker = '7445519f-e9db-409f-82f4-187fb8334317'
        req = orro.ReceiverListRequest(limit=1, marker=marker, sort='name',
                                       type=['webhook'],
                                       action=['CLUSTER_RESIZE'],
                                       cluster_id=['123abc'],
                                       user=['user123'])
        result = self.eng.receiver_list(self.ctx, req.obj_to_primitive())

        self.assertIsInstance(result, list)
        self.assertEqual([{'FOO': 'BAR'}], result)
        mock_get.assert_called_once_with(self.ctx, limit=1, marker=marker,
                                         sort='name',
                                         filters={'type': ['webhook'],
                                                  'action': ['CLUSTER_RESIZE'],
                                                  'cluster_id': ['123abc'],
                                                  'user': ['user123']},
                                         project_safe=True)

    @mock.patch.object(ro.Receiver, 'get_all')
    def test_receiver_list_with_project_safe(self, mock_get):
        mock_get.return_value = []

        req = orro.ReceiverListRequest(project_safe=False)
        ex = self.assertRaises(rpc.ExpectedException,
                               self.eng.receiver_list,
                               self.ctx, req.obj_to_primitive())
        self.assertEqual(exc.Forbidden, ex.exc_info[0])

        self.ctx.is_admin = True

        result = self.eng.receiver_list(self.ctx, req.obj_to_primitive())
        self.assertEqual([], result)
        mock_get.assert_called_once_with(self.ctx, project_safe=False)
        mock_get.reset_mock()

        req = orro.ReceiverListRequest(project_safe=True)
        result = self.eng.receiver_list(self.ctx, req.obj_to_primitive())
        self.assertEqual([], result)
        mock_get.assert_called_once_with(self.ctx, project_safe=True)
        mock_get.reset_mock()

    @mock.patch.object(co.Cluster, 'find')
    @mock.patch.object(rb.Receiver, 'create')
    def test_receiver_create_webhook_succeed(self, mock_create, mock_find):
        fake_cluster = mock.Mock()
        fake_cluster.user = self.ctx.user_id
        mock_find.return_value = fake_cluster

        fake_receiver = mock.Mock(id='FAKE_RECEIVER')
        fake_receiver.to_dict.return_value = {
            'id': 'FAKE_RECEIVER',
            'foo': 'bar'
        }
        mock_create.return_value = fake_receiver
        req = orro.ReceiverCreateRequestBody(
            name='r1', type=consts.RECEIVER_WEBHOOK, cluster_id='C1',
            action=consts.CLUSTER_RESIZE)

        result = self.eng.receiver_create(self.ctx, req.obj_to_primitive())

        self.assertIsInstance(result, dict)
        self.assertEqual('FAKE_RECEIVER', result['id'])
        mock_find.assert_called_once_with(self.ctx, 'C1')
        mock_create.assert_called_once_with(
            self.ctx, 'webhook', fake_cluster, consts.CLUSTER_RESIZE,
            name='r1', user=self.ctx.user_id, project=self.ctx.project_id,
            domain=self.ctx.domain_id, params={})

        # test params passed
        mock_create.reset_mock()
        req = orro.ReceiverCreateRequestBody(
            name='r1', type=consts.RECEIVER_WEBHOOK, cluster_id='C1',
            action=consts.CLUSTER_RESIZE, params={'FOO': 'BAR'})

        self.eng.receiver_create(self.ctx, req.obj_to_primitive())
        mock_create.assert_called_once_with(
            self.ctx, 'webhook', fake_cluster, consts.CLUSTER_RESIZE,
            name='r1', user=self.ctx.user_id, project=self.ctx.project_id,
            domain=self.ctx.domain_id, params={'FOO': 'BAR'})

    @mock.patch.object(ro.Receiver, 'get_by_name')
    def test_receiver_create_name_duplicated(self, mock_get):
        cfg.CONF.set_override('name_unique', True)
        # Return an existing instance
        mock_get.return_value = mock.Mock()
        req = orro.ReceiverCreateRequestBody(
            name='r1', type=consts.RECEIVER_MESSAGE)

        ex = self.assertRaises(rpc.ExpectedException,
                               self.eng.receiver_create,
                               self.ctx, req.obj_to_primitive())

        self.assertEqual(exc.BadRequest, ex.exc_info[0])
        self.assertEqual("A receiver named 'r1' already exists.",
                         six.text_type(ex.exc_info[1]))

    @mock.patch.object(co.Cluster, 'find')
    def test_receiver_create_webhook_cluster_not_found(self, mock_find):
        mock_find.side_effect = exc.ResourceNotFound(type='cluster', id='C1')
        req = orro.ReceiverCreateRequestBody(
            name='r1', type=consts.RECEIVER_WEBHOOK, cluster_id='C1',
            action=consts.CLUSTER_RESIZE)

        ex = self.assertRaises(rpc.ExpectedException,
                               self.eng.receiver_create,
                               self.ctx, req.obj_to_primitive())

        self.assertEqual(exc.BadRequest, ex.exc_info[0])
        self.assertEqual("The referenced cluster 'C1' could not be found.",
                         six.text_type(ex.exc_info[1]))

    @mock.patch.object(co.Cluster, 'find')
    def test_receiver_create_webhook_invalid_action(self, mock_find):
        fake_cluster = mock.Mock()
        fake_cluster.user = 'someone'
        mock_find.return_value = fake_cluster
        req = orro.ReceiverCreateRequestBody(
            name='r1', type=consts.RECEIVER_WEBHOOK, cluster_id='C1',
            action=consts.CLUSTER_CREATE)

        ex = self.assertRaises(rpc.ExpectedException,
                               self.eng.receiver_create,
                               self.ctx, req.obj_to_primitive())

        self.assertEqual(exc.BadRequest, ex.exc_info[0])
        self.assertEqual("Action name cannot be any of ['CLUSTER_CREATE'].",
                         six.text_type(ex.exc_info[1]))

    @mock.patch.object(co.Cluster, 'find')
    @mock.patch.object(rb.Receiver, 'create')
    def test_receiver_create_webhook_forbidden(self, mock_create, mock_find):
        fake_cluster = mock.Mock()
        fake_cluster.user = 'someone'
        mock_find.return_value = fake_cluster
        req = orro.ReceiverCreateRequestBody(
            name='r1', type=consts.RECEIVER_WEBHOOK, cluster_id='C1',
            action=consts.CLUSTER_RESIZE)

        ex = self.assertRaises(rpc.ExpectedException,
                               self.eng.receiver_create,
                               self.ctx, req.obj_to_primitive())
        self.assertEqual(exc.Forbidden, ex.exc_info[0])

        fake_receiver = mock.Mock(id='FAKE_RECEIVER')
        fake_receiver.to_dict.return_value = {
            'id': 'FAKE_RECEIVER',
            'foo': 'bar'
        }
        mock_create.return_value = fake_receiver

        # an admin can do this
        self.ctx.is_admin = True
        result = self.eng.receiver_create(self.ctx, req.obj_to_primitive())
        self.assertIsInstance(result, dict)

    @mock.patch.object(co.Cluster, 'find')
    def test_receiver_create_webhook_cluster_not_specified(self, mock_find):
        fake_cluster = mock.Mock()
        fake_cluster.user = self.ctx.user_id
        mock_find.return_value = fake_cluster
        req1 = orro.ReceiverCreateRequestBody(name='r1', type='webhook',
                                              action='CLUSTER_RESIZE')
        req2 = orro.ReceiverCreateRequestBody(name='r1', type='webhook',
                                              cluster_id=None,
                                              action='CLUSTER_RESIZE')

        for req in [req1, req2]:
            ex = self.assertRaises(rpc.ExpectedException,
                                   self.eng.receiver_create,
                                   self.ctx, req.obj_to_primitive())
            self.assertEqual(exc.BadRequest, ex.exc_info[0])
            self.assertEqual("Cluster identity is required for creating "
                             "webhook receiver.",
                             six.text_type(ex.exc_info[1]))

    @mock.patch.object(co.Cluster, 'find')
    def test_receiver_create_webhook_action_not_specified(self, mock_find):
        fake_cluster = mock.Mock()
        fake_cluster.user = self.ctx.user_id
        mock_find.return_value = fake_cluster
        req1 = orro.ReceiverCreateRequestBody(name='r1', type='webhook',
                                              cluster_id='C1')
        req2 = orro.ReceiverCreateRequestBody(name='r1', type='webhook',
                                              cluster_id='C1', action=None)

        for req in [req1, req2]:
            ex = self.assertRaises(rpc.ExpectedException,
                                   self.eng.receiver_create,
                                   self.ctx, req.obj_to_primitive())
            self.assertEqual(exc.BadRequest, ex.exc_info[0])
            self.assertEqual("Action name is required for creating webhook "
                             "receiver.", six.text_type(ex.exc_info[1]))

    @mock.patch.object(rb.Receiver, 'create')
    def test_receiver_create_message_succeed(self, mock_create):
        fake_receiver = mock.Mock(id='FAKE_RECEIVER')
        fake_receiver.to_dict.return_value = {
            'id': 'FAKE_RECEIVER',
            'foo': 'bar'
        }
        mock_create.return_value = fake_receiver

        req = orro.ReceiverCreateRequestBody(name='r1', type='message')
        result = self.eng.receiver_create(self.ctx, req.obj_to_primitive())

        self.assertIsInstance(result, dict)
        self.assertEqual('FAKE_RECEIVER', result['id'])
        mock_create.assert_called_once_with(
            self.ctx, 'message', None, None, name='r1', user=self.ctx.user_id,
            project=self.ctx.project_id, domain=self.ctx.domain_id, params={})

    @mock.patch.object(ro.Receiver, 'find')
    def test_receiver_get(self, mock_find):
        fake_obj = mock.Mock()
        mock_find.return_value = fake_obj
        fake_obj.to_dict.return_value = {'FOO': 'BAR'}

        req = orro.ReceiverGetRequest(identity='FAKE_ID')
        res = self.eng.receiver_get(self.ctx, req.obj_to_primitive())

        self.assertEqual({'FOO': 'BAR'}, res)
        mock_find.assert_called_once_with(self.ctx, 'FAKE_ID')

    @mock.patch.object(ro.Receiver, 'find')
    def test_receiver_get_not_found(self, mock_find):
        mock_find.side_effect = exc.ResourceNotFound(type='receiver', id='RR')

        req = orro.ReceiverGetRequest(identity='Bogus')
        ex = self.assertRaises(rpc.ExpectedException,
                               self.eng.receiver_get, self.ctx,
                               req.obj_to_primitive())
        self.assertEqual(exc.ResourceNotFound, ex.exc_info[0])

    @mock.patch.object(rb.Receiver, 'load')
    @mock.patch.object(ro.Receiver, 'find')
    def test_receiver_update_request(self, mock_find, mock_load):
        x_obj = mock.Mock()
        mock_find.return_value = x_obj
        x_receiver = mock.Mock()
        x_receiver.name = 'OLD_NAME'
        x_receiver.params = {'count': '3'}
        x_receiver.to_dict.return_value = {'foo': 'bar'}
        mock_load.return_value = x_receiver

        params = {'name': 'NEW_NAME', 'params': {'count': '3'},
                  'identity': 'PID'}

        req = orro.ReceiverUpdateRequest(**params)

        result = self.eng.receiver_update(self.ctx, req.obj_to_primitive())
        self.assertEqual({'foo': 'bar'}, result)
        mock_find.assert_called_once_with(self.ctx, 'PID')
        mock_load.assert_called_once_with(self.ctx, receiver_obj=x_obj)
        self.assertEqual('NEW_NAME', x_receiver.name)
        self.assertEqual({'count': '3'}, x_receiver.params)
        x_receiver.store.assert_called_once_with(self.ctx, update=True)

    @mock.patch.object(ro.Receiver, 'find')
    def test_receiver_update_not_found(self, mock_find):

        mock_find.side_effect = exc.ResourceNotFound(type='receiver',
                                                     id='Bogus')

        kwargs = {'identity': 'Bogus', 'name': 'NEW_NAME'}
        req = orro.ReceiverUpdateRequest(**kwargs)
        ex = self.assertRaises(rpc.ExpectedException,
                               self.eng.receiver_update,
                               self.ctx, req.obj_to_primitive())

        self.assertEqual(exc.ResourceNotFound, ex.exc_info[0])
        self.assertEqual("The receiver 'Bogus' could not be found.",
                         six.text_type(ex.exc_info[1]))
        mock_find.assert_called_once_with(self.ctx, 'Bogus')

    @mock.patch.object(rb.Receiver, 'load')
    @mock.patch.object(ro.Receiver, 'find')
    def test_receiver_update_no_change(self, mock_find, mock_load):
        x_obj = mock.Mock()
        mock_find.return_value = x_obj
        x_receiver = mock.Mock()
        x_receiver.name = 'OLD_NAME'
        x_receiver.to_dict.return_value = {'foo': 'bar'}
        mock_load.return_value = x_receiver

        kwargs = {'name': 'OLD_NAME', 'identity': 'PID'}
        req = orro.ReceiverUpdateRequest(**kwargs)
        ex = self.assertRaises(rpc.ExpectedException,
                               self.eng.receiver_update,
                               self.ctx, req.obj_to_primitive())

        self.assertEqual(exc.BadRequest, ex.exc_info[0])
        self.assertEqual('No property needs an update.',
                         six.text_type(ex.exc_info[1]))
        mock_find.assert_called_once_with(self.ctx, 'PID')
        mock_load.assert_called_once_with(self.ctx, receiver_obj=x_obj)
        self.assertEqual(0, x_receiver.store.call_count)
        self.assertEqual('OLD_NAME', x_receiver.name)

    @mock.patch.object(ro.Receiver, 'find')
    @mock.patch.object(rb.Receiver, 'delete')
    def test_receiver_delete(self, mock_delete, mock_find):
        fake_obj = mock.Mock()
        fake_obj.id = 'FAKE_ID'
        mock_find.return_value = fake_obj
        req = orro.ReceiverDeleteRequest(identity='FAKE_RECEIVER')

        result = self.eng.receiver_delete(self.ctx, req.obj_to_primitive())

        self.assertIsNone(result)
        mock_find.assert_called_once_with(self.ctx, 'FAKE_RECEIVER')
        mock_delete.assert_called_once_with(self.ctx, 'FAKE_ID')

    @mock.patch.object(ro.Receiver, 'find')
    def test_receiver_delete_not_found(self, mock_find):
        mock_find.side_effect = exc.ResourceNotFound(type='receiver', id='RR')

        req = orro.ReceiverDeleteRequest(identity='Bogus')
        ex = self.assertRaises(rpc.ExpectedException,
                               self.eng.receiver_delete, self.ctx,
                               req.obj_to_primitive())
        self.assertEqual(exc.ResourceNotFound, ex.exc_info[0])

    @mock.patch.object(rb.Receiver, 'load')
    @mock.patch.object(ro.Receiver, 'find')
    def test_receiver_notify(self, mock_find, mock_load):
        fake_obj = mock.Mock()
        fake_obj.id = 'FAKE_ID'
        fake_obj.type = 'message'
        fake_obj.user = self.ctx.user_id
        fake_receiver = mock.Mock()
        mock_find.return_value = fake_obj
        mock_load.return_value = fake_receiver

        req = orro.ReceiverNotifyRequest(identity='FAKE_RECEIVER')
        result = self.eng.receiver_notify(self.ctx, req.obj_to_primitive())

        self.assertIsNone(result)
        mock_find.assert_called_once_with(self.ctx, 'FAKE_RECEIVER')
        mock_load.assert_called_once_with(self.ctx, receiver_obj=fake_obj,
                                          project_safe=True)
        fake_receiver.notify.assert_called_once_with(self.ctx)

    @mock.patch.object(ro.Receiver, 'find')
    def test_receiver_notify_not_found(self, mock_find):
        mock_find.side_effect = exc.ResourceNotFound(type='receiver', id='RR')

        req = orro.ReceiverNotifyRequest(identity='Bogus')
        ex = self.assertRaises(rpc.ExpectedException,
                               self.eng.receiver_notify, self.ctx,
                               req.obj_to_primitive())
        self.assertEqual(exc.ResourceNotFound, ex.exc_info[0])

    @mock.patch.object(ro.Receiver, 'find')
    def test_receiver_notify_permission_check_fail(self, mock_find):
        fake_obj = mock.Mock()
        fake_obj.id = 'FAKE_ID'
        fake_obj.user = 'foo'
        mock_find.return_value = fake_obj

        req = orro.ReceiverNotifyRequest(identity='FAKE_RECEIVER')
        ex = self.assertRaises(rpc.ExpectedException,
                               self.eng.receiver_notify, self.ctx,
                               req.obj_to_primitive())
        self.assertEqual(exc.Forbidden, ex.exc_info[0])

    @mock.patch.object(ro.Receiver, 'find')
    def test_receiver_notify_incorrect_type(self, mock_find):
        fake_obj = mock.Mock()
        fake_obj.id = 'FAKE_ID'
        fake_obj.user = self.ctx.user_id
        fake_obj.type = 'not_message'
        mock_find.return_value = fake_obj

        req = orro.ReceiverNotifyRequest(identity='FAKE_RECEIVER')
        ex = self.assertRaises(rpc.ExpectedException,
                               self.eng.receiver_notify, self.ctx,
                               req.obj_to_primitive())
        self.assertEqual(exc.BadRequest, ex.exc_info[0])
