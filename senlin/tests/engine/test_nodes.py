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
        self.ctx = utils.dummy_context(tenant_id='node_test_tenant')
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
    def test_cluster_create_with_role_and_tags(self, notify):
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
        ctx_cluster = utils.dummy_context(tenant_id='a-different-tenant')
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
    def test_cluster_list_with_cluster_id(self, notify):
        c = self.eng.cluster_create(self.ctx, 'c-1', 0, self.profile['id'])
        node = self.eng.node_create(self.ctx, 'n1', self.profile['id'],
                                    cluster_id=c['id'])

        result = self.eng.node_list(self.ctx, cluster_id=c['id'])
        self.assertEqual(1, len(result))
        self.assertEqual(node['id'], result[0]['id'])

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

    def test_cluster_list_bad_param(self):
        ex = self.assertRaises(rpc.ExpectedException,
                               self.eng.cluster_list, self.ctx, limit='no')
        self.assertEqual(exception.InvalidParameter, ex.exc_info[0])

        ex = self.assertRaises(rpc.ExpectedException,
                               self.eng.cluster_list, self.ctx,
                               show_deleted='no')
        self.assertEqual(exception.InvalidParameter, ex.exc_info[0])

        ex = self.assertRaises(rpc.ExpectedException,
                               self.eng.cluster_list, self.ctx,
                               tenant_safe='no')
        self.assertEqual(exception.InvalidParameter, ex.exc_info[0])

    def test_cluster_list_empty(self):
        result = self.eng.node_list(self.ctx)
        self.assertIsInstance(result, list)
        self.assertEqual(0, len(result))
