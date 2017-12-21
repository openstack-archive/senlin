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
from senlin.common.i18n import _
from senlin.common import utils as common_utils
from senlin.engine.actions import base as action_mod
from senlin.engine import dispatcher
from senlin.engine import environment
from senlin.engine import node as node_mod
from senlin.engine import service
from senlin.objects import cluster as co
from senlin.objects import node as no
from senlin.objects import profile as po
from senlin.objects.requests import nodes as orno
from senlin.profiles import base as pb
from senlin.tests.unit.common import base
from senlin.tests.unit.common import utils


class NodeTest(base.SenlinTestCase):

    def setUp(self):
        super(NodeTest, self).setUp()
        self.ctx = utils.dummy_context(project='node_test_project')
        self.eng = service.EngineService('host-a', 'topic-a')

    @mock.patch.object(no.Node, 'get_all')
    def test_node_list(self, mock_get):
        obj_1 = mock.Mock()
        obj_1.to_dict.return_value = {'k': 'v1'}
        obj_2 = mock.Mock()
        obj_2.to_dict.return_value = {'k': 'v2'}
        mock_get.return_value = [obj_1, obj_2]

        req = orno.NodeListRequest()
        result = self.eng.node_list(self.ctx, req.obj_to_primitive())

        self.assertEqual([{'k': 'v1'}, {'k': 'v2'}], result)
        mock_get.assert_called_once_with(self.ctx, project_safe=True)

    @mock.patch.object(co.Cluster, 'find')
    @mock.patch.object(no.Node, 'get_all')
    def test_node_list_with_cluster_id(self, mock_get, mock_find):
        obj_1 = mock.Mock()
        obj_1.to_dict.return_value = {'k': 'v1'}
        obj_2 = mock.Mock()
        obj_2.to_dict.return_value = {'k': 'v2'}
        mock_get.return_value = [obj_1, obj_2]
        mock_find.return_value = mock.Mock(id='CLUSTER_ID')

        req = orno.NodeListRequest(cluster_id='MY_CLUSTER_NAME',
                                   project_safe=True)
        result = self.eng.node_list(self.ctx, req.obj_to_primitive())

        self.assertEqual([{'k': 'v1'}, {'k': 'v2'}], result)
        mock_find.assert_called_once_with(self.ctx, 'MY_CLUSTER_NAME')
        mock_get.assert_called_once_with(self.ctx, cluster_id='CLUSTER_ID',
                                         project_safe=True)

    @mock.patch.object(no.Node, 'get_all')
    def test_node_list_with_params(self, mock_get):
        obj_1 = mock.Mock()
        obj_1.to_dict.return_value = {'k': 'v1'}
        obj_2 = mock.Mock()
        obj_2.to_dict.return_value = {'k': 'v2'}
        mock_get.return_value = [obj_1, obj_2]

        MARKER_UUID = '2fd5b45f-bae4-4cdb-b283-a71e9f9805c7'
        req = orno.NodeListRequest(status=['ACTIVE'], sort='status',
                                   limit=123, marker=MARKER_UUID,
                                   project_safe=True)
        result = self.eng.node_list(self.ctx, req.obj_to_primitive())

        self.assertEqual([{'k': 'v1'}, {'k': 'v2'}], result)
        mock_get.assert_called_once_with(self.ctx, sort='status', limit=123,
                                         marker=MARKER_UUID, project_safe=True,
                                         filters={'status': ['ACTIVE']})

    @mock.patch.object(co.Cluster, 'find')
    def test_node_list_cluster_not_found(self, mock_find):
        mock_find.side_effect = exc.ResourceNotFound(type='cluster',
                                                     id='BOGUS')

        req = orno.NodeListRequest(cluster_id='BOGUS', project_safe=True)

        ex = self.assertRaises(rpc.ExpectedException,
                               self.eng.node_list,
                               self.ctx, req.obj_to_primitive())

        self.assertEqual(exc.BadRequest, ex.exc_info[0])
        self.assertEqual('Cannot find the given cluster: BOGUS.',
                         six.text_type(ex.exc_info[1]))
        mock_find.assert_called_once_with(self.ctx, 'BOGUS')

    @mock.patch.object(no.Node, 'get_all')
    def test_node_list_with_project_safe(self, mock_get):
        mock_get.return_value = []

        req = orno.NodeListRequest(project_safe=True)
        result = self.eng.node_list(self.ctx, req.obj_to_primitive())
        self.assertEqual([], result)
        mock_get.assert_called_once_with(self.ctx, project_safe=True)
        mock_get.reset_mock()

        req = orno.NodeListRequest(project_safe=False)
        ex = self.assertRaises(rpc.ExpectedException,
                               self.eng.node_list,
                               self.ctx, req.obj_to_primitive())
        self.assertEqual(exc.Forbidden, ex.exc_info[0])

        self.ctx.is_admin = True
        req = orno.NodeListRequest(project_safe=False)
        result = self.eng.node_list(self.ctx, req.obj_to_primitive())
        self.assertEqual([], result)
        mock_get.assert_called_once_with(self.ctx, project_safe=False)
        mock_get.reset_mock()

    @mock.patch.object(no.Node, 'get_all')
    def test_node_list_empty(self, mock_get):
        mock_get.return_value = []

        req = orno.NodeListRequest()
        result = self.eng.node_list(self.ctx, req.obj_to_primitive())

        self.assertEqual([], result)
        mock_get.assert_called_once_with(self.ctx, project_safe=True)

    @mock.patch.object(action_mod.Action, 'create')
    @mock.patch.object(no.Node, 'create')
    @mock.patch.object(po.Profile, 'find')
    @mock.patch.object(dispatcher, 'start_action')
    def test_node_create(self, notify, mock_profile, mock_node, mock_action):
        mock_profile.return_value = mock.Mock(id='PROFILE_ID')
        x_node = mock.Mock(id='NODE_ID')
        x_node.to_dict.return_value = {'foo': 'bar'}
        mock_node.return_value = x_node
        mock_action.return_value = 'ACTION_ID'
        req = orno.NodeCreateRequestBody(name='NODE1',
                                         profile_id='PROFILE_NAME')

        result = self.eng.node_create(self.ctx, req.obj_to_primitive())

        self.assertEqual({'foo': 'bar', 'action': 'ACTION_ID'}, result)
        mock_profile.assert_called_once_with(self.ctx, 'PROFILE_NAME')
        mock_node.assert_called_once_with(
            self.ctx,
            {
                'name': 'NODE1',
                'profile_id': 'PROFILE_ID',
                'cluster_id': '',
                'index': -1,
                'role': '',
                'metadata': {},
                'user': self.ctx.user_id,
                'project': self.ctx.project_id,
                'domain': self.ctx.domain_id,
                'data': {},
                'init_at': mock.ANY,
                'dependents': {},
                'physical_id': None,
                'status': 'INIT',
                'status_reason': 'Initializing',
            })
        mock_action.assert_called_once_with(
            self.ctx, 'NODE_ID', consts.NODE_CREATE,
            name='node_create_NODE_ID',
            cause=consts.CAUSE_RPC,
            status=action_mod.Action.READY)
        notify.assert_called_once_with()

    @mock.patch.object(common_utils, 'format_node_name')
    @mock.patch.object(action_mod.Action, 'create')
    @mock.patch.object(no.Node, 'create')
    @mock.patch.object(co.Cluster, 'get_next_index')
    @mock.patch.object(co.Cluster, 'find')
    @mock.patch.object(po.Profile, 'find')
    @mock.patch.object(dispatcher, 'start_action')
    def test_node_create_same_profile(self, notify, mock_profile,
                                      mock_cluster, mock_index,
                                      mock_node, mock_action,
                                      mock_node_name):
        mock_profile.return_value = mock.Mock(id='PROFILE_ID',
                                              type='PROFILE_TYPE')
        x_cluster = mock.Mock(id='CLUSTER_ID', profile_id='PROFILE_ID',
                              config={})
        mock_cluster.return_value = x_cluster
        mock_index.return_value = 12345
        x_node = mock.Mock(id='NODE_ID')
        x_node.to_dict.return_value = {'foo': 'bar'}
        mock_node.return_value = x_node
        mock_action.return_value = 'ACTION_ID'
        mock_node_name.return_value = "GENERATED_NAME"
        req = orno.NodeCreateRequestBody(name='NODE1',
                                         profile_id='PROFILE_NAME',
                                         cluster_id='FAKE_CLUSTER')

        result = self.eng.node_create(self.ctx, req.obj_to_primitive())

        self.assertEqual({'foo': 'bar', 'action': 'ACTION_ID'}, result)
        mock_cluster.assert_called_once_with(self.ctx, 'FAKE_CLUSTER')
        mock_profile.assert_called_once_with(self.ctx, 'PROFILE_NAME')
        mock_index.assert_called_once_with(self.ctx, 'CLUSTER_ID')
        mock_node.assert_called_once_with(
            self.ctx,
            {
                'name': 'GENERATED_NAME',
                'profile_id': 'PROFILE_ID',
                'cluster_id': 'CLUSTER_ID',
                'index': 12345,
                'role': '',
                'metadata': {},
                'user': self.ctx.user_id,
                'project': self.ctx.project_id,
                'domain': self.ctx.domain_id,
                'data': {},
                'init_at': mock.ANY,
                'dependents': {},
                'physical_id': None,
                'status': 'INIT',
                'status_reason': 'Initializing',
            })
        mock_action.assert_called_once_with(
            self.ctx, 'NODE_ID', consts.NODE_CREATE,
            name='node_create_NODE_ID',
            cause=consts.CAUSE_RPC,
            status=action_mod.Action.READY)
        notify.assert_called_once_with()

    @mock.patch.object(common_utils, "format_node_name")
    @mock.patch.object(action_mod.Action, 'create')
    @mock.patch.object(no.Node, 'create')
    @mock.patch.object(co.Cluster, 'get_next_index')
    @mock.patch.object(co.Cluster, 'find')
    @mock.patch.object(po.Profile, 'find')
    @mock.patch.object(dispatcher, 'start_action')
    def test_node_create_same_profile_type(self, notify, mock_profile,
                                           mock_cluster, mock_index,
                                           mock_node, mock_action,
                                           mock_node_name):
        mock_profile.side_effect = [
            mock.Mock(id='NODE_PROFILE_ID', type='PROFILE_TYPE'),
            mock.Mock(id='CLUSTER_PROFILE_ID', type='PROFILE_TYPE'),
        ]
        x_cluster = mock.Mock(id='CLUSTER_ID', profile_id='CLUSTER_PROFILE_ID',
                              config={})
        mock_cluster.return_value = x_cluster
        mock_index.return_value = 12345
        x_node = mock.Mock(id='NODE_ID')
        x_node.to_dict.return_value = {'foo': 'bar'}
        mock_node.return_value = x_node
        mock_action.return_value = 'ACTION_ID'
        mock_node_name.return_value = 'GENERATED_NAME'
        req = orno.NodeCreateRequestBody(name='NODE1',
                                         profile_id='PROFILE_NAME',
                                         cluster_id='FAKE_CLUSTER')

        result = self.eng.node_create(self.ctx, req.obj_to_primitive())

        self.assertEqual({'foo': 'bar', 'action': 'ACTION_ID'}, result)
        mock_cluster.assert_called_once_with(self.ctx, 'FAKE_CLUSTER')
        mock_profile.assert_has_calls([
            mock.call(self.ctx, 'PROFILE_NAME'),  # for node
            mock.call(self.ctx, 'CLUSTER_PROFILE_ID'),  # for cluster
        ])
        mock_index.assert_called_once_with(self.ctx, 'CLUSTER_ID')
        mock_node.assert_called_once_with(
            self.ctx,
            {
                'name': 'GENERATED_NAME',
                'profile_id': 'NODE_PROFILE_ID',
                'cluster_id': 'CLUSTER_ID',
                'physical_id': None,
                'index': 12345,
                'role': '',
                'metadata': {},
                'status': 'INIT',
                'status_reason': 'Initializing',
                'user': self.ctx.user_id,
                'project': self.ctx.project_id,
                'domain': self.ctx.domain_id,
                'data': {},
                'dependents': {},
                'init_at': mock.ANY,
            })
        mock_action.assert_called_once_with(
            self.ctx, 'NODE_ID', consts.NODE_CREATE,
            name='node_create_NODE_ID',
            cause=consts.CAUSE_RPC,
            status=action_mod.Action.READY)
        notify.assert_called_once_with()

    @mock.patch.object(po.Profile, 'find')
    @mock.patch.object(no.Node, 'get_by_name')
    def test_node_create_name_conflict(self, mock_find, mock_get):
        cfg.CONF.set_override('name_unique', True)
        mock_get.return_value = mock.Mock()
        req = orno.NodeCreateRequestBody(name='NODE1',
                                         profile_id='PROFILE_NAME')

        ex = self.assertRaises(rpc.ExpectedException,
                               self.eng.node_create,
                               self.ctx, req.obj_to_primitive())

        self.assertEqual(exc.BadRequest, ex.exc_info[0])
        self.assertEqual(_("The node named (NODE1) already exists."),
                         six.text_type(ex.exc_info[1]))

    @mock.patch.object(po.Profile, 'find')
    def test_node_create_profile_not_found(self, mock_profile):
        mock_profile.side_effect = exc.ResourceNotFound(type='profile',
                                                        id='Bogus')
        req = orno.NodeCreateRequestBody(name='NODE1',
                                         profile_id='Bogus')

        ex = self.assertRaises(rpc.ExpectedException,
                               self.eng.node_create,
                               self.ctx, req.obj_to_primitive())
        self.assertEqual(exc.BadRequest, ex.exc_info[0])
        self.assertEqual("The specified profile 'Bogus' could not be "
                         "found.", six.text_type(ex.exc_info[1]))
        mock_profile.assert_called_once_with(self.ctx, 'Bogus')

    @mock.patch.object(co.Cluster, 'find')
    @mock.patch.object(po.Profile, 'find')
    def test_node_create_cluster_not_found(self, mock_profile, mock_cluster):
        mock_cluster.side_effect = exc.ResourceNotFound(type='cluster',
                                                        id='Bogus')
        req = orno.NodeCreateRequestBody(name='NODE1',
                                         profile_id='PROFILE_NAME',
                                         cluster_id='Bogus')

        ex = self.assertRaises(rpc.ExpectedException,
                               self.eng.node_create,
                               self.ctx, req.obj_to_primitive())

        self.assertEqual(exc.BadRequest, ex.exc_info[0])
        self.assertEqual("The specified cluster 'Bogus' could not be found.",
                         six.text_type(ex.exc_info[1]))
        mock_cluster.assert_called_once_with(self.ctx, 'Bogus')

    @mock.patch.object(co.Cluster, 'find')
    @mock.patch.object(po.Profile, 'find')
    def test_node_create_profile_type_not_match(self, mock_profile,
                                                mock_cluster):
        mock_profile.side_effect = [
            mock.Mock(id='NODE_PROFILE_ID', type='TYPE-A'),
            mock.Mock(id='CLUSTER_PROFILE_ID', type='TYPE-B'),
        ]
        mock_cluster.return_value = mock.Mock(id='CLUSTER_ID',
                                              profile_id='CLUSTER_PROFILE_ID')
        req = orno.NodeCreateRequestBody(name='NODE1',
                                         profile_id='NODE_PROFILE',
                                         cluster_id='FAKE_CLUSTER')

        ex = self.assertRaises(rpc.ExpectedException,
                               self.eng.node_create,
                               self.ctx, req.obj_to_primitive())

        self.assertEqual(exc.BadRequest, ex.exc_info[0])
        self.assertEqual("Node and cluster have different profile "
                         "type, operation aborted.",
                         six.text_type(ex.exc_info[1]))
        mock_profile.assert_has_calls([
            mock.call(self.ctx, 'NODE_PROFILE'),
            mock.call(self.ctx, 'CLUSTER_PROFILE_ID'),
        ])
        mock_cluster.assert_called_once_with(self.ctx, 'FAKE_CLUSTER')

    @mock.patch.object(no.Node, 'find')
    def test_node_get(self, mock_find):
        x_obj = mock.Mock(physical_id='PHYSICAL_ID')
        x_obj.to_dict.return_value = {'foo': 'bar'}
        mock_find.return_value = x_obj
        req = orno.NodeGetRequest(identity='NODE1', show_details=False)

        result = self.eng.node_get(self.ctx, req.obj_to_primitive())

        self.assertEqual({'foo': 'bar'}, result)
        mock_find.assert_called_once_with(self.ctx, 'NODE1')
        x_obj.to_dict.assert_called_once_with()

    @mock.patch.object(node_mod.Node, 'load')
    @mock.patch.object(no.Node, 'find')
    def test_node_get_with_details(self, mock_find, mock_load):
        x_obj = mock.Mock(physical_id='PHYSICAL_ID')
        x_obj.to_dict.return_value = {'foo': 'bar'}
        mock_find.return_value = x_obj
        x_node = mock.Mock()
        x_node.get_details.return_value = {'info': 'blahblah'}
        mock_load.return_value = x_node

        req = orno.NodeGetRequest(identity='NODE1', show_details=True)
        result = self.eng.node_get(self.ctx, req.obj_to_primitive())

        self.assertEqual({'foo': 'bar', 'details': {'info': 'blahblah'}},
                         result)
        mock_find.assert_called_once_with(self.ctx, 'NODE1')
        mock_load.assert_called_once_with(self.ctx, db_node=x_obj)
        x_obj.to_dict.assert_called_once_with()
        x_node.get_details.assert_called_once_with(self.ctx)

    @mock.patch.object(no.Node, 'find')
    def test_node_get_node_not_found(self, mock_find):
        mock_find.side_effect = exc.ResourceNotFound(type='node', id='Bogus')
        req = orno.NodeGetRequest(identity='Bogus', show_details=False)

        ex = self.assertRaises(rpc.ExpectedException,
                               self.eng.node_get,
                               self.ctx, req.obj_to_primitive())

        self.assertEqual(exc.ResourceNotFound, ex.exc_info[0])
        self.assertEqual("The node 'Bogus' could not be found.",
                         six.text_type(ex.exc_info[1]))
        mock_find.assert_called_once_with(self.ctx, 'Bogus')

    @mock.patch.object(no.Node, 'find')
    def test_node_get_no_physical_id(self, mock_find):
        x_obj = mock.Mock(physical_id=None)
        x_obj.to_dict.return_value = {'foo': 'bar'}
        mock_find.return_value = x_obj
        req = orno.NodeGetRequest(identity='NODE1', show_details=True)

        result = self.eng.node_get(self.ctx, req.obj_to_primitive())

        self.assertEqual({'foo': 'bar'}, result)
        mock_find.assert_called_once_with(self.ctx, 'NODE1')
        x_obj.to_dict.assert_called_once_with()

    @mock.patch.object(dispatcher, 'start_action')
    @mock.patch.object(action_mod.Action, 'create')
    @mock.patch.object(no.Node, 'find')
    def test_node_update(self, mock_find, mock_action, mock_start):
        x_obj = mock.Mock(id='FAKE_NODE_ID', name='NODE1', role='ROLE1',
                          metadata={'KEY': 'VALUE'})
        x_obj.to_dict.return_value = {'foo': 'bar'}
        mock_find.return_value = x_obj
        mock_action.return_value = 'ACTION_ID'

        req = orno.NodeUpdateRequest(identity='FAKE_NODE',
                                     name='NODE2',
                                     role='NEW_ROLE',
                                     metadata={'foo1': 'bar1'})

        # all properties changed except profile id
        result = self.eng.node_update(self.ctx, req.obj_to_primitive())

        self.assertEqual({'foo': 'bar', 'action': 'ACTION_ID'}, result)
        mock_find.assert_called_once_with(self.ctx, 'FAKE_NODE')
        mock_action.assert_called_once_with(
            self.ctx, 'FAKE_NODE_ID', consts.NODE_UPDATE,
            name='node_update_FAKE_NOD',
            cause=consts.CAUSE_RPC,
            status=action_mod.Action.READY,
            inputs={
                'name': 'NODE2',
                'role': 'NEW_ROLE',
                'metadata': {
                    'foo1': 'bar1',
                }
            })
        mock_start.assert_called_once_with()

    @mock.patch.object(dispatcher, 'start_action')
    @mock.patch.object(action_mod.Action, 'create')
    @mock.patch.object(po.Profile, 'find')
    @mock.patch.object(no.Node, 'find')
    def test_node_update_new_profile(self, mock_find, mock_profile,
                                     mock_action, mock_start):
        x_obj = mock.Mock(id='FAKE_NODE_ID', role='ROLE1',
                          metadata={'KEY': 'VALUE'},
                          profile_id='OLD_PROFILE_ID')
        x_obj.name = 'NODE1'
        x_obj.to_dict.return_value = {'foo': 'bar'}
        mock_find.return_value = x_obj
        # Same profile type
        mock_profile.side_effect = [
            mock.Mock(id='NEW_PROFILE_ID', type='PROFILE_TYPE'),
            mock.Mock(id='OLD_PROFILE_ID', type='PROFILE_TYPE'),
        ]
        mock_action.return_value = 'ACTION_ID'

        # all properties are filtered out except for profile_id
        req = orno.NodeUpdateRequest(identity='FAKE_NODE',
                                     name='NODE1',
                                     role='ROLE1',
                                     metadata={'KEY': 'VALUE'},
                                     profile_id='NEW_PROFILE')
        result = self.eng.node_update(self.ctx, req.obj_to_primitive())

        self.assertEqual({'foo': 'bar', 'action': 'ACTION_ID'}, result)
        mock_find.assert_called_once_with(self.ctx, 'FAKE_NODE')
        mock_profile.assert_has_calls([
            mock.call(self.ctx, 'NEW_PROFILE'),
            mock.call(self.ctx, 'OLD_PROFILE_ID'),
        ])
        mock_action.assert_called_once_with(
            self.ctx, 'FAKE_NODE_ID', consts.NODE_UPDATE,
            name='node_update_FAKE_NOD',
            cause=consts.CAUSE_RPC,
            status=action_mod.Action.READY,
            inputs={
                'new_profile_id': 'NEW_PROFILE_ID',
            })
        mock_start.assert_called_once_with()

    @mock.patch.object(no.Node, 'find')
    def test_node_update_node_not_found(self, mock_find):
        mock_find.side_effect = exc.ResourceNotFound(type='node', id='Bogus')

        req = orno.NodeUpdateRequest(identity='Bogus')
        ex = self.assertRaises(rpc.ExpectedException,
                               self.eng.node_update, self.ctx,
                               req.obj_to_primitive())

        self.assertEqual(exc.ResourceNotFound, ex.exc_info[0])
        self.assertEqual("The node 'Bogus' could not be found.",
                         six.text_type(ex.exc_info[1]))
        mock_find.assert_called_once_with(self.ctx, 'Bogus')

    @mock.patch.object(po.Profile, 'find')
    @mock.patch.object(no.Node, 'find')
    def test_node_update_profile_not_found(self, mock_find, mock_profile):
        mock_find.return_value = mock.Mock()
        mock_profile.side_effect = exc.ResourceNotFound(type='profile',
                                                        id='Bogus')

        req = orno.NodeUpdateRequest(identity='FAKE_NODE',
                                     profile_id='Bogus')
        ex = self.assertRaises(rpc.ExpectedException,
                               self.eng.node_update,
                               self.ctx, req.obj_to_primitive())

        self.assertEqual(exc.BadRequest, ex.exc_info[0])
        self.assertEqual("The specified profile 'Bogus' could not be "
                         "found.", six.text_type(ex.exc_info[1]))
        mock_find.assert_called_once_with(self.ctx, 'FAKE_NODE')
        mock_profile.assert_called_once_with(self.ctx, 'Bogus')

    @mock.patch.object(po.Profile, 'find')
    @mock.patch.object(no.Node, 'find')
    def test_node_update_diff_profile_type(self, mock_find, mock_profile):
        mock_find.return_value = mock.Mock(profile_id='OLD_PROFILE_ID')
        mock_profile.side_effect = [
            mock.Mock(id='NEW_PROFILE_ID', type='NEW_PROFILE_TYPE'),
            mock.Mock(id='OLD_PROFILE_ID', type='OLD_PROFILE_TYPE'),
        ]

        req = orno.NodeUpdateRequest(identity='FAKE_NODE',
                                     profile_id='NEW_PROFILE')
        ex = self.assertRaises(rpc.ExpectedException,
                               self.eng.node_update,
                               self.ctx, req.obj_to_primitive())

        self.assertEqual(exc.BadRequest, ex.exc_info[0])
        self.assertEqual("Cannot update a node to a different "
                         "profile type, operation aborted.",
                         six.text_type(ex.exc_info[1]))
        mock_find.assert_called_once_with(self.ctx, 'FAKE_NODE')
        mock_profile.assert_has_calls([
            mock.call(self.ctx, 'NEW_PROFILE'),
            mock.call(self.ctx, 'OLD_PROFILE_ID'),
        ])

    @mock.patch.object(po.Profile, 'find')
    @mock.patch.object(no.Node, 'find')
    def test_node_update_dumplicated_profile(self, mock_find, mock_profile):
        mock_find.return_value = mock.Mock(profile_id='OLD_PROFILE_ID')
        mock_profile.side_effect = [
            mock.Mock(id='OLD_PROFILE_ID', type='PROFILE_TYPE'),
            mock.Mock(id='OLD_PROFILE_ID', type='PROFILE_TYPE'),
        ]

        req = orno.NodeUpdateRequest(identity='FAKE_NODE',
                                     profile_id='OLD_PROFILE_ID')
        ex = self.assertRaises(rpc.ExpectedException,
                               self.eng.node_update,
                               self.ctx, req.obj_to_primitive())

        self.assertEqual(exc.BadRequest, ex.exc_info[0])
        self.assertEqual("No property needs an update.",
                         six.text_type(ex.exc_info[1]))
        mock_find.assert_called_once_with(self.ctx, 'FAKE_NODE')
        mock_profile.assert_has_calls([
            mock.call(self.ctx, 'OLD_PROFILE_ID'),
            mock.call(self.ctx, 'OLD_PROFILE_ID'),
        ])

    @mock.patch.object(no.Node, 'find')
    def test_node_update_no_property_for_update(self, mock_find):
        x_obj = mock.Mock(id='FAKE_NODE_ID', name='NODE1', role='ROLE1',
                          metadata={'KEY': 'VALUE'})
        mock_find.return_value = x_obj

        # no property has been specified for update
        req = orno.NodeUpdateRequest(identity='FAKE_NODE')
        ex = self.assertRaises(rpc.ExpectedException,
                               self.eng.node_update,
                               self.ctx, req.obj_to_primitive())

        self.assertEqual(exc.BadRequest, ex.exc_info[0])
        self.assertEqual("No property needs an update.",
                         six.text_type(ex.exc_info[1]))
        mock_find.assert_called_once_with(self.ctx, 'FAKE_NODE')

    @mock.patch.object(dispatcher, 'start_action')
    @mock.patch.object(action_mod.Action, 'create')
    @mock.patch.object(no.Node, 'find')
    def test_node_delete(self, mock_find, mock_action, mock_start):
        mock_find.return_value = mock.Mock(id='12345678AB', status='ACTIVE',
                                           dependents={})
        mock_action.return_value = 'ACTION_ID'

        req = orno.NodeDeleteRequest(identity='FAKE_NODE', force=False)
        result = self.eng.node_delete(self.ctx, req.obj_to_primitive())

        self.assertEqual({'action': 'ACTION_ID'}, result)
        mock_find.assert_called_once_with(self.ctx, 'FAKE_NODE')
        mock_action.assert_called_once_with(
            self.ctx, '12345678AB', consts.NODE_DELETE,
            name='node_delete_12345678',
            cause=consts.CAUSE_RPC,
            status=action_mod.Action.READY)
        mock_start.assert_called_once_with()

    @mock.patch.object(no.Node, 'find')
    def test_node_delete_node_not_found(self, mock_find):
        mock_find.side_effect = exc.ResourceNotFound(type='node', id='Bogus')

        req = orno.NodeDeleteRequest(identity='Bogus', force=False)
        ex = self.assertRaises(rpc.ExpectedException,
                               self.eng.node_delete, self.ctx,
                               req.obj_to_primitive())

        self.assertEqual(exc.ResourceNotFound, ex.exc_info[0])
        self.assertEqual("The node 'Bogus' could not be found.",
                         six.text_type(ex.exc_info[1]))
        mock_find.assert_called_once_with(self.ctx, 'Bogus')

    @mock.patch.object(no.Node, 'find')
    def test_node_delete_improper_status(self, mock_find):
        for bad_status in [consts.NS_CREATING, consts.NS_UPDATING,
                           consts.NS_DELETING, consts.NS_RECOVERING]:
            fake_node = mock.Mock(id='12345678AB', status=bad_status)
            mock_find.return_value = fake_node
            req = orno.NodeDeleteRequest(identity='BUSY', force=False)
            ex = self.assertRaises(rpc.ExpectedException,
                                   self.eng.node_delete,
                                   self.ctx, req.obj_to_primitive())

            self.assertEqual(exc.ActionInProgress, ex.exc_info[0])
            self.assertEqual("The node 'BUSY' is in status %s." % bad_status,
                             six.text_type(ex.exc_info[1]))
            # skipping assertion on mock_find

    @mock.patch.object(no.Node, 'find')
    def test_node_delete_have_dependency(self, mock_find):
        dependents = {'nodes': ['NODE1']}
        node = mock.Mock(id='NODE_ID', status='ACTIVE', dependents=dependents)
        mock_find.return_value = node
        req = orno.NodeDeleteRequest(identity='node1', force=False)
        ex = self.assertRaises(rpc.ExpectedException,
                               self.eng.node_delete,
                               self.ctx, req.obj_to_primitive())
        self.assertEqual(exc.ResourceInUse, ex.exc_info[0])
        self.assertEqual("The node 'node1' cannot be deleted: still depended "
                         "by other clusters and/or nodes.",
                         six.text_type(ex.exc_info[1]))

    @mock.patch.object(dispatcher, 'start_action')
    @mock.patch.object(action_mod.Action, 'create')
    @mock.patch.object(no.Node, 'find')
    def test_node_delete_force(self, mock_find, mock_action, mock_start):
        for bad_status in [consts.NS_CREATING, consts.NS_UPDATING,
                           consts.NS_DELETING, consts.NS_RECOVERING]:

            mock_find.return_value = mock.Mock(id='12345678AB',
                                               status=bad_status,
                                               dependents={})
            mock_action.return_value = 'ACTION_ID'

            req = orno.NodeDeleteRequest(identity='FAKE_NODE', force=True)
            result = self.eng.node_delete(self.ctx, req.obj_to_primitive())

            self.assertEqual({'action': 'ACTION_ID'}, result)
            mock_find.assert_called_with(self.ctx, 'FAKE_NODE')
            mock_action.assert_called_with(
                self.ctx, '12345678AB', consts.NODE_DELETE,
                name='node_delete_12345678',
                cause=consts.CAUSE_RPC,
                status=action_mod.Action.READY)
            mock_start.assert_called_with()

    @mock.patch.object(environment.Environment, 'get_profile')
    @mock.patch.object(pb.Profile, 'adopt_node')
    def test__node_adopt_preview(self, mock_adopt, mock_profile):
        class FakeProfile(object):
            pass

        req = mock.Mock(
            identity="FAKE_NODE",
            type="TestProfile-1.0",
            overrides="foo",
            snapshot=True
        )
        mock_adopt.return_value = {'prop': 'value'}
        mock_profile.return_value = FakeProfile

        c, s = self.eng._node_adopt_preview(self.ctx, req)

        req.obj_set_defaults.assert_called_once_with()
        mock_profile.assert_called_once_with("TestProfile-1.0")
        self.assertEqual(FakeProfile, c)
        mock_adopt.assert_called_once_with(
            self.ctx, mock.ANY, 'TestProfile-1.0',
            overrides="foo", snapshot=True)
        fake_node = mock_adopt.call_args[0][1]
        self.assertIsInstance(fake_node, node_mod.Node)
        self.assertEqual('adopt', fake_node.name)
        self.assertEqual('TBD', fake_node.profile_id)
        self.assertEqual('FAKE_NODE', fake_node.physical_id)
        expected = {
            'type': 'TestProfile',
            'version': '1.0',
            'properties': {'prop': 'value'}
        }
        self.assertEqual(expected, s)

    @mock.patch.object(pb.Profile, 'adopt_node')
    def test__node_adopt_preview_bad_type(self, mock_adopt):
        req = mock.Mock(
            identity="FAKE_NODE",
            type="TestProfile-1.0",
            overrides="foo",
            snapshot=True
        )

        ex = self.assertRaises(exc.BadRequest,
                               self.eng._node_adopt_preview,
                               self.ctx, req)

        req.obj_set_defaults.assert_called_once_with()
        self.assertEqual("The profile_type 'TestProfile-1.0' could not be "
                         "found.", six.text_type(ex))

    @mock.patch.object(environment.Environment, 'get_profile')
    @mock.patch.object(pb.Profile, 'adopt_node')
    def test__node_adopt_preview_failed_adopt(self, mock_adopt, mock_profile):
        class FakeProfile(object):
            pass

        req = mock.Mock(
            identity="FAKE_NODE",
            type="TestProfile-1.0",
            overrides="foo",
            snapshot=True
        )
        mock_profile.return_value = FakeProfile
        mock_adopt.return_value = {
            'Error': {'code': 502, 'message': 'something is bad'}
        }

        ex = self.assertRaises(exc.ProfileOperationFailed,
                               self.eng._node_adopt_preview,
                               self.ctx, req)

        req.obj_set_defaults.assert_called_once_with()
        mock_profile.assert_called_once_with("TestProfile-1.0")
        mock_adopt.assert_called_once_with(
            self.ctx, mock.ANY, 'TestProfile-1.0',
            overrides="foo", snapshot=True)

        self.assertEqual('502: something is bad', six.text_type(ex))

    @mock.patch.object(service.EngineService, '_node_adopt_preview')
    def test_node_adopt_preview(self, mock_preview):
        spec = {'foo': 'bar'}
        mock_preview.return_value = mock.Mock(), spec
        req = orno.NodeAdoptPreviewRequest(identity='FAKE_ID',
                                           type='FAKE_TYPE')

        res = self.eng.node_adopt_preview(self.ctx, req.obj_to_primitive())

        self.assertEqual({'node_preview': {'foo': 'bar'}}, res)
        mock_preview.assert_called_once_with(self.ctx, mock.ANY)
        self.assertIsInstance(mock_preview.call_args[0][1],
                              orno.NodeAdoptPreviewRequest)

    @mock.patch.object(service.EngineService, '_node_adopt_preview')
    def test_node_adopt_preview_with_exception(self, mock_preview):
        mock_preview.side_effect = exc.BadRequest(msg="boom")
        req = orno.NodeAdoptPreviewRequest(identity='FAKE_ID',
                                           type='FAKE_TYPE')

        ex = self.assertRaises(rpc.ExpectedException,
                               self.eng.node_adopt_preview,
                               self.ctx, req.obj_to_primitive())

        mock_preview.assert_called_once_with(self.ctx, mock.ANY)
        self.assertIsInstance(mock_preview.call_args[0][1],
                              orno.NodeAdoptPreviewRequest)
        self.assertEqual(exc.BadRequest, ex.exc_info[0])
        self.assertEqual('boom.', six.text_type(ex.exc_info[1]))

    @mock.patch.object(no.Node, 'create')
    @mock.patch.object(service.EngineService, '_node_adopt_preview')
    def test_node_adopt(self, mock_preview, mock_create):
        class FakeProfile(object):
            @classmethod
            def create(cls, ctx, name, spec):
                obj = mock.Mock(spec=spec, id='PROFILE_ID')
                obj.name = name
                return obj

        req = orno.NodeAdoptRequest(identity='FAKE_ID', type='FAKE_TYPE')
        mock_preview.return_value = FakeProfile, {'foo': 'bar'}
        fake_node = mock.Mock()
        fake_node.to_dict = mock.Mock(return_value={'attr': 'value'})
        mock_create.return_value = fake_node

        res = self.eng.node_adopt(self.ctx, req.obj_to_primitive())

        self.assertEqual({'attr': 'value'}, res)
        mock_preview.assert_called_once_with(self.ctx, mock.ANY)
        self.assertIsInstance(mock_preview.call_args[0][1],
                              orno.NodeAdoptRequest)
        attrs = {
            'name': mock.ANY,
            'data': {},
            'dependents': {},
            'profile_id': 'PROFILE_ID',
            'physical_id': 'FAKE_ID',
            'cluster_id': '',
            'index': -1,
            'role': '',
            'metadata': {},
            'status': consts.NS_ACTIVE,
            'status_reason': 'Node adopted successfully',
            'init_at': mock.ANY,
            'created_at': mock.ANY,
            'user': self.ctx.user_id,
            'project': self.ctx.project_id,
            'domain': self.ctx.domain_id
        }
        mock_create.assert_called_once_with(self.ctx, attrs)

    @mock.patch.object(no.Node, 'get_by_name')
    def test_node_adopt_name_not_unique(self, mock_get):
        cfg.CONF.set_override('name_unique', True)
        req = orno.NodeAdoptRequest(
            name='FAKE_NAME', preview=False,
            identity='FAKE_ID', type='FAKE_TYPE')
        mock_get.return_value = mock.Mock()

        ex = self.assertRaises(rpc.ExpectedException,
                               self.eng.node_adopt,
                               self.ctx, req.obj_to_primitive())

        self.assertEqual(exc.BadRequest, ex.exc_info[0])
        self.assertEqual("The node named (FAKE_NAME) already exists.",
                         six.text_type(ex.exc_info[1]))

    @mock.patch.object(no.Node, 'create')
    @mock.patch.object(service.EngineService, '_node_adopt_preview')
    def test_node_adopt_failed_preview(self, mock_preview, mock_create):
        req = orno.NodeAdoptRequest(identity='FAKE_ID', type='FAKE_TYPE')
        mock_preview.side_effect = exc.BadRequest(msg='boom')

        ex = self.assertRaises(rpc.ExpectedException,
                               self.eng.node_adopt,
                               self.ctx, req.obj_to_primitive())

        mock_preview.assert_called_once_with(self.ctx, mock.ANY)
        self.assertIsInstance(mock_preview.call_args[0][1],
                              orno.NodeAdoptRequest)

        self.assertEqual(exc.BadRequest, ex.exc_info[0])
        self.assertEqual("boom.", six.text_type(ex.exc_info[1]))

    @mock.patch.object(dispatcher, 'start_action')
    @mock.patch.object(action_mod.Action, 'create')
    @mock.patch.object(no.Node, 'find')
    def test_node_check(self, mock_find, mock_action, mock_start):
        mock_find.return_value = mock.Mock(id='12345678AB')
        mock_action.return_value = 'ACTION_ID'

        params = {'k1': 'v1'}
        req = orno.NodeCheckRequest(identity='FAKE_NODE', params=params)
        result = self.eng.node_check(self.ctx, req.obj_to_primitive())

        self.assertEqual({'action': 'ACTION_ID'}, result)
        mock_find.assert_called_once_with(self.ctx, 'FAKE_NODE')
        mock_action.assert_called_once_with(
            self.ctx, '12345678AB', consts.NODE_CHECK,
            name='node_check_12345678',
            cause=consts.CAUSE_RPC,
            status=action_mod.Action.READY,
            inputs={'k1': 'v1'})
        mock_start.assert_called_once_with()

    @mock.patch.object(no.Node, 'find')
    def test_node_check_not_found(self, mock_find):
        mock_find.side_effect = exc.ResourceNotFound(type='node', id='Bogus')

        req = orno.NodeCheckRequest(identity='Bogus')
        ex = self.assertRaises(rpc.ExpectedException,
                               self.eng.node_check,
                               self.ctx, req.obj_to_primitive())

        self.assertEqual(exc.ResourceNotFound, ex.exc_info[0])
        self.assertEqual("The node 'Bogus' could not be found.",
                         six.text_type(ex.exc_info[1]))
        mock_find.assert_called_once_with(self.ctx, 'Bogus')

    @mock.patch.object(dispatcher, 'start_action')
    @mock.patch.object(action_mod.Action, 'create')
    @mock.patch.object(no.Node, 'find')
    def test_node_recover(self, mock_find, mock_action, mock_start):
        mock_find.return_value = mock.Mock(id='12345678AB')
        mock_action.return_value = 'ACTION_ID'

        params = {'operation': 'some_action'}
        req = orno.NodeRecoverRequest(identity='FAKE_NODE', params=params)
        result = self.eng.node_recover(self.ctx, req.obj_to_primitive())

        self.assertEqual({'action': 'ACTION_ID'}, result)
        mock_find.assert_called_once_with(self.ctx, 'FAKE_NODE')
        mock_action.assert_called_once_with(
            self.ctx, '12345678AB', consts.NODE_RECOVER,
            name='node_recover_12345678',
            cause=consts.CAUSE_RPC,
            status=action_mod.Action.READY,
            inputs={'operation': [{'name': 'some_action'}]})
        mock_start.assert_called_once_with()

    @mock.patch.object(dispatcher, 'start_action')
    @mock.patch.object(action_mod.Action, 'create')
    @mock.patch.object(no.Node, 'find')
    def test_node_recover_with_check(self, mock_find, mock_action, mock_start):
        mock_find.return_value = mock.Mock(id='12345678AB')
        mock_action.return_value = 'ACTION_ID'

        params = {'check': True, 'operation': 'some_action'}
        req = orno.NodeRecoverRequest(identity='FAKE_NODE', params=params)
        result = self.eng.node_recover(self.ctx, req.obj_to_primitive())

        self.assertEqual({'action': 'ACTION_ID'}, result)
        mock_find.assert_called_once_with(self.ctx, 'FAKE_NODE')
        mock_action.assert_called_once_with(
            self.ctx, '12345678AB', consts.NODE_RECOVER,
            name='node_recover_12345678',
            cause=consts.CAUSE_RPC,
            status=action_mod.Action.READY,
            inputs={'check': True, 'operation': [{'name': 'some_action'}]})
        mock_start.assert_called_once_with()

    @mock.patch.object(no.Node, 'find')
    def test_node_recover_not_found(self, mock_find):
        mock_find.side_effect = exc.ResourceNotFound(type='node', id='Bogus')

        req = orno.NodeRecoverRequest(identity='Bogus')
        ex = self.assertRaises(rpc.ExpectedException,
                               self.eng.node_recover,
                               self.ctx, req.obj_to_primitive())

        self.assertEqual(exc.ResourceNotFound, ex.exc_info[0])
        self.assertEqual("The node 'Bogus' could not be found.",
                         six.text_type(ex.exc_info[1]))
        mock_find.assert_called_once_with(self.ctx, 'Bogus')

    @mock.patch.object(action_mod.Action, 'create')
    @mock.patch.object(no.Node, 'find')
    def test_node_recover_invalid_operation(self, mock_find, mock_action):
        mock_find.return_value = mock.Mock(id='12345678AB')
        mock_action.return_value = 'ACTION_ID'
        params = {'bogus': 'illegal'}
        req = orno.NodeRecoverRequest(identity='FAKE_NODE', params=params)

        ex = self.assertRaises(rpc.ExpectedException,
                               self.eng.node_recover,
                               self.ctx, req.obj_to_primitive())

        self.assertEqual(exc.BadRequest, ex.exc_info[0])
        self.assertEqual("Action parameter ['bogus'] is not recognizable.",
                         six.text_type(ex.exc_info[1]))
        mock_find.assert_called_once_with(self.ctx, 'FAKE_NODE')
        self.assertEqual(0, mock_action.call_count)

    @mock.patch.object(dispatcher, 'start_action')
    @mock.patch.object(action_mod.Action, 'create')
    @mock.patch.object(node_mod.Node, 'load')
    @mock.patch.object(no.Node, 'find')
    def test_node_op(self, mock_find, mock_node, mock_action, mock_start):
        x_db_node = mock.Mock(id='12345678AB')
        mock_find.return_value = x_db_node
        x_schema = mock.Mock()
        x_profile = mock.Mock(OPERATIONS={'dance': x_schema})
        x_node = mock.Mock()
        x_node.rt = {'profile': x_profile}
        mock_node.return_value = x_node
        mock_action.return_value = 'ACTION_ID'
        params = {'style': 'tango'}
        req = orno.NodeOperationRequest(identity='FAKE_NODE',
                                        operation='dance',
                                        params=params)

        result = self.eng.node_op(self.ctx, req.obj_to_primitive())

        self.assertEqual({'action': 'ACTION_ID'}, result)
        mock_find.assert_called_once_with(self.ctx, 'FAKE_NODE')
        mock_node.assert_called_once_with(self.ctx, db_node=x_db_node)
        x_schema.validate.assert_called_once_with({'style': 'tango'})
        mock_action.assert_called_once_with(
            self.ctx, '12345678AB', consts.NODE_OPERATION,
            name='node_dance_12345678',
            cause=consts.CAUSE_RPC,
            status=action_mod.Action.READY,
            inputs={'operation': 'dance', 'params': {'style': 'tango'}})
        mock_start.assert_called_once_with()

    @mock.patch.object(no.Node, 'find')
    def test_node_op_node_not_found(self, mock_find):
        mock_find.side_effect = exc.ResourceNotFound(type='node', id='Bogus')

        req = orno.NodeOperationRequest(identity='Bogus', operation='dance',
                                        params={})
        ex = self.assertRaises(rpc.ExpectedException,
                               self.eng.node_op,
                               self.ctx, req.obj_to_primitive())

        self.assertEqual(exc.ResourceNotFound, ex.exc_info[0])
        self.assertEqual("The node 'Bogus' could not be found.",
                         six.text_type(ex.exc_info[1]))
        mock_find.assert_called_once_with(self.ctx, 'Bogus')

    @mock.patch.object(node_mod.Node, 'load')
    @mock.patch.object(no.Node, 'find')
    def test_node_op_unsupported_operation(self, mock_find, mock_node):
        x_db_node = mock.Mock(id='12345678AB')
        mock_find.return_value = x_db_node
        x_schema = mock.Mock()
        x_profile = mock.Mock(OPERATIONS={'dance': x_schema}, type='cow')
        x_node = mock.Mock()
        x_node.rt = {'profile': x_profile}
        mock_node.return_value = x_node

        req = orno.NodeOperationRequest(identity='node1', operation='swim',
                                        params={})
        ex = self.assertRaises(rpc.ExpectedException,
                               self.eng.node_op,
                               self.ctx, req.obj_to_primitive())

        self.assertEqual(exc.BadRequest, ex.exc_info[0])
        self.assertEqual("The requested operation 'swim' is not "
                         "supported by the profile type 'cow'.",
                         six.text_type(ex.exc_info[1]))
        mock_find.assert_called_once_with(self.ctx, 'node1')
        mock_node.assert_called_once_with(self.ctx, db_node=x_db_node)

    @mock.patch.object(node_mod.Node, 'load')
    @mock.patch.object(no.Node, 'find')
    def test_node_op_bad_parameters(self, mock_find, mock_node):
        x_db_node = mock.Mock(id='12345678AB')
        mock_find.return_value = x_db_node
        x_schema = mock.Mock()
        x_schema.validate.side_effect = exc.ESchema(message='Boom')
        x_profile = mock.Mock(OPERATIONS={'dance': x_schema})
        x_node = mock.Mock()
        x_node.rt = {'profile': x_profile}
        mock_node.return_value = x_node

        req = orno.NodeOperationRequest(identity='node1', operation='dance',
                                        params={'style': 'tango'})
        ex = self.assertRaises(rpc.ExpectedException,
                               self.eng.node_op,
                               self.ctx, req.obj_to_primitive())

        self.assertEqual(exc.BadRequest, ex.exc_info[0])
        self.assertEqual("Boom.", six.text_type(ex.exc_info[1]))
        mock_find.assert_called_once_with(self.ctx, 'node1')
        mock_node.assert_called_once_with(self.ctx, db_node=x_db_node)
        x_schema.validate.assert_called_once_with({'style': 'tango'})
