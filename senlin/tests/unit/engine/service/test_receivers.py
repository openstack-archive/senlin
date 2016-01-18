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

from senlin.common import exception
from senlin.common.i18n import _
from senlin.db.sqlalchemy import api as db_api
from senlin.engine import receiver
from senlin.engine import service
from senlin.tests.unit.common import base
from senlin.tests.unit.common import utils


class ReceiverTest(base.SenlinTestCase):

    def setUp(self):
        super(ReceiverTest, self).setUp()
        self.ctx = utils.dummy_context(project='receiver_test_project')
        self.eng = service.EngineService('host-a', 'topic-a')
        self.eng.init_tgm()

    @mock.patch.object(db_api, 'receiver_get')
    @mock.patch.object(db_api, 'receiver_get_by_name')
    def test_receiver_find_by_id(self, mock_get_name, mock_get):
        fake_obj = mock.Mock()
        mock_get.return_value = fake_obj
        fake_id = uuidutils.generate_uuid()

        # Found: project_safe True
        res = self.eng.receiver_find(self.ctx, fake_id)
        self.assertEqual(fake_obj, res)
        mock_get.assert_called_once_with(self.ctx, fake_id, project_safe=True)
        mock_get.reset_mock()

        # Found: project_safe False
        res = self.eng.receiver_find(self.ctx, fake_id, False)
        self.assertEqual(fake_obj, res)
        mock_get.assert_called_once_with(self.ctx, fake_id, project_safe=False)
        mock_get.reset_mock()

        # Not Found: project_safe True
        mock_get.return_value = None
        mock_get_name.return_value = fake_obj
        res = self.eng.receiver_find(self.ctx, fake_id)
        self.assertEqual(fake_obj, res)
        mock_get.assert_called_once_with(self.ctx, fake_id, project_safe=True)
        mock_get_name.assert_called_once_with(self.ctx, fake_id,
                                              project_safe=True)
        mock_get.reset_mock()
        mock_get_name.reset_mock()

        # Not Found: project_safe False
        res = self.eng.receiver_find(self.ctx, fake_id, False)
        self.assertEqual(fake_obj, res)
        mock_get.assert_called_once_with(self.ctx, fake_id, project_safe=False)
        mock_get_name.assert_called_once_with(self.ctx, fake_id,
                                              project_safe=False)
        mock_get.reset_mock()
        mock_get_name.reset_mock()

        # No luck at all
        mock_get_name.return_value = None
        self.assertRaises(exception.ReceiverNotFound,
                          self.eng.receiver_find,
                          self.ctx, fake_id, True)

    @mock.patch.object(db_api, 'receiver_get_by_name')
    @mock.patch.object(db_api, 'receiver_get_by_short_id')
    def test_receiver_find_by_name_short_id(self, x_get_short, x_get_name):
        fake_obj = mock.Mock()
        x_get_name.return_value = fake_obj
        fake_id = 'aaaa-bbbb'

        # Found: project_safe True
        res = self.eng.receiver_find(self.ctx, fake_id)
        self.assertEqual(fake_obj, res)
        x_get_name.assert_called_once_with(self.ctx, fake_id,
                                           project_safe=True)
        x_get_name.reset_mock()

        # Found: project_safe False
        res = self.eng.receiver_find(self.ctx, fake_id, False)
        self.assertEqual(fake_obj, res)
        x_get_name.assert_called_once_with(self.ctx, fake_id,
                                           project_safe=False)
        x_get_name.reset_mock()

        # Not Found: project_safe True
        x_get_name.return_value = None
        x_get_short.return_value = fake_obj
        res = self.eng.receiver_find(self.ctx, fake_id)
        self.assertEqual(fake_obj, res)
        x_get_name.assert_called_once_with(self.ctx, fake_id,
                                           project_safe=True)
        x_get_short.assert_called_once_with(self.ctx, fake_id,
                                            project_safe=True)
        x_get_name.reset_mock()
        x_get_short.reset_mock()

        # Not Found: project_safe False
        res = self.eng.receiver_find(self.ctx, fake_id, False)
        self.assertEqual(fake_obj, res)
        x_get_name.assert_called_once_with(self.ctx, fake_id,
                                           project_safe=False)
        x_get_short.assert_called_once_with(self.ctx, fake_id,
                                            project_safe=False)

        # No luck at all
        x_get_short.return_value = None
        self.assertRaises(exception.ReceiverNotFound,
                          self.eng.receiver_find,
                          self.ctx, fake_id, True)

    @mock.patch.object(receiver.Receiver, 'load_all')
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

    @mock.patch.object(receiver.Receiver, 'load_all')
    def test_receiver_list_with_params(self, mock_load):
        fake_obj = mock.Mock()
        fake_obj.to_dict.return_value = {'FOO': 'BAR'}
        mock_load.return_value = [fake_obj]

        result = self.eng.receiver_list(self.ctx, limit=1, marker='MARKER',
                                        sort='KEY', filters={'key1': 'value1'},
                                        project_safe=False)

        self.assertIsInstance(result, list)
        self.assertEqual([{'FOO': 'BAR'}], result)
        mock_load.assert_called_once_with(self.ctx, limit=1, marker='MARKER',
                                          sort='KEY',
                                          filters={'key1': 'value1'},
                                          project_safe=False)

    def test_receiver_list_bad_params(self):
        ex = self.assertRaises(rpc.ExpectedException,
                               self.eng.receiver_list, self.ctx, limit='no')
        self.assertEqual(exception.InvalidParameter, ex.exc_info[0])

        ex = self.assertRaises(rpc.ExpectedException,
                               self.eng.receiver_list,
                               self.ctx, project_safe='yes')
        self.assertEqual(exception.InvalidParameter, ex.exc_info[0])

    @mock.patch.object(service.EngineService, 'cluster_find')
    @mock.patch.object(receiver.Receiver, 'create')
    def test_receiver_create_okay(self, mock_create, mock_find):
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

    @mock.patch.object(db_api, 'receiver_get_by_name')
    def test_receiver_create_name_duplicated(self, mock_get):
        cfg.CONF.set_override('name_unique', True, enforce_type=True)
        # Return an existing instance
        mock_get.return_value = mock.Mock()

        ex = self.assertRaises(rpc.ExpectedException,
                               self.eng.receiver_create,
                               self.ctx, 'r1', 'webhook', 'C1',
                               'CLUSTER_RESIZE')
        self.assertEqual(exception.SenlinBadRequest, ex.exc_info[0])
        self.assertEqual(_("The request is malformed: A receiver named 'r1' "
                           "already exists."),
                         six.text_type(ex.exc_info[1]))

    def test_receiver_create_bad_type(self):
        ex = self.assertRaises(rpc.ExpectedException,
                               self.eng.receiver_create,
                               self.ctx, 'r1', 'rocket', 'C1',
                               'CLUSTER_RESIZE')
        self.assertEqual(exception.SenlinBadRequest, ex.exc_info[0])
        self.assertEqual(_("The request is malformed: Receiver type 'rocket' "
                           "is not supported."),
                         six.text_type(ex.exc_info[1]))

    @mock.patch.object(service.EngineService, 'cluster_find')
    def test_receiver_create_cluster_not_found(self, mock_find):
        mock_find.side_effect = exception.ClusterNotFound(cluster='C1')
        ex = self.assertRaises(rpc.ExpectedException,
                               self.eng.receiver_create,
                               self.ctx, 'r1', 'webhook', 'C1', 'whatever')
        self.assertEqual(exception.SenlinBadRequest, ex.exc_info[0])
        self.assertEqual("The request is malformed: The referenced cluster "
                         "'C1' is not found.",
                         six.text_type(ex.exc_info[1]))

    @mock.patch.object(service.EngineService, 'cluster_find')
    @mock.patch.object(receiver.Receiver, 'create')
    def test_receiver_create_forbidden(self, mock_create, mock_find):
        fake_cluster = mock.Mock()
        fake_cluster.user = 'someone'
        mock_find.return_value = fake_cluster

        ex = self.assertRaises(rpc.ExpectedException,
                               self.eng.receiver_create,
                               self.ctx, 'r1', 'webhook', 'C1', 'FLY')
        self.assertEqual(exception.Forbidden, ex.exc_info[0])

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
        # All other tests are done in 'test_receiver_create_okay'

    @mock.patch.object(service.EngineService, 'cluster_find')
    def test_receiver_create_bad_action(self, mock_find):
        fake_cluster = mock.Mock()
        fake_cluster.user = self.ctx.user
        mock_find.return_value = fake_cluster

        ex = self.assertRaises(rpc.ExpectedException,
                               self.eng.receiver_create,
                               self.ctx, 'r1', 'webhook', 'C1', 'DANCE')
        self.assertEqual(exception.SenlinBadRequest, ex.exc_info[0])
        self.assertEqual("The request is malformed: Illegal action 'DANCE' "
                         "specified.",
                         six.text_type(ex.exc_info[1]))

        ex = self.assertRaises(rpc.ExpectedException,
                               self.eng.receiver_create,
                               self.ctx, 'r1', 'webhook', 'C1', 'NODE_JOIN')
        self.assertEqual(exception.SenlinBadRequest, ex.exc_info[0])
        self.assertEqual("The request is malformed: Action 'NODE_JOIN' is "
                         "not applicable to clusters.",
                         six.text_type(ex.exc_info[1]))

    @mock.patch.object(receiver.Receiver, 'load')
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

        # Simulate not found
        mock_find = self.patchobject(self.eng, 'receiver_find')
        mock_find.side_effect = exception.ReceiverNotFound(receiver='RR')

        ex = self.assertRaises(rpc.ExpectedException,
                               self.eng.receiver_get, self.ctx, 'Bogus')
        self.assertEqual(exception.ReceiverNotFound, ex.exc_info[0])

    @mock.patch.object(db_api, 'receiver_delete')
    def test_receiver_delete(self, mock_delete):
        fake_obj = mock.Mock()
        fake_obj.id = 'FAKE_ID'
        mock_find = self.patchobject(self.eng, 'receiver_find',
                                     return_value=fake_obj)

        result = self.eng.receiver_delete(self.ctx, 'FAKE_RECEIVER')

        self.assertIsNone(result)
        mock_find.assert_called_once_with(self.ctx, 'FAKE_RECEIVER')
        mock_delete.assert_called_once_with(self.ctx, 'FAKE_ID')

    def test_receiver_delete_not_found(self):
        mock_find = self.patchobject(self.eng, 'receiver_find')
        mock_find.side_effect = exception.ReceiverNotFound(receiver='RR')

        ex = self.assertRaises(rpc.ExpectedException,
                               self.eng.receiver_delete, self.ctx, 'Bogus')
        self.assertEqual(exception.ReceiverNotFound, ex.exc_info[0])
