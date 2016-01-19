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

from senlin.common import exception
from senlin.common.i18n import _
from senlin.engine.actions import base as action_mod
from senlin.engine import dispatcher
from senlin.engine import environment
from senlin.engine import node as node_mod
from senlin.engine import service
from senlin.tests.unit.common import base
from senlin.tests.unit.common import utils
from senlin.tests.unit import fakes


class NodeTest(base.SenlinTestCase):

    def setUp(self):
        super(NodeTest, self).setUp()
        self.ctx = utils.dummy_context(project='node_test_project')
        self.eng = service.EngineService('host-a', 'topic-a')
        self.eng.init_tgm()

        self.eng.dispatcher = mock.Mock()

        env = environment.global_env()
        env.register_profile('TestProfile-1.0', fakes.TestProfile)

        self.spec = {
            'type': 'TestProfile',
            'version': '1.0',
            'properties': {
                'INT': 10,
                'STR': 'string'
            }
        }
        self.profile = self.eng.profile_create(self.ctx, 'p-test', self.spec)

    def _verify_action(self, obj, action, name, target, cause, inputs=None):
        if inputs is None:
            inputs = {}
        self.assertEqual(action, obj['action'])
        self.assertEqual(name, obj['name'])
        self.assertEqual(target, obj['target'])
        self.assertEqual(cause, obj['cause'])
        self.assertEqual(inputs, obj['inputs'])

    @mock.patch.object(dispatcher, 'start_action')
    def test_node_create_default(self, notify):
        node = self.eng.node_create(self.ctx, 'n-1', self.profile['id'])
        self.assertIsNotNone(node)
        self.assertEqual('n-1', node['name'])
        self.assertEqual(-1, node['index'])
        self.assertEqual(self.profile['id'], node['profile_id'])
        self.assertEqual('', node['cluster_id'])
        self.assertIsNone(node['role'])
        self.assertEqual({}, node['metadata'])

    def test_node_create_profile_not_found(self):
        ex = self.assertRaises(rpc.ExpectedException,
                               self.eng.node_create,
                               self.ctx, 'n-1', 'Bogus')
        self.assertEqual(exception.SenlinBadRequest, ex.exc_info[0])
        self.assertEqual("The request is malformed: The specified profile "
                         "(Bogus) is not found.",
                         six.text_type(ex.exc_info[1]))

    @mock.patch.object(dispatcher, 'start_action')
    def test_node_create_with_role_and_metadata(self, notify):
        node = self.eng.node_create(self.ctx, 'n-1', self.profile['id'],
                                    role='master', metadata={'k': 'v'})

        self.assertIsNotNone(node)
        self.assertEqual('n-1', node['name'])
        self.assertEqual('master', node['role'])
        self.assertEqual({'k': 'v'}, node['metadata'])

    @mock.patch.object(dispatcher, 'start_action')
    def test_node_create_with_profile_name_or_short_id(self, notify):
        node = self.eng.node_create(self.ctx, 'n-1', self.profile['id'][:8])
        self.assertIsNotNone(node)
        self.assertEqual(self.profile['id'], node['profile_id'])

        node = self.eng.node_create(self.ctx, 'n-2', self.profile['name'])
        self.assertIsNotNone(node)
        self.assertEqual(self.profile['id'], node['profile_id'])

    @mock.patch.object(dispatcher, 'start_action')
    def test_node_create_already_exists(self, notify):
        cfg.CONF.set_override('name_unique', True, enforce_type=True)
        node = self.eng.node_create(self.ctx, 'n-1', self.profile['id'])
        self.assertIsNotNone(node)

        ex = self.assertRaises(rpc.ExpectedException,
                               self.eng.node_create,
                               self.ctx, 'n-1', self.profile['id'])

        self.assertEqual(exception.SenlinBadRequest, ex.exc_info[0])
        self.assertEqual(_("The request is malformed: The node (n-1) "
                           "already exists."),
                         six.text_type(ex.exc_info[1]))

    def test_node_create_with_cluster_id_not_found(self):
        ex = self.assertRaises(rpc.ExpectedException,
                               self.eng.node_create,
                               self.ctx, 'n-1', self.profile['id'],
                               cluster_id='Bogus')

        self.assertEqual(exception.SenlinBadRequest, ex.exc_info[0])
        self.assertEqual("The request is malformed: The specified cluster "
                         "(Bogus) is not found.",
                         six.text_type(ex.exc_info[1]))

    @mock.patch.object(dispatcher, 'start_action')
    def test_node_create_project_not_match(self, notify):
        cluster = self.eng.cluster_create(self.ctx, 'c-1', 0,
                                          self.profile['id'])

        ctx_node = utils.dummy_context(project='a-different-project')
        profile_node = self.eng.profile_create(ctx_node, 'p-test', self.spec)
        ex = self.assertRaises(rpc.ExpectedException,
                               self.eng.node_create,
                               ctx_node, 'n-1', profile_node['id'],
                               cluster_id=cluster['id'])

        self.assertEqual(exception.SenlinBadRequest, ex.exc_info[0])
        self.assertEqual("The request is malformed: The specified cluster "
                         "(%s) is not found."
                         "" % cluster['id'],
                         six.text_type(ex.exc_info[1]))

    @mock.patch.object(dispatcher, 'start_action')
    def test_node_create_profile_type_not_match(self, notify):
        env = environment.global_env()
        env.register_profile('SecondProfile-1.0', fakes.TestProfile)
        new_spec = {
            'type': 'SecondProfile',
            'version': '1.0',
            'properties': {'INT': 20, 'STR': 'string'}
        }
        cluster_profile = self.eng.profile_create(self.ctx, 'cp', new_spec)

        cluster = self.eng.cluster_create(self.ctx, 'c-1', 0,
                                          cluster_profile['id'])

        ex = self.assertRaises(rpc.ExpectedException,
                               self.eng.node_create,
                               self.ctx, 'n-1', self.profile['id'],
                               cluster_id=cluster['id'])

        self.assertEqual(exception.ProfileTypeNotMatch, ex.exc_info[0])
        self.assertEqual("Node and cluster have different profile type, "
                         "operation aborted.",
                         six.text_type(ex.exc_info[1]))

    @mock.patch.object(dispatcher, 'start_action')
    def test_node_get(self, notify):
        node = self.eng.node_create(self.ctx, 'n-1', self.profile['id'])

        for identity in [node['id'], node['id'][:6], 'n-1']:
            result = self.eng.node_get(self.ctx, identity)
            self.assertIsInstance(result, dict)
            self.assertEqual(node['id'], result['id'])

        ex = self.assertRaises(rpc.ExpectedException,
                               self.eng.node_get, self.ctx, 'Bogus')
        self.assertEqual(exception.NodeNotFound, ex.exc_info[0])

    @mock.patch.object(dispatcher, 'start_action')
    def test_node_list(self, notify):
        node1 = self.eng.node_create(self.ctx, 'n1', self.profile['id'])
        node2 = self.eng.node_create(self.ctx, 'n2', self.profile['id'])
        result = self.eng.node_list(self.ctx)

        self.assertIsInstance(result, list)
        names = [n['name'] for n in result]
        ids = [n['id'] for n in result]
        self.assertEqual(node1['name'], names[0])
        self.assertEqual(node2['name'], names[1])
        self.assertEqual(node1['id'], ids[0])
        self.assertEqual(node2['id'], ids[1])

    @mock.patch.object(dispatcher, 'start_action')
    def test_node_list_with_limit_marker(self, notify):
        node1 = self.eng.node_create(self.ctx, 'n1', self.profile['id'])
        node2 = self.eng.node_create(self.ctx, 'n2', self.profile['id'])
        result = self.eng.node_list(self.ctx, limit=0)

        self.assertEqual(0, len(result))
        result = self.eng.node_list(self.ctx, limit=1)
        self.assertEqual(1, len(result))
        result = self.eng.node_list(self.ctx, limit=2)
        self.assertEqual(2, len(result))
        result = self.eng.node_list(self.ctx, limit=3)
        self.assertEqual(2, len(result))

        result = self.eng.node_list(self.ctx, marker=node1['id'])
        self.assertEqual(1, len(result))
        result = self.eng.node_list(self.ctx, marker=node2['id'])
        self.assertEqual(0, len(result))

        self.eng.node_create(self.ctx, 'n3', self.profile['id'])

        result = self.eng.node_list(self.ctx, limit=1, marker=node1['id'])
        self.assertEqual(1, len(result))
        result = self.eng.node_list(self.ctx, limit=2, marker=node1['id'])
        self.assertEqual(2, len(result))

    @mock.patch.object(dispatcher, 'start_action')
    def test_node_list_with_sort_keys(self, notify):
        node1 = self.eng.node_create(self.ctx, 'CC', self.profile['id'])
        node2 = self.eng.node_create(self.ctx, 'BB', self.profile['id'])

        # default by created_time
        result = self.eng.node_list(self.ctx)
        self.assertEqual(node1['id'], result[0]['id'])
        self.assertEqual(node2['id'], result[1]['id'])

        # use name for sorting
        result = self.eng.node_list(self.ctx, sort='name')
        self.assertEqual(node2['id'], result[0]['id'])
        self.assertEqual(node1['id'], result[1]['id'])

        # unknown keys will be ignored
        result = self.eng.node_list(self.ctx, sort='duang')
        self.assertIsNotNone(result)

    @mock.patch.object(dispatcher, 'start_action')
    def test_node_list_with_sort_dir(self, notify):
        node1 = self.eng.node_create(self.ctx, 'BB', self.profile['id'])
        node2 = self.eng.node_create(self.ctx, 'AA', self.profile['id'])
        node3 = self.eng.node_create(self.ctx, 'CC', self.profile['id'])

        # default by init_at, ascending
        result = self.eng.node_list(self.ctx)
        self.assertEqual(node1['id'], result[0]['id'])
        self.assertEqual(node2['id'], result[1]['id'])

        # sort by init_at, descending
        result = self.eng.node_list(self.ctx, sort='init_at:desc')
        self.assertEqual(node3['id'], result[0]['id'])
        self.assertEqual(node2['id'], result[1]['id'])

        # use name for sorting, descending
        result = self.eng.node_list(self.ctx, sort='name:desc')
        self.assertEqual(node3['id'], result[0]['id'])
        self.assertEqual(node1['id'], result[1]['id'])

    @mock.patch.object(dispatcher, 'start_action')
    def test_node_list_project_safe(self, notify):
        new_ctx = utils.dummy_context(project='a_diff_project')
        spec = {
            'type': 'TestProfile',
            'version': '1.0',
            'properties': {'INT': 10, 'STR': 'string'},
        }
        p1 = self.eng.profile_create(self.ctx, 'p-test-1', spec)
        p2 = self.eng.profile_create(new_ctx, 'p-test-2', spec)
        node1 = self.eng.node_create(self.ctx, 'n1', p1['id'])
        node2 = self.eng.node_create(new_ctx, 'n2', p2['id'])

        # default is project_safe
        result = self.eng.node_list(self.ctx)
        self.assertIsInstance(result, list)
        self.assertEqual(1, len(result))
        self.assertEqual(node1['id'], result[0]['id'])

        result = self.eng.node_list(new_ctx)
        self.assertIsInstance(result, list)
        self.assertEqual(1, len(result))
        self.assertEqual(node2['id'], result[0]['id'])

        # try project_safe set to False
        result = self.eng.node_list(self.ctx, project_safe=False)
        self.assertIsInstance(result, list)
        self.assertEqual(2, len(result))
        self.assertEqual(node1['id'], result[0]['id'])
        self.assertEqual(node2['id'], result[1]['id'])

    @mock.patch.object(dispatcher, 'start_action')
    def test_node_list_with_cluster_id(self, notify):
        c = self.eng.cluster_create(self.ctx, 'c-1', 0, self.profile['id'])
        node = self.eng.node_create(self.ctx, 'n1', self.profile['id'],
                                    cluster_id=c['id'])

        result = self.eng.node_list(self.ctx, cluster_id=c['id'])
        self.assertEqual(1, len(result))
        self.assertEqual(node['id'], result[0]['id'])

        ex = self.assertRaises(rpc.ExpectedException,
                               self.eng.node_list, self.ctx,
                               cluster_id='Bogus')

        self.assertEqual(exception.ClusterNotFound, ex.exc_info[0])
        self.assertEqual('The cluster (Bogus) could not be found.',
                         six.text_type(ex.exc_info[1]))

    @mock.patch.object(dispatcher, 'start_action')
    def test_node_list_with_filters(self, notify):
        self.eng.node_create(self.ctx, 'BB', self.profile['id'])
        self.eng.node_create(self.ctx, 'AA', self.profile['id'])
        self.eng.node_create(self.ctx, 'CC', self.profile['id'])

        result = self.eng.node_list(self.ctx, filters={'name': 'BB'})
        self.assertEqual(1, len(result))
        self.assertEqual('BB', result[0]['name'])

        result = self.eng.node_list(self.ctx, filters={'name': 'DD'})
        self.assertEqual(0, len(result))

    def test_node_list_bad_param(self):
        ex = self.assertRaises(rpc.ExpectedException,
                               self.eng.node_list, self.ctx, limit='no')
        self.assertEqual(exception.InvalidParameter, ex.exc_info[0])

        ex = self.assertRaises(rpc.ExpectedException,
                               self.eng.node_list, self.ctx,
                               project_safe='no')
        self.assertEqual(exception.InvalidParameter, ex.exc_info[0])

    def test_node_list_empty(self):
        result = self.eng.node_list(self.ctx)
        self.assertIsInstance(result, list)
        self.assertEqual(0, len(result))

    @mock.patch.object(dispatcher, 'start_action')
    def test_node_find(self, notify):
        node = self.eng.node_create(self.ctx, 'n1', self.profile['id'])
        nodeid = node['id']

        result = self.eng.node_find(self.ctx, nodeid)
        self.assertIsNotNone(result)

        # short id
        result = self.eng.node_find(self.ctx, nodeid[:5])
        self.assertIsNotNone(result)

        # name
        result = self.eng.node_find(self.ctx, 'n1')
        self.assertIsNotNone(result)

        # others
        self.assertRaises(exception.NodeNotFound,
                          self.eng.node_find, self.ctx, 'Bogus')

    @mock.patch.object(node_mod.Node, 'load')
    @mock.patch.object(dispatcher, 'start_action')
    @mock.patch.object(action_mod, 'Action')
    def test_node_update_simple(self, mock_action, notify, mock_node_load):
        node = self.eng.node_create(self.ctx, 'node-1', self.profile['id'],
                                    role='Master', metadata={'foo': 'bar'})
        nodeid = node['id']
        node_obj = mock.Mock()
        node_obj.id = nodeid
        mock_node_load.return_value = node_obj
        params = {
            'user': self.ctx.user,
            'project': self.ctx.project,
            'domain': self.ctx.domain
        }

        # 1. update name
        mock_action.reset_mock()
        self.eng.node_update(self.ctx, nodeid, name='node-2')
        action_name = 'node_update_%s' % nodeid[:8]
        mock_action.assert_called_once_with(node_obj.id, 'NODE_UPDATE',
                                            name=action_name,
                                            inputs={
                                                'new_profile_id': None,
                                                'name': 'node-2'
                                            },
                                            cause=action_mod.CAUSE_RPC,
                                            **params)

        # 2. update role
        mock_action.reset_mock()
        self.eng.node_update(self.ctx, nodeid, role='worker')
        mock_action.assert_called_once_with(node_obj.id, 'NODE_UPDATE',
                                            name=action_name,
                                            inputs={
                                                'new_profile_id': None,
                                                'role': 'worker'
                                            },
                                            cause=action_mod.CAUSE_RPC,
                                            **params)

        # 3. update metadata
        mock_action.reset_mock()
        self.eng.node_update(self.ctx, nodeid, metadata={'FOO': 'BAR'})
        mock_action.assert_called_once_with(node_obj.id, 'NODE_UPDATE',
                                            name=action_name,
                                            inputs={
                                                'new_profile_id': None,
                                                'metadata': {'FOO': 'BAR'},
                                            },
                                            cause=action_mod.CAUSE_RPC,
                                            **params)

    def test_node_update_node_not_found(self):
        ex = self.assertRaises(rpc.ExpectedException,
                               self.eng.node_update, self.ctx, 'Bogus')

        self.assertEqual(exception.NodeNotFound, ex.exc_info[0])
        self.assertEqual('The node (Bogus) could not be found.',
                         six.text_type(ex.exc_info[1]))

    @mock.patch.object(dispatcher, 'start_action')
    def test_node_update_with_new_profile(self, notify):
        node = self.eng.node_create(self.ctx, 'node-1', self.profile['id'])
        notify.reset_mock()
        new_spec = {
            'type': 'TestProfile',
            'version': '1.0',
            'properties': {'INT': 20},
        }
        new_profile = self.eng.profile_create(self.ctx, 'p-new', new_spec)

        result = self.eng.node_update(self.ctx, node['id'],
                                      profile_id=new_profile['id'])
        self.assertEqual(node, result)

    @mock.patch.object(dispatcher, 'start_action')
    def test_node_update_profile_not_found(self, notify):
        node = self.eng.node_create(self.ctx, 'node-1', self.profile['id'])
        ex = self.assertRaises(rpc.ExpectedException,
                               self.eng.node_update, self.ctx, node['id'],
                               profile_id='Bogus')

        self.assertEqual(exception.SenlinBadRequest, ex.exc_info[0])
        self.assertEqual('The request is malformed: The specified profile '
                         '(Bogus) is not found.',
                         six.text_type(ex.exc_info[1]))

    @mock.patch.object(dispatcher, 'start_action')
    def test_node_update_with_diff_profile_type(self, notify):
        env = environment.global_env()
        env.register_profile('NewProfileType-1.0', fakes.TestProfile)
        new_spec = {
            'type': 'NewProfileType',
            'version': '1.0',
            'properties': {'INT': 20},
        }
        new_profile = self.eng.profile_create(self.ctx, 'p-new', new_spec)

        node = self.eng.node_create(self.ctx, 'node-1', self.profile['id'])

        ex = self.assertRaises(rpc.ExpectedException,
                               self.eng.node_update,
                               self.ctx, node['id'],
                               profile_id=new_profile['id'])

        self.assertEqual(exception.ProfileTypeNotMatch, ex.exc_info[0])
        self.assertEqual('Cannot update a node to a different profile type, '
                         'operation aborted.',
                         six.text_type(ex.exc_info[1]))

    @mock.patch.object(dispatcher, 'start_action')
    def test_node_delete(self, notify):
        node = self.eng.node_create(self.ctx, 'node-1', self.profile['id'])
        nodeid = node['id']

        result = self.eng.node_delete(self.ctx, nodeid)
        self.assertEqual(nodeid, result)

        # verify action is fired
        expected_call = mock.call(action_id=mock.ANY)

        # two calls: one for create, the other for delete
        notify.assert_has_calls([expected_call] * 2)

    def test_node_delete_not_found(self):
        ex = self.assertRaises(rpc.ExpectedException,
                               self.eng.node_delete, self.ctx, 'Bogus')

        self.assertEqual(exception.NodeNotFound, ex.exc_info[0])
        self.assertEqual('The node (Bogus) could not be found.',
                         six.text_type(ex.exc_info[1]))

    @mock.patch.object(node_mod.Node, 'load')
    @mock.patch.object(service.EngineService, 'node_find')
    @mock.patch.object(dispatcher, 'start_action')
    def test_node_check(self, notify, mock_find, mock_load):
        node = mock.Mock()
        node.id = 'nid'
        nodeid = node.id
        node.to_dict = mock.Mock(return_value={'id': nodeid})
        mock_load.return_value = node

        result = self.eng.node_check(self.ctx, nodeid)
        self.assertEqual(node.id, result.get('id'))

        notify.assert_called_once_with(action_id=mock.ANY)

    @mock.patch.object(node_mod.Node, 'load')
    def test_node_check_not_found(self, mock_load):
        nid = 'Bogus'
        exp = exception.NodeNotFound(node=nid)
        mock_load.side_effect = exp

        ex = self.assertRaises(rpc.ExpectedException,
                               self.eng.node_check, self.ctx, nid)

        self.assertEqual(exception.NodeNotFound, ex.exc_info[0])
        self.assertEqual('The node (Bogus) could not be found.',
                         six.text_type(ex.exc_info[1]))

    @mock.patch.object(node_mod.Node, 'load')
    @mock.patch.object(service.EngineService, 'node_find')
    @mock.patch.object(dispatcher, 'start_action')
    def test_node_recover(self, notify, mock_find, mock_load):
        node = mock.Mock()
        node.id = 'nid'
        nodeid = node.id
        node.to_dict = mock.Mock(return_value={'id': nodeid})
        mock_load.return_value = node

        result = self.eng.node_recover(self.ctx, nodeid)
        self.assertEqual(node.id, result.get('id'))

        notify.assert_called_once_with(action_id=mock.ANY)

    @mock.patch.object(node_mod.Node, 'load')
    def test_node_recover_not_found(self, mock_load):
        nid = 'Bogus'
        exp = exception.NodeNotFound(node=nid)
        mock_load.side_effect = exp

        ex = self.assertRaises(rpc.ExpectedException,
                               self.eng.node_recover, self.ctx, nid)

        self.assertEqual(exception.NodeNotFound, ex.exc_info[0])
        self.assertEqual('The node (Bogus) could not be found.',
                         six.text_type(ex.exc_info[1]))
