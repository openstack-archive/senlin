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

import six

from senlin.common import exception
from senlin.db.sqlalchemy import api as db_api
from senlin.engine import event as eventm
from senlin.engine import node as nodem
from senlin.tests.common import base
from senlin.tests.common import utils


class TestNode(base.SenlinTestCase):

    def setUp(self):
        super(TestNode, self).setUp()
        self.context = utils.dummy_context()
        self.profile = self._create_profile('PROFILE_ID')
        self.cluster = self._create_cluster('CLUSTER_ID')

    def _create_profile(self, profile_id):
        values = {
            'id': profile_id,
            'type': 'os.nova.server',
            'name': 'test-profile',
        }
        return db_api.profile_create(self.context, values)

    def _create_cluster(self, cluster_id):
        values = {
            'id': cluster_id,
            'profile_id': self.profile.id,
            'name': 'test-cluster',
            'user': self.context.user,
            'project': self.context.project,
            'next_index': 1,
        }

        return db_api.cluster_create(self.context, values)

    def _create_node(self, node_id):
        values = {
            'id': node_id,
            'profile_id': self.profile.id,
            'cluster_id': self.cluster.id,
            'project': self.context.project,
            'name': 'node1',
            'role': 'test_node',
            }
        return db_api.node_create(self.context, values)

    def test_node_init(self):
        node = nodem.Node('node1', self.profile.id, self.cluster.id,
                          role='first_node')
        self.assertIsNone(node.id)
        self.assertEqual('node1', node.name)
        self.assertEqual('', node.physical_id)
        self.assertEqual(self.profile.id, node.profile_id)
        self.assertEqual('', node.user)
        self.assertEqual('', node.project)
        self.assertEqual('', node.domain)
        self.assertEqual(self.cluster.id, node.cluster_id)
        self.assertEqual(-1, node.index)
        self.assertEqual('first_node', node.role)

        self.assertIsNone(node.init_time)
        self.assertIsNone(node.created_time)
        self.assertIsNone(node.updated_time)
        self.assertIsNone(node.deleted_time)

        self.assertEqual('INIT', node.status)
        self.assertEqual('Initializing', node.status_reason)
        self.assertEqual({}, node.data)
        self.assertEqual({}, node.metadata)
        self.assertEqual({}, node.rt)

    def test_node_store_init(self):
        node = nodem.Node('node1', self.profile.id, self.cluster.id,
                          self.context, role='first_node')
        mock_info = self.patchobject(eventm, 'info')
        self.assertIsNone(node.id)
        node_id = node.store(self.context)
        self.assertIsNotNone(node_id)

        node_info = db_api.node_get(self.context, node_id)
        self.assertIsNotNone(node_info)
        self.assertEqual('node1', node_info.name)
        self.assertEqual('', node_info.physical_id)
        self.assertEqual(self.cluster.id, node_info.cluster_id)
        self.assertEqual(self.profile.id, node_info.profile_id)
        self.assertEqual(self.context.user, node_info.user)
        self.assertEqual(self.context.project, node_info.project)
        self.assertEqual(self.context.domain, node_info.domain)
        self.assertEqual(1, node_info.index)
        self.assertEqual('first_node', node.role)

        self.assertIsNotNone(node_info.init_time)
        self.assertIsNone(node_info.created_time)
        self.assertIsNone(node_info.updated_time)
        self.assertIsNone(node_info.deleted_time)

        self.assertEqual('INIT', node_info.status)
        self.assertEqual('Initializing', node_info.status_reason)
        self.assertEqual({}, node_info.meta_data)
        self.assertEqual({}, node_info.data)

        mock_info.assert_called_once_with(self.context, node, 'create')

    def test_node_load(self):
        ex = self.assertRaises(exception.NodeNotFound,
                               nodem.Node.load,
                               self.context, 'non-existent', None)
        self.assertEqual('The node (non-existent) could not be found.',
                         six.text_type(ex))

        node = self._create_node('NODE_ID')
        node_info = nodem.Node.load(self.context, 'NODE_ID')

        self.assertEqual(node.id, node_info.id)
        self.assertEqual(node.name, node_info.name)
        self.assertEqual(node.physical_id, node_info.physical_id)
        self.assertEqual(node.cluster_id, node_info.cluster_id)
        self.assertEqual(node.profile_id, node_info.profile_id)
        self.assertEqual(node.user, node_info.user)
        self.assertEqual(node.project, node_info.project)
        self.assertEqual(node.domain, node_info.domain)
        self.assertEqual(node.index, node_info.index)
        self.assertEqual(node.role, node_info.role)

        self.assertEqual(node.init_time, node_info.init_time)
        self.assertEqual(node.created_time, node_info.created_time)
        self.assertEqual(node.updated_time, node_info.updated_time)
        self.assertEqual(node.deleted_time, node_info.deleted_time)

        self.assertEqual(node.status, node_info.status)
        self.assertEqual(node.status_reason, node_info.status_reason)
        self.assertEqual(node.meta_data, node_info.metadata)
        self.assertEqual(node.data, node_info.data)

    def test_node_load_all(self):
        node_info = nodem.Node.load_all(self.context)
        self.assertEqual([], [c for c in node_info])

        node1 = self._create_node('NODE1')
        node2 = self._create_node('NODE2')

        # NOTE: we don't test all other parameters because the db api tests
        #       already covered that
        nodes = nodem.Node.load_all(self.context)
        self.assertEqual(2, len(nodes))
        self.assertEqual(node1.id, nodes[0].id)
        self.assertEqual(node2.id, nodes[1].id)
