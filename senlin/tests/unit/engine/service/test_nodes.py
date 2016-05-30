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

from senlin.common import consts
from senlin.common import exception as exc
from senlin.common.i18n import _
from senlin.engine.actions import base as action_mod
from senlin.engine import dispatcher
from senlin.engine import node as node_mod
from senlin.engine import service
from senlin.objects import cluster as co
from senlin.objects import node as no
from senlin.tests.unit.common import base
from senlin.tests.unit.common import utils


class NodeTest(base.SenlinTestCase):

    def setUp(self):
        super(NodeTest, self).setUp()
        self.ctx = utils.dummy_context(project='node_test_project')
        self.eng = service.EngineService('host-a', 'topic-a')

    @mock.patch.object(no.Node, 'get')
    def test_node_find_by_uuid(self, mock_get):
        x_node = mock.Mock()
        mock_get.return_value = x_node
        aid = uuidutils.generate_uuid()

        result = self.eng.node_find(self.ctx, aid)

        self.assertEqual(x_node, result)
        mock_get.assert_called_once_with(self.ctx, aid, project_safe=True)

    @mock.patch.object(no.Node, 'get_by_name')
    @mock.patch.object(no.Node, 'get')
    def test_node_find_by_uuid_as_name(self, mock_get, mock_name):
        mock_get.return_value = None
        x_node = mock.Mock()
        mock_name.return_value = x_node
        aid = uuidutils.generate_uuid()

        result = self.eng.node_find(self.ctx, aid, False)

        self.assertEqual(x_node, result)
        mock_get.assert_called_once_with(self.ctx, aid, project_safe=False)
        mock_name.assert_called_once_with(self.ctx, aid, project_safe=False)

    @mock.patch.object(no.Node, 'get_by_name')
    def test_node_find_by_name(self, mock_name):
        x_node = mock.Mock()
        mock_name.return_value = x_node
        aid = 'not-a-uuid'

        result = self.eng.node_find(self.ctx, aid)

        self.assertEqual(x_node, result)
        mock_name.assert_called_once_with(self.ctx, aid, project_safe=True)

    @mock.patch.object(no.Node, 'get_by_short_id')
    @mock.patch.object(no.Node, 'get_by_name')
    def test_node_find_by_short_id(self, mock_name, mock_shortid):
        mock_name.return_value = None
        x_node = mock.Mock()
        mock_shortid.return_value = x_node
        aid = 'abcdef'

        result = self.eng.node_find(self.ctx, aid, False)

        self.assertEqual(x_node, result)
        mock_name.assert_called_once_with(self.ctx, aid, project_safe=False)
        mock_shortid.assert_called_once_with(self.ctx, aid, project_safe=False)

    @mock.patch.object(no.Node, 'get_by_short_id')
    def test_node_find_not_found(self, mock_shortid):
        mock_shortid.return_value = None

        ex = self.assertRaises(exc.NodeNotFound,
                               self.eng.node_find,
                               self.ctx, 'BOGUS')
        self.assertEqual("The node (BOGUS) could not be found.",
                         six.text_type(ex))
        mock_shortid.assert_called_once_with(self.ctx, 'BOGUS',
                                             project_safe=True)

    @mock.patch.object(node_mod.Node, 'load_all')
    def test_node_list(self, mock_load):
        obj_1 = mock.Mock()
        obj_1.to_dict.return_value = {'k': 'v1'}
        obj_2 = mock.Mock()
        obj_2.to_dict.return_value = {'k': 'v2'}

        mock_load.return_value = [obj_1, obj_2]

        result = self.eng.node_list(self.ctx)

        self.assertEqual([{'k': 'v1'}, {'k': 'v2'}], result)
        mock_load.assert_called_once_with(
            self.ctx, cluster_id=None, filters=None, sort=None,
            limit=None, marker=None, project_safe=True)

    @mock.patch.object(service.EngineService, 'cluster_find')
    @mock.patch.object(node_mod.Node, 'load_all')
    def test_node_list_with_cluster_id(self, mock_load, mock_find):
        obj_1 = mock.Mock()
        obj_1.to_dict.return_value = {'k': 'v1'}
        obj_2 = mock.Mock()
        obj_2.to_dict.return_value = {'k': 'v2'}
        mock_load.return_value = [obj_1, obj_2]
        mock_find.return_value = mock.Mock(id='FAKE_CLUSTER')

        result = self.eng.node_list(self.ctx, cluster_id='MY_CLUSTER',
                                    filters={'K': 'V'}, sort='name',
                                    limit=123, marker='MMM',
                                    project_safe=True)

        self.assertEqual([{'k': 'v1'}, {'k': 'v2'}], result)
        mock_find.assert_called_once_with(self.ctx, 'MY_CLUSTER')
        mock_load.assert_called_once_with(self.ctx, cluster_id='FAKE_CLUSTER',
                                          filters={'K': 'V'}, sort='name',
                                          limit=123, marker='MMM',
                                          project_safe=True)

    @mock.patch.object(node_mod.Node, 'load_all')
    def test_node_list_with_params(self, mock_load):
        obj_1 = mock.Mock()
        obj_1.to_dict.return_value = {'k': 'v1'}
        obj_2 = mock.Mock()
        obj_2.to_dict.return_value = {'k': 'v2'}

        mock_load.return_value = [obj_1, obj_2]

        result = self.eng.node_list(self.ctx, cluster_id=None, filters='FFF',
                                    sort='status', limit=123, marker='MMM',
                                    project_safe=True)

        self.assertEqual([{'k': 'v1'}, {'k': 'v2'}], result)
        mock_load.assert_called_once_with(self.ctx, cluster_id=None,
                                          filters='FFF', sort='status',
                                          limit=123, marker='MMM',
                                          project_safe=True)

    def test_node_list_bad_limit(self):
        ex = self.assertRaises(rpc.ExpectedException,
                               self.eng.node_list,
                               self.ctx, limit='MANY')
        self.assertEqual(exc.InvalidParameter, ex.exc_info[0])
        self.assertEqual("Invalid value 'MANY' specified for 'limit'",
                         six.text_type(ex.exc_info[1]))

    def test_node_list_bad_sort(self):
        ex = self.assertRaises(rpc.ExpectedException,
                               self.eng.node_list,
                               self.ctx, sort='crazykey')
        self.assertEqual(exc.InvalidParameter, ex.exc_info[0])
        self.assertEqual("Invalid value 'crazykey' specified for 'sort key'",
                         six.text_type(ex.exc_info[1]))

    def test_node_list_bad_project_safe(self):
        ex = self.assertRaises(rpc.ExpectedException,
                               self.eng.node_list,
                               self.ctx, project_safe='yes')
        self.assertEqual(exc.InvalidParameter, ex.exc_info[0])
        self.assertEqual("Invalid value 'yes' specified for 'project_safe'",
                         six.text_type(ex.exc_info[1]))

    @mock.patch.object(service.EngineService, 'cluster_find')
    def test_node_list_cluster_not_found(self, mock_find):
        mock_find.side_effect = exc.ClusterNotFound(cluster='BOGUS')

        ex = self.assertRaises(rpc.ExpectedException,
                               self.eng.node_list,
                               self.ctx, cluster_id='BOGUS')

        self.assertEqual(exc.ClusterNotFound, ex.exc_info[0])
        self.assertEqual("The cluster (BOGUS) could not be found.",
                         six.text_type(ex.exc_info[1]))
        mock_find.assert_called_once_with(self.ctx, 'BOGUS')

    @mock.patch.object(node_mod.Node, 'load_all')
    def test_node_list_with_project_safe(self, mock_load):
        mock_load.return_value = []

        result = self.eng.node_list(self.ctx)
        self.assertEqual([], result)
        mock_load.assert_called_once_with(self.ctx, filters=None, limit=None,
                                          sort=None, marker=None,
                                          cluster_id=None, project_safe=True)
        mock_load.reset_mock()

        ex = self.assertRaises(rpc.ExpectedException,
                               self.eng.node_list,
                               self.ctx, project_safe=False)
        self.assertEqual(exc.Forbidden, ex.exc_info[0])

        self.ctx.is_admin = True

        result = self.eng.node_list(self.ctx)
        self.assertEqual([], result)
        mock_load.assert_called_once_with(self.ctx, filters=None, limit=None,
                                          sort=None, marker=None,
                                          cluster_id=None, project_safe=True)
        mock_load.reset_mock()

        result = self.eng.node_list(self.ctx, project_safe=True)
        self.assertEqual([], result)
        mock_load.assert_called_once_with(self.ctx, filters=None, limit=None,
                                          sort=None, marker=None,
                                          cluster_id=None, project_safe=True)
        mock_load.reset_mock()

        result = self.eng.node_list(self.ctx, project_safe=False)
        self.assertEqual([], result)
        mock_load.assert_called_once_with(self.ctx, filters=None, limit=None,
                                          sort=None, marker=None,
                                          cluster_id=None, project_safe=False)

    @mock.patch.object(node_mod.Node, 'load_all')
    def test_node_list_empty(self, mock_load):
        mock_load.return_value = []

        result = self.eng.node_list(self.ctx)

        self.assertEqual([], result)
        mock_load.assert_called_once_with(self.ctx, cluster_id=None,
                                          filters=None, sort=None,
                                          limit=None, marker=None,
                                          project_safe=True)

    @mock.patch.object(action_mod.Action, 'create')
    @mock.patch('senlin.engine.node.Node')
    @mock.patch.object(service.EngineService, 'profile_find')
    @mock.patch.object(dispatcher, 'start_action')
    def test_node_create(self, notify, mock_profile, mock_node, mock_action):
        mock_profile.return_value = mock.Mock(id='PROFILE_ID')
        x_node = mock.Mock(id='NODE_ID')
        x_node.to_dict.return_value = {'foo': 'bar'}
        mock_node.return_value = x_node
        mock_action.return_value = 'ACTION_ID'

        result = self.eng.node_create(self.ctx, 'NODE1', 'FAKE_PROFILE')

        self.assertEqual({'foo': 'bar', 'action': 'ACTION_ID'}, result)
        mock_profile.assert_called_once_with(self.ctx, 'FAKE_PROFILE')
        mock_node.assert_called_once_with(
            'NODE1', 'PROFILE_ID', '', self.ctx,
            index=-1, role=None, metadata={},
            user=self.ctx.user,
            project=self.ctx.project,
            domain=self.ctx.domain)
        x_node.store.assert_called_once_with(self.ctx)
        mock_action.assert_called_once_with(
            self.ctx, 'NODE_ID', consts.NODE_CREATE,
            name='node_create_NODE_ID',
            cause=action_mod.CAUSE_RPC,
            status=action_mod.Action.READY)
        notify.assert_called_once_with()

    @mock.patch.object(action_mod.Action, 'create')
    @mock.patch('senlin.engine.node.Node')
    @mock.patch.object(co.Cluster, 'get_next_index')
    @mock.patch.object(service.EngineService, 'cluster_find')
    @mock.patch.object(service.EngineService, 'profile_find')
    @mock.patch.object(dispatcher, 'start_action')
    def test_node_create_same_profile(self, notify, mock_profile, mock_cluster,
                                      mock_index, mock_node, mock_action):
        mock_profile.return_value = mock.Mock(id='PROFILE_ID',
                                              type='PROFILE_TYPE')
        x_cluster = mock.Mock(id='CLUSTER_ID', profile_id='PROFILE_ID')
        mock_cluster.return_value = x_cluster
        mock_index.return_value = 12345
        x_node = mock.Mock(id='NODE_ID')
        x_node.to_dict.return_value = {'foo': 'bar'}
        mock_node.return_value = x_node
        mock_action.return_value = 'ACTION_ID'

        result = self.eng.node_create(self.ctx, 'NODE1', 'FAKE_PROFILE',
                                      cluster_id='FAKE_CLUSTER')

        self.assertEqual({'foo': 'bar', 'action': 'ACTION_ID'}, result)
        mock_cluster.assert_called_once_with(self.ctx, 'FAKE_CLUSTER')
        mock_profile.assert_called_once_with(self.ctx, 'FAKE_PROFILE')
        mock_index.assert_called_once_with(self.ctx, 'CLUSTER_ID')
        mock_node.assert_called_once_with(
            'NODE1', 'PROFILE_ID', 'CLUSTER_ID', self.ctx,
            index=12345, role=None, metadata={},
            user=self.ctx.user,
            project=self.ctx.project,
            domain=self.ctx.domain)
        x_node.store.assert_called_once_with(self.ctx)
        mock_action.assert_called_once_with(
            self.ctx, 'NODE_ID', consts.NODE_CREATE,
            name='node_create_NODE_ID',
            cause=action_mod.CAUSE_RPC,
            status=action_mod.Action.READY)
        notify.assert_called_once_with()

    @mock.patch.object(action_mod.Action, 'create')
    @mock.patch('senlin.engine.node.Node')
    @mock.patch.object(co.Cluster, 'get_next_index')
    @mock.patch.object(service.EngineService, 'cluster_find')
    @mock.patch.object(service.EngineService, 'profile_find')
    @mock.patch.object(dispatcher, 'start_action')
    def test_node_create_same_profile_type(self, notify, mock_profile,
                                           mock_cluster, mock_index,
                                           mock_node, mock_action):
        mock_profile.side_effect = [
            mock.Mock(id='NODE_PROFILE_ID', type='PROFILE_TYPE'),
            mock.Mock(id='CLUSTER_PROFILE_ID', type='PROFILE_TYPE'),
        ]
        x_cluster = mock.Mock(id='CLUSTER_ID', profile_id='CLUSTER_PROFILE_ID')
        mock_cluster.return_value = x_cluster
        mock_index.return_value = 12345
        x_node = mock.Mock(id='NODE_ID')
        x_node.to_dict.return_value = {'foo': 'bar'}
        mock_node.return_value = x_node
        mock_action.return_value = 'ACTION_ID'

        result = self.eng.node_create(self.ctx, 'NODE1', 'FAKE_PROFILE',
                                      cluster_id='FAKE_CLUSTER')

        self.assertEqual({'foo': 'bar', 'action': 'ACTION_ID'}, result)
        mock_cluster.assert_called_once_with(self.ctx, 'FAKE_CLUSTER')
        mock_profile.assert_has_calls([
            mock.call(self.ctx, 'FAKE_PROFILE'),  # for node
            mock.call(self.ctx, 'CLUSTER_PROFILE_ID'),  # for cluster
        ])
        mock_index.assert_called_once_with(self.ctx, 'CLUSTER_ID')
        mock_node.assert_called_once_with(
            'NODE1', 'NODE_PROFILE_ID', 'CLUSTER_ID', self.ctx,
            index=12345, role=None, metadata={},
            user=self.ctx.user,
            project=self.ctx.project,
            domain=self.ctx.domain)
        x_node.store.assert_called_once_with(self.ctx)
        mock_action.assert_called_once_with(
            self.ctx, 'NODE_ID', consts.NODE_CREATE,
            name='node_create_NODE_ID',
            cause=action_mod.CAUSE_RPC,
            status=action_mod.Action.READY)
        notify.assert_called_once_with()

    @mock.patch.object(no.Node, 'get_by_name')
    def test_node_create_name_conflict(self, mock_get):
        cfg.CONF.set_override('name_unique', True, enforce_type=True)
        mock_get.return_value = mock.Mock()

        ex = self.assertRaises(rpc.ExpectedException,
                               self.eng.node_create,
                               self.ctx, 'node-1', 'FAKE_PROFILE')

        self.assertEqual(exc.BadRequest, ex.exc_info[0])
        self.assertEqual(_("The request is malformed: The node named "
                           "(node-1) already exists."),
                         six.text_type(ex.exc_info[1]))

    @mock.patch.object(service.EngineService, 'profile_find')
    def test_node_create_profile_not_found(self, mock_profile):
        mock_profile.side_effect = exc.ProfileNotFound(profile='Bogus')

        ex = self.assertRaises(rpc.ExpectedException,
                               self.eng.node_create,
                               self.ctx, 'n-1', 'Bogus')
        self.assertEqual(exc.BadRequest, ex.exc_info[0])
        self.assertEqual("The request is malformed: The specified profile "
                         "(Bogus) is not found.",
                         six.text_type(ex.exc_info[1]))
        mock_profile.assert_called_once_with(self.ctx, 'Bogus')

    @mock.patch.object(service.EngineService, 'cluster_find')
    @mock.patch.object(service.EngineService, 'profile_find')
    def test_node_create_cluster_not_found(self, mock_profile, mock_cluster):
        mock_profile.return_value = mock.Mock()
        mock_cluster.side_effect = exc.ClusterNotFound(cluster='Bogus')

        ex = self.assertRaises(rpc.ExpectedException,
                               self.eng.node_create,
                               self.ctx, 'node-1', 'FAKE_PROFILE',
                               cluster_id='Bogus')

        self.assertEqual(exc.BadRequest, ex.exc_info[0])
        self.assertEqual("The request is malformed: The specified cluster "
                         "(Bogus) is not found.",
                         six.text_type(ex.exc_info[1]))
        mock_profile.assert_called_once_with(self.ctx, 'FAKE_PROFILE')
        mock_cluster.assert_called_once_with(self.ctx, 'Bogus')

    @mock.patch.object(service.EngineService, 'cluster_find')
    @mock.patch.object(service.EngineService, 'profile_find')
    def test_node_create_profile_type_not_match(self, mock_profile,
                                                mock_cluster):
        mock_profile.side_effect = [
            mock.Mock(id='NODE_PROFILE_ID', type='TYPE-A'),
            mock.Mock(id='CLUSTER_PROFILE_ID', type='TYPE-B'),
        ]
        mock_cluster.return_value = mock.Mock(id='CLUSTER_ID',
                                              profile_id='CLUSTER_PROFILE_ID')

        ex = self.assertRaises(rpc.ExpectedException,
                               self.eng.node_create,
                               self.ctx, 'node-1', 'NODE_PROFILE',
                               cluster_id='FAKE_CLUSTER')

        self.assertEqual(exc.ProfileTypeNotMatch, ex.exc_info[0])
        self.assertEqual("Node and cluster have different profile type, "
                         "operation aborted.",
                         six.text_type(ex.exc_info[1]))
        mock_profile.assert_has_calls([
            mock.call(self.ctx, 'NODE_PROFILE'),
            mock.call(self.ctx, 'CLUSTER_PROFILE_ID'),
        ])
        mock_cluster.assert_called_once_with(self.ctx, 'FAKE_CLUSTER')

    @mock.patch.object(node_mod.Node, 'load')
    @mock.patch.object(service.EngineService, 'node_find')
    def test_node_get(self, mock_find, mock_load):
        x_obj = mock.Mock()
        mock_find.return_value = x_obj
        x_node = mock.Mock(physical_id='PHYSICAL_ID')
        x_node.to_dict.return_value = {'foo': 'bar'}
        mock_load.return_value = x_node

        result = self.eng.node_get(self.ctx, 'FAKE_NODE')

        self.assertEqual({'foo': 'bar'}, result)
        mock_find.assert_called_once_with(self.ctx, 'FAKE_NODE')
        mock_load.assert_called_once_with(self.ctx, db_node=x_obj)
        x_node.to_dict.assert_called_once_with()

    @mock.patch.object(node_mod.Node, 'load')
    @mock.patch.object(service.EngineService, 'node_find')
    def test_node_get_with_details(self, mock_find, mock_load):
        x_obj = mock.Mock()
        mock_find.return_value = x_obj
        x_node = mock.Mock(physical_id='PHYSICAL_ID')
        x_node.to_dict.return_value = {'foo': 'bar'}
        x_node.get_details.return_value = {'info': 'blahblah'}
        mock_load.return_value = x_node

        result = self.eng.node_get(self.ctx, 'FAKE_NODE', show_details=True)

        self.assertEqual({'foo': 'bar', 'details': {'info': 'blahblah'}},
                         result)
        mock_find.assert_called_once_with(self.ctx, 'FAKE_NODE')
        mock_load.assert_called_once_with(self.ctx, db_node=x_obj)
        x_node.to_dict.assert_called_once_with()
        x_node.get_details.assert_called_once_with(self.ctx)

    @mock.patch.object(service.EngineService, 'node_find')
    def test_node_get_node_not_found(self, mock_find):
        mock_find.side_effect = exc.NodeNotFound(node='Bogus')

        ex = self.assertRaises(rpc.ExpectedException,
                               self.eng.node_get,
                               self.ctx, 'Bogus')

        self.assertEqual(exc.NodeNotFound, ex.exc_info[0])
        self.assertEqual("The node (Bogus) could not be found.",
                         six.text_type(ex.exc_info[1]))
        mock_find.assert_called_once_with(self.ctx, 'Bogus')

    @mock.patch.object(node_mod.Node, 'load')
    @mock.patch.object(service.EngineService, 'node_find')
    def test_node_get_node_not_created(self, mock_find, mock_load):
        x_obj = mock.Mock()
        mock_find.return_value = x_obj
        x_node = mock.Mock(physical_id=None)
        x_node.to_dict.return_value = {'foo': 'bar'}
        mock_load.return_value = x_node
        result = self.eng.node_get(self.ctx, 'FAKE_NODE', show_details=True)

        self.assertEqual({'foo': 'bar'}, result)
        mock_find.assert_called_once_with(self.ctx, 'FAKE_NODE')
        mock_load.assert_called_once_with(self.ctx, db_node=x_obj)
        x_node.to_dict.assert_called_once_with()
        self.assertEqual(0, x_node.get_details.call_count)

    @mock.patch.object(dispatcher, 'start_action')
    @mock.patch.object(action_mod.Action, 'create')
    @mock.patch.object(node_mod.Node, 'load')
    @mock.patch.object(service.EngineService, 'node_find')
    def test_node_update(self, mock_find, mock_load, mock_action, mock_start):
        x_obj = mock.Mock(id='FAKE_NODE_ID', name='NODE1', role='ROLE1',
                          metadata={'KEY': 'VALUE'})
        mock_find.return_value = x_obj
        x_node = mock.Mock()
        x_node.to_dict.return_value = {'foo': 'bar'}
        mock_load.return_value = x_node
        mock_action.return_value = 'ACTION_ID'

        # all properties changed except profile id
        result = self.eng.node_update(self.ctx, 'FAKE_NODE', name='NODE2',
                                      role='NEW_ROLE', metadata={'KEY': 'V1'})

        self.assertEqual({'foo': 'bar', 'action': 'ACTION_ID'}, result)
        mock_find.assert_called_once_with(self.ctx, 'FAKE_NODE')
        mock_action.assert_called_once_with(
            self.ctx, 'FAKE_NODE_ID', consts.NODE_UPDATE,
            name='node_update_FAKE_NOD',
            cause=action_mod.CAUSE_RPC,
            status=action_mod.Action.READY,
            inputs={
                'name': 'NODE2',
                'role': 'NEW_ROLE',
                'metadata': {
                    'KEY': 'V1',
                }
            })
        mock_start.assert_called_once_with()
        mock_load.assert_called_once_with(self.ctx, db_node=x_obj)

    @mock.patch.object(dispatcher, 'start_action')
    @mock.patch.object(action_mod.Action, 'create')
    @mock.patch.object(service.EngineService, 'profile_find')
    @mock.patch.object(node_mod.Node, 'load')
    @mock.patch.object(service.EngineService, 'node_find')
    def test_node_update_new_profile(self, mock_find, mock_load, mock_profile,
                                     mock_action, mock_start):
        x_obj = mock.Mock(id='FAKE_NODE_ID', role='ROLE1',
                          metadata={'KEY': 'VALUE'},
                          profile_id='OLD_PROFILE_ID')
        x_obj.name = 'NODE1'
        mock_find.return_value = x_obj
        # Same profile type
        mock_profile.side_effect = [
            mock.Mock(id='NEW_PROFILE_ID', type='PROFILE_TYPE'),
            mock.Mock(id='OLD_PROFILE_ID', type='PROFILE_TYPE'),
        ]
        x_node = mock.Mock()
        x_node.to_dict.return_value = {'foo': 'bar'}
        mock_load.return_value = x_node
        mock_action.return_value = 'ACTION_ID'

        # all properties are filtered out except for profile_id
        result = self.eng.node_update(self.ctx, 'FAKE_NODE', name='NODE1',
                                      role='ROLE1', metadata={'KEY': 'VALUE'},
                                      profile_id='NEW_PROFILE')

        self.assertEqual({'foo': 'bar', 'action': 'ACTION_ID'}, result)
        mock_find.assert_called_once_with(self.ctx, 'FAKE_NODE')
        mock_profile.assert_has_calls([
            mock.call(self.ctx, 'NEW_PROFILE'),
            mock.call(self.ctx, 'OLD_PROFILE_ID'),
        ])
        mock_action.assert_called_once_with(
            self.ctx, 'FAKE_NODE_ID', consts.NODE_UPDATE,
            name='node_update_FAKE_NOD',
            cause=action_mod.CAUSE_RPC,
            status=action_mod.Action.READY,
            inputs={
                'new_profile_id': 'NEW_PROFILE_ID',
            })
        mock_start.assert_called_once_with()
        mock_load.assert_called_once_with(self.ctx, db_node=x_obj)

    @mock.patch.object(service.EngineService, 'node_find')
    def test_node_update_node_not_found(self, mock_find):
        mock_find.side_effect = exc.NodeNotFound(node='Bogus')

        ex = self.assertRaises(rpc.ExpectedException,
                               self.eng.node_update, self.ctx, 'Bogus')

        self.assertEqual(exc.NodeNotFound, ex.exc_info[0])
        self.assertEqual('The node (Bogus) could not be found.',
                         six.text_type(ex.exc_info[1]))
        mock_find.assert_called_once_with(self.ctx, 'Bogus')

    @mock.patch.object(service.EngineService, 'profile_find')
    @mock.patch.object(service.EngineService, 'node_find')
    def test_node_update_profile_not_found(self, mock_find, mock_profile):
        mock_find.return_value = mock.Mock()
        mock_profile.side_effect = exc.ProfileNotFound(profile='Bogus')

        ex = self.assertRaises(rpc.ExpectedException,
                               self.eng.node_update,
                               self.ctx, 'FAKE_NODE', profile_id='Bogus')

        self.assertEqual(exc.BadRequest, ex.exc_info[0])
        self.assertEqual('The request is malformed: The specified profile '
                         '(Bogus) is not found.',
                         six.text_type(ex.exc_info[1]))
        mock_find.assert_called_once_with(self.ctx, 'FAKE_NODE')
        mock_profile.assert_called_once_with(self.ctx, 'Bogus')

    @mock.patch.object(service.EngineService, 'profile_find')
    @mock.patch.object(service.EngineService, 'node_find')
    def test_node_update_diff_profile_type(self, mock_find, mock_profile):
        mock_find.return_value = mock.Mock(profile_id='OLD_PROFILE_ID')
        mock_profile.side_effect = [
            mock.Mock(id='NEW_PROFILE_ID', type='NEW_PROFILE_TYPE'),
            mock.Mock(id='OLD_PROFILE_ID', type='OLD_PROFILE_TYPE'),
        ]

        ex = self.assertRaises(rpc.ExpectedException,
                               self.eng.node_update,
                               self.ctx, 'FAKE_NODE',
                               profile_id='NEW_PROFILE')

        self.assertEqual(exc.ProfileTypeNotMatch, ex.exc_info[0])
        self.assertEqual('Cannot update a node to a different profile type, '
                         'operation aborted.',
                         six.text_type(ex.exc_info[1]))
        mock_find.assert_called_once_with(self.ctx, 'FAKE_NODE')
        mock_profile.assert_has_calls([
            mock.call(self.ctx, 'NEW_PROFILE'),
            mock.call(self.ctx, 'OLD_PROFILE_ID'),
        ])

    @mock.patch.object(service.EngineService, 'node_find')
    def test_node_update_no_property_for_update(self, mock_find):
        x_obj = mock.Mock(id='FAKE_NODE_ID', name='NODE1', role='ROLE1',
                          metadata={'KEY': 'VALUE'})
        mock_find.return_value = x_obj

        # no property has been specified for update
        ex = self.assertRaises(rpc.ExpectedException,
                               self.eng.node_update,
                               self.ctx, 'FAKE_NODE')

        self.assertEqual(exc.BadRequest, ex.exc_info[0])
        self.assertEqual('The request is malformed: No property needs an '
                         'update.',
                         six.text_type(ex.exc_info[1]))
        mock_find.assert_called_once_with(self.ctx, 'FAKE_NODE')

    @mock.patch.object(dispatcher, 'start_action')
    @mock.patch.object(action_mod.Action, 'create')
    @mock.patch.object(service.EngineService, 'node_find')
    def test_node_delete(self, mock_find, mock_action, mock_start):
        mock_find.return_value = mock.Mock(id='12345678AB')
        mock_action.return_value = 'ACTION_ID'

        result = self.eng.node_delete(self.ctx, 'FAKE_NODE')

        self.assertEqual({'action': 'ACTION_ID'}, result)
        mock_find.assert_called_once_with(self.ctx, 'FAKE_NODE')
        mock_action.assert_called_once_with(
            self.ctx, '12345678AB', consts.NODE_DELETE,
            name='node_delete_12345678',
            cause=action_mod.CAUSE_RPC,
            status=action_mod.Action.READY)
        mock_start.assert_called_once_with()

    @mock.patch.object(service.EngineService, 'node_find')
    def test_node_delete_node_not_found(self, mock_find):
        mock_find.side_effect = exc.NodeNotFound(node='Bogus')

        ex = self.assertRaises(rpc.ExpectedException,
                               self.eng.node_delete, self.ctx, 'Bogus')

        self.assertEqual(exc.NodeNotFound, ex.exc_info[0])
        self.assertEqual('The node (Bogus) could not be found.',
                         six.text_type(ex.exc_info[1]))
        mock_find.assert_called_once_with(self.ctx, 'Bogus')

    @mock.patch.object(dispatcher, 'start_action')
    @mock.patch.object(action_mod.Action, 'create')
    @mock.patch.object(service.EngineService, 'node_find')
    def test_node_check(self, mock_find, mock_action, mock_start):
        mock_find.return_value = mock.Mock(id='12345678AB')
        mock_action.return_value = 'ACTION_ID'

        params = {}
        result = self.eng.node_check(self.ctx, 'FAKE_NODE', params)

        self.assertEqual({'action': 'ACTION_ID'}, result)
        mock_find.assert_called_once_with(self.ctx, 'FAKE_NODE')
        mock_action.assert_called_once_with(
            self.ctx, '12345678AB', consts.NODE_CHECK,
            name='node_check_12345678',
            cause=action_mod.CAUSE_RPC,
            status=action_mod.Action.READY,
            inputs={})
        mock_start.assert_called_once_with()

    @mock.patch.object(service.EngineService, 'node_find')
    def test_node_check_not_found(self, mock_find):
        mock_find.side_effect = exc.NodeNotFound(node='Bogus')

        ex = self.assertRaises(rpc.ExpectedException,
                               self.eng.node_check,
                               self.ctx, 'Bogus')

        self.assertEqual(exc.NodeNotFound, ex.exc_info[0])
        self.assertEqual('The node (Bogus) could not be found.',
                         six.text_type(ex.exc_info[1]))
        mock_find.assert_called_once_with(self.ctx, 'Bogus')

    @mock.patch.object(dispatcher, 'start_action')
    @mock.patch.object(action_mod.Action, 'create')
    @mock.patch.object(service.EngineService, 'node_find')
    def test_node_recover(self, mock_find, mock_action, mock_start):
        mock_find.return_value = mock.Mock(id='12345678AB')
        mock_action.return_value = 'ACTION_ID'
        params = {'foo': 'bar'}

        result = self.eng.node_recover(self.ctx, 'FAKE_NODE', params)

        self.assertEqual({'action': 'ACTION_ID'}, result)
        mock_find.assert_called_once_with(self.ctx, 'FAKE_NODE')
        mock_action.assert_called_once_with(
            self.ctx, '12345678AB', consts.NODE_RECOVER,
            name='node_recover_12345678',
            cause=action_mod.CAUSE_RPC,
            status=action_mod.Action.READY,
            inputs={'foo': 'bar'})
        mock_start.assert_called_once_with()

    @mock.patch.object(service.EngineService, 'node_find')
    def test_node_recover_not_found(self, mock_find):
        mock_find.side_effect = exc.NodeNotFound(node='Bogus')

        ex = self.assertRaises(rpc.ExpectedException,
                               self.eng.node_recover,
                               self.ctx, 'Bogus')

        self.assertEqual(exc.NodeNotFound, ex.exc_info[0])
        self.assertEqual('The node (Bogus) could not be found.',
                         six.text_type(ex.exc_info[1]))
        mock_find.assert_called_once_with(self.ctx, 'Bogus')
