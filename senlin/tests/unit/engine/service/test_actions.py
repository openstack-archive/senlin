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
from oslo_messaging.rpc import dispatcher as rpc
from oslo_utils import uuidutils
import six

from senlin.common import exception as exc
from senlin.engine.actions import base as action_base
from senlin.engine import service
from senlin.objects import action as ao
from senlin.tests.unit.common import base
from senlin.tests.unit.common import utils


class ActionTest(base.SenlinTestCase):

    def setUp(self):
        super(ActionTest, self).setUp()
        self.ctx = utils.dummy_context(project='action_test_project')
        self.eng = service.EngineService('host-a', 'topic-a')
        self.eng.init_tgm()

    @mock.patch.object(ao.Action, 'get')
    def test_action_find_by_uuid(self, mock_get):
        x_action = mock.Mock()
        mock_get.return_value = x_action

        aid = uuidutils.generate_uuid()
        result = self.eng.action_find(self.ctx, aid)

        self.assertEqual(x_action, result)
        mock_get.assert_called_once_with(self.ctx, aid, project_safe=True)

    @mock.patch.object(ao.Action, 'get_by_name')
    @mock.patch.object(ao.Action, 'get')
    def test_action_find_by_uuid_as_name(self, mock_get, mock_get_name):
        x_action = mock.Mock()
        mock_get_name.return_value = x_action
        mock_get.return_value = None

        aid = uuidutils.generate_uuid()
        result = self.eng.action_find(self.ctx, aid, False)

        self.assertEqual(x_action, result)
        mock_get.assert_called_once_with(self.ctx, aid, project_safe=False)
        mock_get_name.assert_called_once_with(self.ctx, aid,
                                              project_safe=False)

    @mock.patch.object(ao.Action, 'get_by_name')
    def test_action_find_by_name(self, mock_get_name):
        x_action = mock.Mock()
        mock_get_name.return_value = x_action

        aid = 'this-is-not-uuid'
        result = self.eng.action_find(self.ctx, aid)

        self.assertEqual(x_action, result)
        mock_get_name.assert_called_once_with(self.ctx, aid, project_safe=True)

    @mock.patch.object(ao.Action, 'get_by_short_id')
    @mock.patch.object(ao.Action, 'get_by_name')
    def test_action_find_by_shortid(self, mock_get_name, mock_get_shortid):
        x_action = mock.Mock()
        mock_get_shortid.return_value = x_action
        mock_get_name.return_value = None

        aid = 'abcd-1234-abcd'
        result = self.eng.action_find(self.ctx, aid, False)

        self.assertEqual(x_action, result)
        mock_get_name.assert_called_once_with(self.ctx, aid,
                                              project_safe=False)
        mock_get_shortid.assert_called_once_with(self.ctx, aid,
                                                 project_safe=False)

    @mock.patch.object(ao.Action, 'get_by_name')
    def test_action_find_not_found(self, mock_get_name):
        mock_get_name.return_value = None

        ex = self.assertRaises(exc.ActionNotFound,
                               self.eng.action_find,
                               self.ctx, 'bogus')
        self.assertEqual('The action (bogus) could not be found.',
                         six.text_type(ex))
        mock_get_name.assert_called_once_with(self.ctx, 'bogus',
                                              project_safe=True)

    @mock.patch.object(action_base.Action, 'load_all')
    def test_action_list(self, mock_load):
        x_1 = mock.Mock()
        x_1.to_dict.return_value = {'k': 'v1'}
        x_2 = mock.Mock()
        x_2.to_dict.return_value = {'k': 'v2'}

        mock_load.return_value = [x_1, x_2]

        result = self.eng.action_list(self.ctx)
        expected = [{'k': 'v1'}, {'k': 'v2'}]
        self.assertEqual(expected, result)

        mock_load.assert_called_once_with(self.ctx, filters=None, limit=None,
                                          marker=None, sort=None,
                                          project_safe=True)

    @mock.patch.object(action_base.Action, 'load_all')
    def test_action_list_with_params(self, mock_load):
        mock_load.return_value = []

        result = self.eng.action_list(self.ctx, filters='F', limit=1,
                                      marker='M', sort='status',
                                      project_safe=True)

        self.assertEqual([], result)

        mock_load.assert_called_once_with(self.ctx, filters='F', limit=1,
                                          marker='M', sort='status',
                                          project_safe=True)

    def test_action_list_with_bad_params(self):
        ex = self.assertRaises(rpc.ExpectedException,
                               self.eng.action_list,
                               self.ctx, limit='large')
        self.assertEqual(exc.InvalidParameter, ex.exc_info[0])

        ex = self.assertRaises(rpc.ExpectedException,
                               self.eng.action_list,
                               self.ctx, sort='crazykey')
        self.assertEqual(exc.InvalidParameter, ex.exc_info[0])

        ex = self.assertRaises(rpc.ExpectedException,
                               self.eng.action_list,
                               self.ctx, project_safe='yes')
        self.assertEqual(exc.InvalidParameter, ex.exc_info[0])

    @mock.patch.object(action_base.Action, 'load_all')
    def test_action_list_with_project_safe(self, mock_load):
        mock_load.return_value = []

        result = self.eng.action_list(self.ctx)
        self.assertEqual([], result)
        mock_load.assert_called_once_with(self.ctx, filters=None, limit=None,
                                          sort=None, marker=None,
                                          project_safe=True)
        mock_load.reset_mock()

        ex = self.assertRaises(rpc.ExpectedException,
                               self.eng.action_list,
                               self.ctx, project_safe=False)
        self.assertEqual(exc.Forbidden, ex.exc_info[0])

        self.ctx.is_admin = True

        result = self.eng.action_list(self.ctx)
        self.assertEqual([], result)
        mock_load.assert_called_once_with(self.ctx, filters=None, limit=None,
                                          sort=None, marker=None,
                                          project_safe=True)
        mock_load.reset_mock()

        result = self.eng.action_list(self.ctx, project_safe=True)
        self.assertEqual([], result)
        mock_load.assert_called_once_with(self.ctx, filters=None, limit=None,
                                          sort=None, marker=None,
                                          project_safe=True)
        mock_load.reset_mock()

        result = self.eng.action_list(self.ctx, project_safe=False)
        self.assertEqual([], result)
        mock_load.assert_called_once_with(self.ctx, filters=None, limit=None,
                                          sort=None, marker=None,
                                          project_safe=False)

    @mock.patch.object(action_base.Action, 'create')
    @mock.patch.object(service.EngineService, 'cluster_find')
    def test_action_create(self, mock_find, mock_action):
        mock_find.return_value = mock.Mock(id='FAKE_CLUSTER')
        mock_action.return_value = 'ACTION_ID'

        result = self.eng.action_create(self.ctx, 'a1', 'C1', 'OBJECT_ACTION')

        self.assertEqual({'action': 'ACTION_ID'}, result)
        mock_find.assert_called_once_with(self.ctx, 'C1')
        mock_action.assert_called_once_with(
            self.ctx, 'FAKE_CLUSTER', 'OBJECT_ACTION',
            name='a1',
            cause=action_base.CAUSE_RPC,
            status=action_base.Action.READY,
            inputs={})

    @mock.patch.object(service.EngineService, 'cluster_find')
    def test_action_create_cluster_not_found(self, mock_find):
        mock_find.side_effect = exc.ClusterNotFound(cluster='C1')

        ex = self.assertRaises(rpc.ExpectedException,
                               self.eng.action_create,
                               self.ctx, 'a1', 'C1', 'OBJECT_ACTION')

        self.assertEqual(exc.ClusterNotFound, ex.exc_info[0])
        mock_find.assert_called_once_with(self.ctx, 'C1')

    @mock.patch.object(action_base.Action, 'load')
    @mock.patch.object(service.EngineService, 'action_find')
    def test_action_get(self, mock_find, mock_load):
        x_obj = mock.Mock()
        mock_find.return_value = x_obj
        x_action = mock.Mock()
        x_action.to_dict.return_value = {'k': 'v'}
        mock_load.return_value = x_action

        result = self.eng.action_get(self.ctx, 'ACTION_ID')

        self.assertEqual({'k': 'v'}, result)
        mock_find.assert_called_once_with(self.ctx, 'ACTION_ID')
        mock_load.assert_called_once_with(self.ctx, db_action=x_obj)

    @mock.patch.object(service.EngineService, 'action_find')
    def test_action_get_not_found(self, mock_find):
        mock_find.side_effect = exc.ActionNotFound(action='Bogus')

        ex = self.assertRaises(rpc.ExpectedException,
                               self.eng.action_get,
                               self.ctx, 'Bogus')
        self.assertEqual(exc.ActionNotFound, ex.exc_info[0])
        mock_find.assert_called_once_with(self.ctx, 'Bogus')

    @mock.patch.object(action_base.Action, 'delete')
    @mock.patch.object(service.EngineService, 'action_find')
    def test_action_delete(self, mock_find, mock_delete):
        x_obj = mock.Mock()
        x_obj.id = 'FAKE_ID'
        mock_find.return_value = x_obj
        mock_delete.return_value = None

        result = self.eng.action_delete(self.ctx, 'ACTION')
        self.assertIsNone(result)
        mock_find.assert_called_once_with(self.ctx, 'ACTION')
        mock_delete.assert_called_once_with(self.ctx, 'FAKE_ID')

    @mock.patch.object(action_base.Action, 'delete')
    @mock.patch.object(service.EngineService, 'action_find')
    def test_action_delete_resource_busy(self, mock_find, mock_delete):
        x_obj = mock.Mock()
        x_obj.id = 'FAKE_ID'
        mock_find.return_value = x_obj
        ex = exc.ResourceBusyError(resource_type='action',
                                   resource_id='FAKE_ID')
        mock_delete.side_effect = ex

        ex = self.assertRaises(rpc.ExpectedException,
                               self.eng.action_delete,
                               self.ctx, 'ACTION')

        self.assertEqual(exc.ResourceInUse, ex.exc_info[0])
        mock_find.assert_called_once_with(self.ctx, 'ACTION')
        mock_delete.assert_called_once_with(self.ctx, 'FAKE_ID')

    @mock.patch.object(service.EngineService, 'action_find')
    def test_action_delete_not_found(self, mock_find):
        mock_find.side_effect = exc.ActionNotFound(action='Bogus')

        ex = self.assertRaises(rpc.ExpectedException,
                               self.eng.action_delete,
                               self.ctx, 'Bogus')

        self.assertEqual(exc.ActionNotFound, ex.exc_info[0])
