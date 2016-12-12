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
from oslo_utils import uuidutils
import six

from senlin.common import exception as exc
from senlin.engine.receivers import base as rb
from senlin.engine import service
from senlin.objects import receiver as ro
from senlin.objects.requests import receivers as orro
from senlin.tests.unit.common import base
from senlin.tests.unit.common import utils


class ReceiverTest(base.SenlinTestCase):

    def setUp(self):
        super(ReceiverTest, self).setUp()
        self.ctx = utils.dummy_context(project='receiver_test_project')
        self.eng = service.EngineService('host-a', 'topic-a')

    @mock.patch.object(ro.Receiver, 'get')
    def test_receiver_find_by_uuid(self, mock_get):
        fake_obj = mock.Mock()
        mock_get.return_value = fake_obj
        fake_id = uuidutils.generate_uuid()

        res = self.eng.receiver_find(self.ctx, fake_id)

        self.assertEqual(fake_obj, res)
        mock_get.assert_called_once_with(self.ctx, fake_id, project_safe=True)

    @mock.patch.object(ro.Receiver, 'get_by_name')
    @mock.patch.object(ro.Receiver, 'get')
    def test_receiver_find_by_uuid_as_name(self, mock_get, mock_get_name):
        mock_get.return_value = None
        fake_obj = mock.Mock()
        mock_get_name.return_value = fake_obj
        fake_id = uuidutils.generate_uuid()

        res = self.eng.receiver_find(self.ctx, fake_id, project_safe=False)

        self.assertEqual(fake_obj, res)
        mock_get.assert_called_once_with(self.ctx, fake_id, project_safe=False)
        mock_get_name.assert_called_once_with(self.ctx, fake_id,
                                              project_safe=False)

    @mock.patch.object(ro.Receiver, 'get_by_name')
    def test_receiver_find_by_name(self, mock_get_name):
        fake_obj = mock.Mock()
        mock_get_name.return_value = fake_obj
        fake_id = 'not-a-uuid'

        res = self.eng.receiver_find(self.ctx, fake_id)

        self.assertEqual(fake_obj, res)
        mock_get_name.assert_called_once_with(self.ctx, fake_id,
                                              project_safe=True)

    @mock.patch.object(ro.Receiver, 'get_by_short_id')
    @mock.patch.object(ro.Receiver, 'get_by_name')
    def test_receiver_find_by_short_id(self, mock_get_name, mock_get_shortid):
        mock_get_name.return_value = None
        fake_obj = mock.Mock()
        mock_get_shortid.return_value = fake_obj
        fake_id = '12345678'

        res = self.eng.receiver_find(self.ctx, fake_id, False)

        self.assertEqual(fake_obj, res)
        mock_get_name.assert_called_once_with(self.ctx, fake_id,
                                              project_safe=False)
        mock_get_shortid.assert_called_once_with(self.ctx, fake_id,
                                                 project_safe=False)

    @mock.patch.object(ro.Receiver, 'get_by_name')
    def test_receiver_find_not_found(self, mock_get_name):
        mock_get_name.return_value = None
        fake_id = '12345678'  # not a uuid

        self.assertRaises(exc.ResourceNotFound,
                          self.eng.receiver_find,
                          self.ctx, fake_id, True)

        mock_get_name.assert_called_once_with(self.ctx, fake_id,
                                              project_safe=True)

    @mock.patch.object(rb.Receiver, 'load_all')
    def test_receiver_list2(self, mock_load):
        fake_obj = mock.Mock()
        fake_obj.to_dict.return_value = {'FOO': 'BAR'}
        # NOTE: actual return value is a generator
        mock_load.return_value = [fake_obj]

        req = orro.ReceiverListRequest()
        result = self.eng.receiver_list2(self.ctx, req.obj_to_primitive())

        self.assertIsInstance(result, list)
        self.assertEqual([{'FOO': 'BAR'}], result)
        mock_load.assert_called_once_with(self.ctx, project_safe=True)

    @mock.patch.object(rb.Receiver, 'load_all')
    def test_receiver_list2_with_params(self, mock_load):
        fake_obj = mock.Mock()
        fake_obj.to_dict.return_value = {'FOO': 'BAR'}
        mock_load.return_value = [fake_obj]

        marker = '7445519f-e9db-409f-82f4-187fb8334317'
        req = orro.ReceiverListRequest(limit=1, marker=marker, sort='name',
                                       type=['webhook'],
                                       action=['CLUSTER_RESIZE'],
                                       cluster_id=['123abc'])
        result = self.eng.receiver_list2(self.ctx, req.obj_to_primitive())

        self.assertIsInstance(result, list)
        self.assertEqual([{'FOO': 'BAR'}], result)
        mock_load.assert_called_once_with(self.ctx, limit=1, marker=marker,
                                          sort='name',
                                          filters={
                                              'type': ['webhook'],
                                              'action': ['CLUSTER_RESIZE'],
                                              'cluster_id': ['123abc']},
                                          project_safe=True)

    @mock.patch.object(rb.Receiver, 'load_all')
    def test_receiver_list2_with_project_safe(self, mock_load):
        mock_load.return_value = []

        req = orro.ReceiverListRequest(project_safe=False)
        ex = self.assertRaises(rpc.ExpectedException,
                               self.eng.receiver_list2,
                               self.ctx, req.obj_to_primitive())
        self.assertEqual(exc.Forbidden, ex.exc_info[0])

        self.ctx.is_admin = True

        result = self.eng.receiver_list2(self.ctx, req.obj_to_primitive())
        self.assertEqual([], result)
        mock_load.assert_called_once_with(self.ctx, project_safe=False)
        mock_load.reset_mock()

        req = orro.ReceiverListRequest(project_safe=True)
        result = self.eng.receiver_list2(self.ctx, req.obj_to_primitive())
        self.assertEqual([], result)
        mock_load.assert_called_once_with(self.ctx, project_safe=True)
        mock_load.reset_mock()

    @mock.patch.object(service.EngineService, 'cluster_find')
    @mock.patch.object(rb.Receiver, 'create')
    def test_receiver_create2_webhook_succeed(self, mock_create, mock_find):
        fake_cluster = mock.Mock()
        fake_cluster.user = self.ctx.user
        mock_find.return_value = fake_cluster

        fake_receiver = mock.Mock(id='FAKE_RECIEVER')
        fake_receiver.to_dict.return_value = {
            'id': 'FAKE_RECEIVER',
            'foo': 'bar'
        }
        mock_create.return_value = fake_receiver

        req = orro.ReceiverCreateRequestBody(name='r1', type='webhook',
                                             cluster_id='C1',
                                             action='CLUSTER_RESIZE')
        result = self.eng.receiver_create2(self.ctx, req.obj_to_primitive())

        self.assertIsInstance(result, dict)
        self.assertEqual('FAKE_RECEIVER', result['id'])
        mock_find.assert_called_once_with(self.ctx, 'C1')
        mock_create.assert_called_once_with(
            self.ctx, 'webhook', fake_cluster, 'CLUSTER_RESIZE',
            name='r1', user=self.ctx.user, project=self.ctx.project,
            domain=self.ctx.domain, params={})

        # test params passed
        mock_create.reset_mock()
        req = orro.ReceiverCreateRequestBody(name='r1', type='webhook',
                                             cluster_id='C1',
                                             action='CLUSTER_RESIZE',
                                             params={'FOO': 'BAR'})
        self.eng.receiver_create2(self.ctx, req.obj_to_primitive())
        mock_create.assert_called_once_with(
            self.ctx, 'webhook', fake_cluster, 'CLUSTER_RESIZE',
            name='r1', user=self.ctx.user, project=self.ctx.project,
            domain=self.ctx.domain, params={'FOO': 'BAR'})

    @mock.patch.object(ro.Receiver, 'get_by_name')
    def test_receiver_create2_name_duplicated(self, mock_get):
        cfg.CONF.set_override('name_unique', True, enforce_type=True)
        # Return an existing instance
        mock_get.return_value = mock.Mock()

        req = orro.ReceiverCreateRequestBody(name='r1', type='message')
        ex = self.assertRaises(rpc.ExpectedException,
                               self.eng.receiver_create2,
                               self.ctx, req.obj_to_primitive())
        self.assertEqual(exc.BadRequest, ex.exc_info[0])
        self.assertEqual("The request is malformed: A receiver named 'r1' "
                         "already exists.",
                         six.text_type(ex.exc_info[1]))

    @mock.patch.object(service.EngineService, 'cluster_find')
    def test_receiver_create2_webhook_cluster_not_found(self, mock_find):
        mock_find.side_effect = exc.ResourceNotFound(type='cluster', id='C1')
        req = orro.ReceiverCreateRequestBody(name='r1', type='webhook',
                                             cluster_id='C1',
                                             action='CLUSTER_RESIZE')

        ex = self.assertRaises(rpc.ExpectedException,
                               self.eng.receiver_create2,
                               self.ctx, req.obj_to_primitive())
        self.assertEqual(exc.BadRequest, ex.exc_info[0])
        self.assertEqual("The request is malformed: The referenced cluster "
                         "(C1) could not be found.",
                         six.text_type(ex.exc_info[1]))

    @mock.patch.object(service.EngineService, 'cluster_find')
    @mock.patch.object(rb.Receiver, 'create')
    def test_receiver_create2_webhook_forbidden(self, mock_create, mock_find):
        fake_cluster = mock.Mock()
        fake_cluster.user = 'someone'
        mock_find.return_value = fake_cluster
        req = orro.ReceiverCreateRequestBody(name='r1', type='webhook',
                                             cluster_id='C1',
                                             action='CLUSTER_RESIZE')

        ex = self.assertRaises(rpc.ExpectedException,
                               self.eng.receiver_create2,
                               self.ctx, req.obj_to_primitive())
        self.assertEqual(exc.Forbidden, ex.exc_info[0])

        fake_receiver = mock.Mock(id='FAKE_RECIEVER')
        fake_receiver.to_dict.return_value = {
            'id': 'FAKE_RECEIVER',
            'foo': 'bar'
        }
        mock_create.return_value = fake_receiver

        # an admin can do this
        self.ctx.is_admin = True
        result = self.eng.receiver_create2(self.ctx, req.obj_to_primitive())
        self.assertIsInstance(result, dict)

    @mock.patch.object(service.EngineService, 'cluster_find')
    def test_receiver_create2_webhook_cluster_not_specified(self, mock_find):
        fake_cluster = mock.Mock()
        fake_cluster.user = self.ctx.user
        mock_find.return_value = fake_cluster
        req1 = orro.ReceiverCreateRequestBody(name='r1', type='webhook',
                                              action='CLUSTER_RESIZE')
        req2 = orro.ReceiverCreateRequestBody(name='r1', type='webhook',
                                              cluster_id=None,
                                              action='CLUSTER_RESIZE')

        for req in [req1, req2]:
            ex = self.assertRaises(rpc.ExpectedException,
                                   self.eng.receiver_create2,
                                   self.ctx, req.obj_to_primitive())
            self.assertEqual(exc.BadRequest, ex.exc_info[0])
            self.assertEqual("The request is malformed: Cluster identity is "
                             "required for creating webhook receiver.",
                             six.text_type(ex.exc_info[1]))

    @mock.patch.object(service.EngineService, 'cluster_find')
    def test_receiver_create2_webhook_action_not_specified(self, mock_find):
        fake_cluster = mock.Mock()
        fake_cluster.user = self.ctx.user
        mock_find.return_value = fake_cluster
        req1 = orro.ReceiverCreateRequestBody(name='r1', type='webhook',
                                              cluster_id='C1')
        req2 = orro.ReceiverCreateRequestBody(name='r1', type='webhook',
                                              cluster_id='C1', action=None)

        for req in [req1, req2]:
            ex = self.assertRaises(rpc.ExpectedException,
                                   self.eng.receiver_create2,
                                   self.ctx, req.obj_to_primitive())
            self.assertEqual(exc.BadRequest, ex.exc_info[0])
            self.assertEqual("The request is malformed: Action name is "
                             "required for creating webhook receiver.",
                             six.text_type(ex.exc_info[1]))

    @mock.patch.object(rb.Receiver, 'create')
    def test_receiver_create2_message_succeed(self, mock_create):
        fake_receiver = mock.Mock(id='FAKE_RECIEVER')
        fake_receiver.to_dict.return_value = {
            'id': 'FAKE_RECEIVER',
            'foo': 'bar'
        }
        mock_create.return_value = fake_receiver

        req = orro.ReceiverCreateRequestBody(name='r1', type='message')
        result = self.eng.receiver_create2(self.ctx, req.obj_to_primitive())

        self.assertIsInstance(result, dict)
        self.assertEqual('FAKE_RECEIVER', result['id'])
        mock_create.assert_called_once_with(
            self.ctx, 'message', None, None, name='r1', user=self.ctx.user,
            project=self.ctx.project, domain=self.ctx.domain, params={})

    @mock.patch.object(rb.Receiver, 'load')
    def test_receiver_get2(self, mock_load):
        fake_obj = mock.Mock()
        mock_find = self.patchobject(self.eng, 'receiver_find',
                                     return_value=fake_obj)
        fake_receiver = mock.Mock()
        fake_receiver.to_dict.return_value = {'FOO': 'BAR'}
        mock_load.return_value = fake_receiver

        req = orro.ReceiverGetRequest(identity='FAKE_ID')
        res = self.eng.receiver_get2(self.ctx, req.obj_to_primitive())

        self.assertEqual({'FOO': 'BAR'}, res)
        mock_find.assert_called_once_with(self.ctx, 'FAKE_ID')
        mock_load.assert_called_once_with(self.ctx,
                                          receiver_obj=fake_obj)

    @mock.patch.object(service.EngineService, 'receiver_find')
    def test_receiver_get2_not_found(self, mock_find):

        mock_find.side_effect = exc.ResourceNotFound(type='receiver', id='RR')

        req = orro.ReceiverGetRequest(identity='Bogus')
        ex = self.assertRaises(rpc.ExpectedException,
                               self.eng.receiver_get2, self.ctx,
                               req.obj_to_primitive())
        self.assertEqual(exc.ResourceNotFound, ex.exc_info[0])

    @mock.patch.object(service.EngineService, 'receiver_find')
    @mock.patch.object(rb.Receiver, 'delete')
    def test_receiver_delete2(self, mock_delete, mock_find):
        fake_obj = mock.Mock()
        fake_obj.id = 'FAKE_ID'
        mock_find.return_value = fake_obj
        req = orro.ReceiverDeleteRequest(identity='FAKE_RECEIVER')

        result = self.eng.receiver_delete2(self.ctx, req.obj_to_primitive())

        self.assertIsNone(result)
        mock_find.assert_called_once_with(self.ctx, 'FAKE_RECEIVER')
        mock_delete.assert_called_once_with(self.ctx, 'FAKE_ID')

    @mock.patch.object(service.EngineService, 'receiver_find')
    def test_receiver_delete2_not_found(self, mock_find):
        mock_find.side_effect = exc.ResourceNotFound(type='receiver', id='RR')

        req = orro.ReceiverDeleteRequest(identity='Bogus')
        ex = self.assertRaises(rpc.ExpectedException,
                               self.eng.receiver_delete2, self.ctx,
                               req.obj_to_primitive())
        self.assertEqual(exc.ResourceNotFound, ex.exc_info[0])

    @mock.patch.object(rb.Receiver, 'load')
    @mock.patch.object(service.EngineService, 'receiver_find')
    def test_receiver_notify2(self, mock_find, mock_load):
        fake_obj = mock.Mock()
        fake_obj.id = 'FAKE_ID'
        fake_obj.type = 'message'
        fake_obj.user = self.ctx.user
        fake_receiver = mock.Mock()
        mock_find.return_value = fake_obj
        mock_load.return_value = fake_receiver

        req = orro.ReceiverNotifyRequest(identity='FAKE_RECEIVER')
        result = self.eng.receiver_notify2(self.ctx, req.obj_to_primitive())

        self.assertIsNone(result)
        mock_find.assert_called_once_with(self.ctx, 'FAKE_RECEIVER')
        mock_load.assert_called_once_with(self.ctx, receiver_obj=fake_obj,
                                          project_safe=True)
        fake_receiver.notify.assert_called_once_with(self.ctx)

    @mock.patch.object(service.EngineService, 'receiver_find')
    def test_receiver_notify2_not_found(self, mock_find):
        mock_find.side_effect = exc.ResourceNotFound(type='receiver', id='RR')

        req = orro.ReceiverNotifyRequest(identity='Bogus')
        ex = self.assertRaises(rpc.ExpectedException,
                               self.eng.receiver_notify2, self.ctx,
                               req.obj_to_primitive())
        self.assertEqual(exc.ResourceNotFound, ex.exc_info[0])

    @mock.patch.object(service.EngineService, 'receiver_find')
    def test_receiver_notify2_permission_check_fail(self, mock_find):
        fake_obj = mock.Mock()
        fake_obj.id = 'FAKE_ID'
        fake_obj.user = 'foo'
        mock_find.return_value = fake_obj

        req = orro.ReceiverNotifyRequest(identity='FAKE_RECEIVER')
        ex = self.assertRaises(rpc.ExpectedException,
                               self.eng.receiver_notify2, self.ctx,
                               req.obj_to_primitive())
        self.assertEqual(exc.Forbidden, ex.exc_info[0])

    @mock.patch.object(service.EngineService, 'receiver_find')
    def test_receiver_notify2_incorrect_type(self, mock_find):
        fake_obj = mock.Mock()
        fake_obj.id = 'FAKE_ID'
        fake_obj.user = self.ctx.user
        fake_obj.type = 'not_message'
        mock_find.return_value = fake_obj

        req = orro.ReceiverNotifyRequest(identity='FAKE_RECEIVER')
        ex = self.assertRaises(rpc.ExpectedException,
                               self.eng.receiver_notify2, self.ctx,
                               req.obj_to_primitive())
        self.assertEqual(exc.BadRequest, ex.exc_info[0])
