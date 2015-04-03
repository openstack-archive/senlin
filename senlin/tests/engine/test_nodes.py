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
import six

from senlin.common import exception
from senlin.db import api as db_api
from senlin.engine.actions import base as action_mod
from senlin.engine import dispatcher
from senlin.engine import environment
from senlin.engine import service
from senlin.tests.common import base
from senlin.tests.common import utils
from senlin.tests import fakes


class NodeTest(base.SenlinTestCase):

    def setUp(self):
        super(NodeTest, self).setUp()
        self.ctx = utils.dummy_context(project='node_test_project')
        self.eng = service.EngineService('host-a', 'topic-a')
        self.eng.init_tgm()

        self.eng.dispatcher = mock.Mock()

        env = environment.global_env()
        env.register_profile('TestProfile', fakes.TestProfile)

        self.profile = self.eng.profile_create(
            self.ctx, 'p-test', 'TestProfile',
            spec={'INT': 10, 'STR': 'string'}, perm='1111')

    def _verify_action(self, obj, action, name, target, cause, inputs=None):
        if inputs is None:
            inputs = {}
        self.assertEqual(action, obj['action'])
        self.assertEqual(name, obj['name'])
        self.assertEqual(target, obj['target'])
        self.assertEqual(cause, obj['cause'])
        self.assertEqual(inputs, obj['inputs'])

    @mock.patch.object(dispatcher, 'notify')
    def test_node_create_default(self, notify):
        node = self.eng.node_create(self.ctx, 'n-1', self.profile['id'])
        self.assertIsNotNone(node)
        self.assertEqual('n-1', node['name'])
        self.assertEqual(-1, node['index'])
        self.assertEqual(self.profile['id'], node['profile_id'])
        self.assertIsNone(node['cluster_id'])
        self.assertIsNone(node['role'])
        self.assertEqual({}, node['tags'])

        action_id = node['action']
        action = db_api.action_get(self.ctx, action_id)
        self.assertIsNotNone(action)
        self._verify_action(action, 'NODE_CREATE',
                            'node_create_%s' % node['id'][:8],
                            node['id'],
                            cause=action_mod.CAUSE_RPC)
        notify.assert_called_once_with(self.ctx,
                                       self.eng.dispatcher.NEW_ACTION,
                                       None, action_id=action_id)

    def test_node_create_profile_not_found(self):
        ex = self.assertRaises(rpc.ExpectedException,
                               self.eng.node_create,
                               self.ctx, 'n-1', 'Bogus')
        self.assertEqual(exception.ProfileNotFound, ex.exc_info[0])

    @mock.patch.object(dispatcher, 'notify')
    def test_node_create_with_role_and_tags(self, notify):
        node = self.eng.node_create(self.ctx, 'n-1', self.profile['id'],
                                    role='master', tags={'k': 'v'})

        self.assertIsNotNone(node)
        self.assertEqual('n-1', node['name'])
        self.assertEqual('master', node['role'])
        self.assertEqual({'k': 'v'}, node['tags'])

    @mock.patch.object(dispatcher, 'notify')
    def test_node_create_with_profile_name_or_short_id(self, notify):
        node = self.eng.node_create(self.ctx, 'n-1', self.profile['id'][:8])
        self.assertIsNotNone(node)
        self.assertEqual(self.profile['id'], node['profile_id'])

        node = self.eng.node_create(self.ctx, 'n-2', self.profile['name'])
        self.assertIsNotNone(node)
        self.assertEqual(self.profile['id'], node['profile_id'])

    def test_node_create_with_cluster_id_not_found(self):
        ex = self.assertRaises(rpc.ExpectedException,
                               self.eng.node_create,
                               self.ctx, 'n-1', self.profile['id'],
                               cluster_id='Bogus')

        self.assertEqual(exception.ClusterNotFound, ex.exc_info[0])
        self.assertEqual("The cluster (Bogus) could not be found.",
                         six.text_type(ex.exc_info[1]))

    @mock.patch.object(dispatcher, 'notify')
    def test_node_create_project_not_match(self, notify):
        ctx_cluster = utils.dummy_context(project='a-different-project')
        cluster = self.eng.cluster_create(ctx_cluster, 'c-1', 0,
                                          self.profile['id'])

        ex = self.assertRaises(rpc.ExpectedException,
                               self.eng.node_create,
                               self.ctx, 'n-1', self.profile['id'],
                               cluster_id=cluster['id'])

        self.assertEqual(exception.ClusterNotFound, ex.exc_info[0])
        self.assertEqual("The cluster (%s) could not be found."
                         "" % cluster['id'],
                         six.text_type(ex.exc_info[1]))

    @mock.patch.object(dispatcher, 'notify')
    def test_node_create_profile_type_not_match(self, notify):
        env = environment.global_env()
        env.register_profile('SecondProfile', fakes.TestProfile)
        cluster_profile = self.eng.profile_create(
            self.ctx, 'cluster-profile', 'SecondProfile',
            spec={'INT': 20, 'STR': 'string'})

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

    @mock.patch.object(dispatcher, 'notify')
    def test_node_get(self, notify):
        node = self.eng.node_create(self.ctx, 'n-1', self.profile['id'])

        for identity in [node['id'], node['id'][:6], 'n-1']:
            result = self.eng.node_get(self.ctx, identity)
            self.assertIsInstance(result, dict)
            self.assertEqual(node['id'], result['id'])

        ex = self.assertRaises(rpc.ExpectedException,
                               self.eng.node_get, self.ctx, 'Bogus')
        self.assertEqual(exception.NodeNotFound, ex.exc_info[0])

    @mock.patch.object(dispatcher, 'notify')
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

    @mock.patch.object(dispatcher, 'notify')
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

    @mock.patch.object(dispatcher, 'notify')
    def test_node_list_with_sort_keys(self, notify):
        node1 = self.eng.node_create(self.ctx, 'CC', self.profile['id'])
        node2 = self.eng.node_create(self.ctx, 'BB', self.profile['id'])

        # default by created_time
        result = self.eng.node_list(self.ctx)
        self.assertEqual(node1['id'], result[0]['id'])
        self.assertEqual(node2['id'], result[1]['id'])

        # use name for sorting
        result = self.eng.node_list(self.ctx, sort_keys=['name'])
        self.assertEqual(node2['id'], result[0]['id'])
        self.assertEqual(node1['id'], result[1]['id'])

        # unknown keys will be ignored
        result = self.eng.node_list(self.ctx, sort_keys=['duang'])
        self.assertIsNotNone(result)

    @mock.patch.object(dispatcher, 'notify')
    def test_node_list_with_sort_dir(self, notify):
        node1 = self.eng.node_create(self.ctx, 'BB', self.profile['id'])
        node2 = self.eng.node_create(self.ctx, 'AA', self.profile['id'])
        node3 = self.eng.node_create(self.ctx, 'CC', self.profile['id'])

        # default by created_time, ascending
        result = self.eng.node_list(self.ctx)
        self.assertEqual(node1['id'], result[0]['id'])
        self.assertEqual(node2['id'], result[1]['id'])

        # sort by created_time, descending
        result = self.eng.node_list(self.ctx, sort_dir='desc')
        self.assertEqual(node3['id'], result[0]['id'])
        self.assertEqual(node2['id'], result[1]['id'])

        # use name for sorting, descending
        result = self.eng.node_list(self.ctx, sort_keys=['name'],
                                    sort_dir='desc')
        self.assertEqual(node3['id'], result[0]['id'])
        self.assertEqual(node1['id'], result[1]['id'])

        # use permission for sorting
        ex = self.assertRaises(ValueError,
                               self.eng.node_list, self.ctx,
                               sort_dir='Bogus')
        self.assertEqual("Unknown sort direction, must be "
                         "'desc' or 'asc'", six.text_type(ex))

    @mock.patch.object(dispatcher, 'notify')
    def test_node_list_show_deleted(self, notify):
        node = self.eng.node_create(self.ctx, 'n1', self.profile['id'])
        result = self.eng.node_list(self.ctx)
        self.assertEqual(1, len(result))
        self.assertEqual(node['id'], result[0]['id'])

        db_api.node_delete(self.ctx, node['id'])

        result = self.eng.node_list(self.ctx)
        self.assertEqual(0, len(result))

        result = self.eng.node_list(self.ctx, show_deleted=True)
        self.assertEqual(1, len(result))
        self.assertEqual(node['id'], result[0]['id'])

    @mock.patch.object(dispatcher, 'notify')
    def test_node_list_project_safe(self, notify):
        node1 = self.eng.node_create(self.ctx, 'n1', self.profile['id'])
        new_ctx = utils.dummy_context(project='a_diff_project')
        node2 = self.eng.node_create(new_ctx, 'n2', self.profile['id'])

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

    @mock.patch.object(dispatcher, 'notify')
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

    @mock.patch.object(dispatcher, 'notify')
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
                               show_deleted='no')
        self.assertEqual(exception.InvalidParameter, ex.exc_info[0])

        ex = self.assertRaises(rpc.ExpectedException,
                               self.eng.node_list, self.ctx,
                               project_safe='no')
        self.assertEqual(exception.InvalidParameter, ex.exc_info[0])

    def test_node_list_empty(self):
        result = self.eng.node_list(self.ctx)
        self.assertIsInstance(result, list)
        self.assertEqual(0, len(result))

    @mock.patch.object(dispatcher, 'notify')
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

    @mock.patch.object(dispatcher, 'notify')
    def test_node_find_show_deleted(self, notify):
        node = self.eng.node_create(self.ctx, 'n1', self.profile['id'])
        nodeid = node['id']
        db_api.node_delete(self.ctx, nodeid)

        for identity in [nodeid, nodeid[:6], 'n1']:
            self.assertRaises(exception.NodeNotFound,
                              self.eng.node_find, self.ctx, identity)

        # short id and name based finding does not support show_deleted
        for identity in [nodeid[:6], 'n-1']:
            self.assertRaises(exception.NodeNotFound,
                              self.eng.node_find, self.ctx, identity)

        # ID based finding is okay with show_deleted
        result = self.eng.node_find(self.ctx, nodeid, show_deleted=True)
        self.assertIsNotNone(result)

    @mock.patch.object(dispatcher, 'notify')
    def test_node_update_simple(self, notify):
        node = self.eng.node_create(self.ctx, 'node-1', self.profile['id'],
                                    role='Master', tags={'foo': 'bar'})
        nodeid = node['id']

        # 1. update name
        self.eng.node_update(self.ctx, nodeid, name='node-2')
        res = self.eng.node_get(self.ctx, nodeid)
        self.assertEqual(nodeid, res['id'])
        self.assertEqual('node-2', res['name'])

        # 2. update role
        self.eng.node_update(self.ctx, nodeid, role='worker')
        res = self.eng.node_get(self.ctx, nodeid)
        self.assertEqual(nodeid, res['id'])
        self.assertEqual('worker', res['role'])

        # 3. update tags
        self.eng.node_update(self.ctx, nodeid, tags={'FOO': 'BAR'})
        res = self.eng.node_get(self.ctx, nodeid)
        self.assertEqual(nodeid, res['id'])
        self.assertEqual({'FOO': 'BAR'}, res['tags'])

    def test_node_update_node_not_found(self):
        ex = self.assertRaises(rpc.ExpectedException,
                               self.eng.node_update, self.ctx, 'Bogus')

        self.assertEqual(exception.NodeNotFound, ex.exc_info[0])
        self.assertEqual('The node (Bogus) could not be found.',
                         six.text_type(ex.exc_info[1]))

    @mock.patch.object(dispatcher, 'notify')
    def test_node_update_with_new_profile(self, notify):
        node = self.eng.node_create(self.ctx, 'node-1', self.profile['id'])
        new_profile = self.eng.profile_create(
            self.ctx, 'p-new', 'TestProfile', spec={'INT': 20})

        self.eng.node_update(self.ctx, node['id'],
                             profile_id=new_profile['id'])

        # TODO(anyone): uncomment the following lines when cluster-update
        # is implemented
        # action_id = result['action']
        # action = self.eng.action_get(self.ctx, action_id)
        # self._verify_action(action, 'NODE_UPDATE',
        #                     'node_update_%s' % c['id'][:8],
        #                     result['id'],
        #                     cause=action_mod.CAUSE_RPC)

        # notify.assert_called_once_with(self.ctx,
        #                                self.eng.dispatcher.NEW_ACTION,
        #                                None, action_id=action_id)

    @mock.patch.object(dispatcher, 'notify')
    def test_node_update_profile_not_found(self, notify):
        node = self.eng.node_create(self.ctx, 'node-1', self.profile['id'])
        ex = self.assertRaises(rpc.ExpectedException,
                               self.eng.node_update, self.ctx, node['id'],
                               profile_id='Bogus')

        self.assertEqual(exception.ProfileNotFound, ex.exc_info[0])
        self.assertEqual('The profile (Bogus) could not be found.',
                         six.text_type(ex.exc_info[1]))

    @mock.patch.object(dispatcher, 'notify')
    def test_node_update_with_diff_profile_type(self, notify):
        env = environment.global_env()
        env.register_profile('NewProfileType', fakes.TestProfile)
        new_profile = self.eng.profile_create(
            self.ctx, 'p-new', 'NewProfileType', spec={'INT': 20})

        node = self.eng.node_create(self.ctx, 'node-1', self.profile['id'])

        ex = self.assertRaises(rpc.ExpectedException,
                               self.eng.node_update,
                               self.ctx, node['id'],
                               profile_id=new_profile['id'])

        self.assertEqual(exception.ProfileTypeNotMatch, ex.exc_info[0])
        self.assertEqual('Cannot update a node to a different profile type, '
                         'operation aborted.',
                         six.text_type(ex.exc_info[1]))

    @mock.patch.object(dispatcher, 'notify')
    def test_node_delete(self, notify):
        node = self.eng.node_create(self.ctx, 'node-1', self.profile['id'])
        nodeid = node['id']

        result = self.eng.node_delete(self.ctx, nodeid)
        self.assertIsNotNone(result)

        # verify action is fired
        action_id = result['action']
        action = self.eng.action_get(self.ctx, action_id)
        self._verify_action(action, 'NODE_DELETE',
                            'node_delete_%s' % node['id'][:8],
                            node['id'],
                            cause=action_mod.CAUSE_RPC)

        expected_call = mock.call(self.ctx,
                                  self.eng.dispatcher.NEW_ACTION,
                                  None, action_id=mock.ANY)

        # two calls: one for create, the other for delete
        notify.assert_has_calls([expected_call] * 2)

    def test_node_delete_not_found(self):
        ex = self.assertRaises(rpc.ExpectedException,
                               self.eng.node_delete, self.ctx, 'Bogus')

        self.assertEqual(exception.NodeNotFound, ex.exc_info[0])
        self.assertEqual('The node (Bogus) could not be found.',
                         six.text_type(ex.exc_info[1]))

    @mock.patch.object(dispatcher, 'notify')
    def test_node_join(self, notify):
        c = self.eng.cluster_create(self.ctx, 'c-1', 0, self.profile['id'])
        cluster_id = c['id']

        node = self.eng.node_create(self.ctx, 'node1', self.profile['id'])
        node_id = node['id']

        result = self.eng.node_join(self.ctx, node_id, cluster_id)

        action_id = result['action']
        action = db_api.action_get(self.ctx, result['action'])
        self.assertIsNotNone(action)
        self._verify_action(action, 'NODE_JOIN',
                            'node_join_%s' % node_id[:8], node_id,
                            cause=action_mod.CAUSE_RPC,
                            inputs={'cluster_id': cluster_id})
        notify.assert_called_with(self.ctx,
                                  self.eng.dispatcher.NEW_ACTION,
                                  None, action_id=action_id)
        # Two creations plus one join
        self.assertEqual(3, notify.call_count)

    @mock.patch.object(dispatcher, 'notify')
    def test_node_join_from_other_cluster(self, notify):
        c = self.eng.cluster_create(self.ctx, 'c-1', 0, self.profile['id'])
        cluster_id = c['id']
        new_cluster = self.eng.cluster_create(self.ctx, 'c-new', 0,
                                              self.profile['id'])
        new_cluster_id = new_cluster['id']

        node = self.eng.node_create(self.ctx, 'node1', self.profile['id'],
                                    cluster_id=cluster_id)
        node_id = node['id']

        result = self.eng.node_join(self.ctx, node_id, new_cluster_id)

        action = db_api.action_get(self.ctx, result['action'])
        self.assertIsNotNone(action)
        self._verify_action(action, 'NODE_JOIN',
                            'node_join_%s' % node_id[:8], node_id,
                            cause=action_mod.CAUSE_RPC,
                            inputs={'cluster_id': new_cluster_id})
        notify.assert_called_with(self.ctx, self.eng.dispatcher.NEW_ACTION,
                                  mock.ANY, action_id=mock.ANY)
        # Three creations plus one join
        self.assertEqual(4, notify.call_count)

    def test_node_join_node_not_found(self):
        ex = self.assertRaises(rpc.ExpectedException,
                               self.eng.node_join,
                               self.ctx, 'BogusNode', 'a-cluster')

        self.assertEqual(exception.NodeNotFound, ex.exc_info[0])
        self.assertEqual('The node (BogusNode) could not be found.',
                         six.text_type(ex.exc_info[1]))

    @mock.patch.object(dispatcher, 'notify')
    def test_node_join_cluster_not_found(self, notify):
        node = self.eng.node_create(self.ctx, 'node1', self.profile['id'])
        node_id = node['id']

        ex = self.assertRaises(rpc.ExpectedException,
                               self.eng.node_join,
                               self.ctx, node_id, 'BogusCluster')

        self.assertEqual(exception.ClusterNotFound, ex.exc_info[0])
        self.assertEqual('The cluster (BogusCluster) could not be found.',
                         six.text_type(ex.exc_info[1]))

    @mock.patch.object(dispatcher, 'notify')
    def test_node_join_profile_type_not_match(self, notify):
        # prepare a cluster with different profile type
        env = environment.global_env()
        env.register_profile('OtherProfileType', fakes.TestProfile)
        other_profile = self.eng.profile_create(
            self.ctx, 'new-profile', 'OtherProfileType',
            spec={'INT': 20, 'STR': 'okay'})

        c = self.eng.cluster_create(self.ctx, 'c-1', 0, other_profile['id'])
        cluster_id = c['id']

        node = self.eng.node_create(self.ctx, 'node1', self.profile['id'])
        node_id = node['id']

        ex = self.assertRaises(rpc.ExpectedException,
                               self.eng.node_join,
                               self.ctx, node_id, cluster_id)

        self.assertEqual(exception.ProfileTypeNotMatch, ex.exc_info[0])
        self.assertEqual('Node and cluster have different profile type, '
                         'operation aborted.',
                         six.text_type(ex.exc_info[1]))

    @mock.patch.object(dispatcher, 'notify')
    def test_node_leave(self, notify):
        c = self.eng.cluster_create(self.ctx, 'c-1', 0, self.profile['id'])
        cluster_id = c['id']

        node = self.eng.node_create(self.ctx, 'node1', self.profile['id'],
                                    cluster_id=cluster_id)
        node_id = node['id']

        result = self.eng.node_leave(self.ctx, node_id)

        action = db_api.action_get(self.ctx, result['action'])
        self.assertIsNotNone(action)
        self._verify_action(action, 'NODE_LEAVE',
                            'node_leave_%s' % node_id[:8], node_id,
                            cause=action_mod.CAUSE_RPC)
        notify.assert_called_with(self.ctx,
                                  self.eng.dispatcher.NEW_ACTION,
                                  None, action_id=mock.ANY)
        # Two creations plus one leave
        self.assertEqual(3, notify.call_count)

    def test_node_leave_node_not_found(self):
        ex = self.assertRaises(rpc.ExpectedException,
                               self.eng.node_leave,
                               self.ctx, 'BogusNode')

        self.assertEqual(exception.NodeNotFound, ex.exc_info[0])
        self.assertEqual('The node (BogusNode) could not be found.',
                         six.text_type(ex.exc_info[1]))

    @mock.patch.object(dispatcher, 'notify')
    def test_node_leave_already_orphan(self, notify):
        node = self.eng.node_create(self.ctx, 'node1', self.profile['id'])
        node_id = node['id']

        ex = self.assertRaises(rpc.ExpectedException,
                               self.eng.node_leave,
                               self.ctx, node_id)

        self.assertEqual(exception.SenlinBadRequest, ex.exc_info[0])
        self.assertEqual('The request is malformed: Node is already an '
                         'orphan node: %s.' % node_id,
                         six.text_type(ex.exc_info[1]))
