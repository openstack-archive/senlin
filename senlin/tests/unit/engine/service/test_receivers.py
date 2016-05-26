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
from senlin.engine import receiver as rb
from senlin.engine import service
from senlin.objects import receiver as ro
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

        self.assertRaises(exc.ReceiverNotFound,
                          self.eng.receiver_find,
                          self.ctx, fake_id, True)

        mock_get_name.assert_called_once_with(self.ctx, fake_id,
                                              project_safe=True)

    @mock.patch.object(rb.Receiver, 'load_all')
    def test_receiver_list(self, mock_load):
        fake_obj = mock.Mock()
        fake_obj.to_dict.return_value = {'FOO': 'BAR'}
        # NOTE: actual return value is a generator
        mock_load.return_value = [fake_obj]

        result = self.eng.receiver_list(self.ctx)

        self.assertIsInstance(result, list)
        self.assertEqual([{'FOO': 'BAR'}], result)
        mock_load.assert_called_once_with(self.ctx, limit=None, marker=None,
                                          sort=None, filters=None,
                                          project_safe=True)

    @mock.patch.object(rb.Receiver, 'load_all')
    def test_receiver_list_with_params(self, mock_load):
        fake_obj = mock.Mock()
        fake_obj.to_dict.return_value = {'FOO': 'BAR'}
        mock_load.return_value = [fake_obj]

        result = self.eng.receiver_list(self.ctx, limit=1, marker='MARKER',
                                        sort='name',
                                        filters={'key1': 'value1'},
                                        project_safe=True)

        self.assertIsInstance(result, list)
        self.assertEqual([{'FOO': 'BAR'}], result)
        mock_load.assert_called_once_with(self.ctx, limit=1, marker='MARKER',
                                          sort='name',
                                          filters={'key1': 'value1'},
                                          project_safe=True)

    def test_receiver_list_bad_params(self):
        ex = self.assertRaises(rpc.ExpectedException,
                               self.eng.receiver_list, self.ctx, limit='no')
        self.assertEqual(exc.InvalidParameter, ex.exc_info[0])

        ex = self.assertRaises(rpc.ExpectedException,
                               self.eng.receiver_list,
                               self.ctx, sort='crazykey')
        self.assertEqual(exc.InvalidParameter, ex.exc_info[0])

        ex = self.assertRaises(rpc.ExpectedException,
                               self.eng.receiver_list,
                               self.ctx, project_safe='yes')
        self.assertEqual(exc.InvalidParameter, ex.exc_info[0])

    @mock.patch.object(rb.Receiver, 'load_all')
    def test_receiver_list_with_project_safe(self, mock_load):
        mock_load.return_value = []

        result = self.eng.receiver_list(self.ctx)
        self.assertEqual([], result)
        mock_load.assert_called_once_with(self.ctx, filters=None, limit=None,
                                          sort=None, marker=None,
                                          project_safe=True)
        mock_load.reset_mock()

        ex = self.assertRaises(rpc.ExpectedException,
                               self.eng.receiver_list,
                               self.ctx, project_safe=False)
        self.assertEqual(exc.Forbidden, ex.exc_info[0])

        self.ctx.is_admin = True

        result = self.eng.receiver_list(self.ctx)
        self.assertEqual([], result)
        mock_load.assert_called_once_with(self.ctx, filters=None, limit=None,
                                          sort=None, marker=None,
                                          project_safe=True)
        mock_load.reset_mock()

        result = self.eng.receiver_list(self.ctx, project_safe=True)
        self.assertEqual([], result)
        mock_load.assert_called_once_with(self.ctx, filters=None, limit=None,
                                          sort=None, marker=None,
                                          project_safe=True)
        mock_load.reset_mock()

        result = self.eng.receiver_list(self.ctx, project_safe=False)
        self.assertEqual([], result)
        mock_load.assert_called_once_with(self.ctx, filters=None, limit=None,
                                          sort=None, marker=None,
                                          project_safe=False)

    @mock.patch.object(service.EngineService, 'cluster_find')
    @mock.patch.object(rb.Receiver, 'create')
    def test_receiver_create(self, mock_create, mock_find):
        fake_cluster = mock.Mock()
        fake_cluster.user = self.ctx.user
        mock_find.return_value = fake_cluster

        fake_receiver = mock.Mock(id='FAKE_RECIEVER')
        fake_receiver.to_dict.return_value = {
            'id': 'FAKE_RECEIVER',
            'foo': 'bar'
        }
        mock_create.return_value = fake_receiver

        result = self.eng.receiver_create(self.ctx, 'r1', 'webhook', 'C1',
                                          'CLUSTER_RESIZE')

        self.assertIsInstance(result, dict)
        self.assertEqual('FAKE_RECEIVER', result['id'])
        mock_find.assert_called_once_with(self.ctx, 'C1')
        mock_create.assert_called_once_with(
            self.ctx, 'webhook', fake_cluster, 'CLUSTER_RESIZE',
            name='r1', user=self.ctx.user, project=self.ctx.project,
            domain=self.ctx.domain, params={})

        # test params passed
        mock_create.reset_mock()
        self.eng.receiver_create(self.ctx, 'r1', 'webhook', 'C1',
                                 'CLUSTER_RESIZE', params={'FOO': 'BAR'})
        mock_create.assert_called_once_with(
            self.ctx, 'webhook', fake_cluster, 'CLUSTER_RESIZE',
            name='r1', user=self.ctx.user, project=self.ctx.project,
            domain=self.ctx.domain, params={'FOO': 'BAR'})

    @mock.patch.object(ro.Receiver, 'get_by_name')
    def test_receiver_create_name_duplicated(self, mock_get):
        cfg.CONF.set_override('name_unique', True, enforce_type=True)
        # Return an existing instance
        mock_get.return_value = mock.Mock()

        ex = self.assertRaises(rpc.ExpectedException,
                               self.eng.receiver_create,
                               self.ctx, 'r1', 'webhook', 'C1',
                               'CLUSTER_RESIZE')
        self.assertEqual(exc.BadRequest, ex.exc_info[0])
        self.assertEqual("The request is malformed: A receiver named 'r1' "
                         "already exists.",
                         six.text_type(ex.exc_info[1]))

    def test_receiver_create_bad_type(self):
        ex = self.assertRaises(rpc.ExpectedException,
                               self.eng.receiver_create,
                               self.ctx, 'r1', 'rocket', 'C1',
                               'CLUSTER_RESIZE')
        self.assertEqual(exc.BadRequest, ex.exc_info[0])
        self.assertEqual("The request is malformed: Receiver type 'rocket' "
                         "is not supported.",
                         six.text_type(ex.exc_info[1]))

    @mock.patch.object(service.EngineService, 'cluster_find')
    def test_receiver_create_cluster_not_found(self, mock_find):
        mock_find.side_effect = exc.ClusterNotFound(cluster='C1')
        ex = self.assertRaises(rpc.ExpectedException,
                               self.eng.receiver_create,
                               self.ctx, 'r1', 'webhook', 'C1', 'whatever')
        self.assertEqual(exc.BadRequest, ex.exc_info[0])
        self.assertEqual("The request is malformed: The referenced cluster "
                         "'C1' is not found.",
                         six.text_type(ex.exc_info[1]))

    @mock.patch.object(service.EngineService, 'cluster_find')
    @mock.patch.object(rb.Receiver, 'create')
    def test_receiver_create_forbidden(self, mock_create, mock_find):
        fake_cluster = mock.Mock()
        fake_cluster.user = 'someone'
        mock_find.return_value = fake_cluster

        ex = self.assertRaises(rpc.ExpectedException,
                               self.eng.receiver_create,
                               self.ctx, 'r1', 'webhook', 'C1', 'FLY')
        self.assertEqual(exc.Forbidden, ex.exc_info[0])

        fake_receiver = mock.Mock(id='FAKE_RECIEVER')
        fake_receiver.to_dict.return_value = {
            'id': 'FAKE_RECEIVER',
            'foo': 'bar'
        }
        mock_create.return_value = fake_receiver

        # an admin can do this
        self.ctx.is_admin = True
        result = self.eng.receiver_create(self.ctx, 'r1', 'webhook', 'C1',
                                          'CLUSTER_RESIZE')
        self.assertIsInstance(result, dict)
        # All other tests are done in 'test_receiver_create'

    @mock.patch.object(service.EngineService, 'cluster_find')
    def test_receiver_create_bad_action(self, mock_find):
        fake_cluster = mock.Mock()
        fake_cluster.user = self.ctx.user
        mock_find.return_value = fake_cluster

        ex = self.assertRaises(rpc.ExpectedException,
                               self.eng.receiver_create,
                               self.ctx, 'r1', 'webhook', 'C1', 'DANCE')
        self.assertEqual(exc.BadRequest, ex.exc_info[0])
        self.assertEqual("The request is malformed: Illegal action 'DANCE' "
                         "specified.",
                         six.text_type(ex.exc_info[1]))

        ex = self.assertRaises(rpc.ExpectedException,
                               self.eng.receiver_create,
                               self.ctx, 'r1', 'webhook', 'C1', 'NODE_JOIN')
        self.assertEqual(exc.BadRequest, ex.exc_info[0])
        self.assertEqual("The request is malformed: Action 'NODE_JOIN' is "
                         "not applicable to clusters.",
                         six.text_type(ex.exc_info[1]))

    @mock.patch.object(rb.Receiver, 'load')
    def test_receiver_get(self, mock_load):
        fake_obj = mock.Mock()
        mock_find = self.patchobject(self.eng, 'receiver_find',
                                     return_value=fake_obj)
        fake_receiver = mock.Mock()
        fake_receiver.to_dict.return_value = {'FOO': 'BAR'}
        mock_load.return_value = fake_receiver

        res = self.eng.receiver_get(self.ctx, 'FAKE_ID')

        self.assertEqual({'FOO': 'BAR'}, res)
        mock_find.assert_called_once_with(self.ctx, 'FAKE_ID',
                                          project_safe=True)
        mock_load.assert_called_once_with(self.ctx,
                                          receiver_obj=fake_obj,
                                          project_safe=True)

    @mock.patch.object(service.EngineService, 'receiver_find')
    def test_receiver_get_not_found(self, mock_find):

        mock_find.side_effect = exc.ReceiverNotFound(receiver='RR')

        ex = self.assertRaises(rpc.ExpectedException,
                               self.eng.receiver_get, self.ctx, 'Bogus')
        self.assertEqual(exc.ReceiverNotFound, ex.exc_info[0])

    @mock.patch.object(service.EngineService, 'receiver_find')
    @mock.patch.object(ro.Receiver, 'delete')
    def test_receiver_delete(self, mock_delete, mock_find):
        fake_obj = mock.Mock()
        fake_obj.id = 'FAKE_ID'
        mock_find.return_value = fake_obj

        result = self.eng.receiver_delete(self.ctx, 'FAKE_RECEIVER')

        self.assertIsNone(result)
        mock_find.assert_called_once_with(self.ctx, 'FAKE_RECEIVER')
        mock_delete.assert_called_once_with(self.ctx, 'FAKE_ID')

    @mock.patch.object(service.EngineService, 'receiver_find')
    def test_receiver_delete_not_found(self, mock_find):
        mock_find.side_effect = exc.ReceiverNotFound(receiver='RR')

        ex = self.assertRaises(rpc.ExpectedException,
                               self.eng.receiver_delete, self.ctx, 'Bogus')
        self.assertEqual(exc.ReceiverNotFound, ex.exc_info[0])
