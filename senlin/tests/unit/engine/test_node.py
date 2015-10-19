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
import six

from oslo_utils import timeutils

from senlin.common import exception
from senlin.db.sqlalchemy import api as db_api
from senlin.engine import event as eventm
from senlin.engine import node as nodem
from senlin.profiles import base as profiles_base
from senlin.tests.unit.common import base
from senlin.tests.unit.common import utils


class TestNode(base.SenlinTestCase):

    def setUp(self):
        super(TestNode, self).setUp()
        self.context = utils.dummy_context()
        self.profile = self._create_profile('PROFILE_ID')
        self.cluster = self._create_cluster('CLUSTER_ID')

    def _create_profile(self, profile_id):
        values = {
            'id': profile_id,
            'type': 'os.nova.server-1.0',
            'name': 'test-profile',
            'spec': {
                'type': 'os.nova.server',
                'version': '1.0',
            },
            'user': self.context.user,
            'project': self.context.project
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

    def test_node_init_random_name(self):
        node = nodem.Node(None, self.profile.id, None)
        self.assertIsNotNone(node.name)
        self.assertEqual(13, len(node.name))

    @mock.patch.object(eventm, 'info')
    def test_node_store_init(self, mock_info):
        node = nodem.Node('node1', self.profile.id, self.cluster.id,
                          self.context, role='first_node',
                          index=1)
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

    @mock.patch.object(eventm, 'info')
    def test_node_store_update(self, mock_info):
        node = nodem.Node('node1', self.profile.id, None)
        node_id = node.store(self.context)

        mock_info.assert_called_once_with(self.context, node, 'create')
        mock_info.reset_mock()

        node.name = 'new_name'
        new_node_id = node.store(self.context)

        self.assertEqual(node_id, new_node_id)
        mock_info.assert_called_once_with(self.context, node, 'update')

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

    def test_node_load_diff_project(self):
        self._create_node('NODE_ID')
        new_ctx = utils.dummy_context(project='a-different-project')
        ex = self.assertRaises(exception.NodeNotFound,
                               nodem.Node.load,
                               new_ctx, 'NODE_ID', None)
        self.assertEqual('The node (NODE_ID) could not be found.',
                         six.text_type(ex))

        res = nodem.Node.load(new_ctx, 'NODE_ID', project_safe=False)
        self.assertIsNotNone(res)
        self.assertEqual('NODE_ID', res.id)

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

    def test_node_to_dict(self):
        def _fmt_time(value):
            return value and value.isoformat()

        node = self._create_node('NODE1')
        self.assertIsNotNone(node.id)
        expected = {
            'id': node.id,
            'name': node.name,
            'cluster_id': node.cluster_id,
            'physical_id': node.physical_id,
            'profile_id': node.profile_id,
            'user': node.user,
            'project': node.project,
            'domain': node.domain,
            'index': node.index,
            'role': node.role,
            'init_time': _fmt_time(node.init_time),
            'created_time': _fmt_time(node.created_time),
            'updated_time': _fmt_time(node.updated_time),
            'deleted_time': _fmt_time(node.deleted_time),
            'status': node.status,
            'status_reason': node.status_reason,
            'data': node.data,
            'metadata': node.meta_data,
        }
        result = nodem.Node.load(self.context, 'NODE1')
        dt = result.to_dict()
        del dt['profile_name']
        self.assertEqual(expected, dt)

    def test_node_set_status(self):
        node = nodem.Node('node1', self.profile.id, self.cluster.id,
                          self.context)
        node.store(self.context)
        self.assertEqual(nodem.Node.INIT, node.status)
        self.assertIsNotNone(node.init_time)
        self.assertIsNone(node.created_time)
        self.assertIsNone(node.updated_time)

        # create
        node.set_status(self.context, node.CREATING,
                        reason='Creation in progress')
        self.assertEqual('CREATING', node.status)
        self.assertEqual('Creation in progress', node.status_reason)
        self.assertIsNone(node.created_time)
        self.assertIsNone(node.updated_time)
        self.assertIsNone(node.deleted_time)

        node.set_status(self.context, node.ACTIVE,
                        reason='Creation succeeded')
        self.assertEqual('ACTIVE', node.status)
        self.assertEqual('Creation succeeded', node.status_reason)
        self.assertIsNotNone(node.created_time)
        self.assertIsNone(node.updated_time)
        self.assertIsNone(node.deleted_time)

        # update
        node.set_status(self.context, node.UPDATING,
                        reason='Update in progress')
        self.assertEqual('UPDATING', node.status)
        self.assertEqual('Update in progress', node.status_reason)
        self.assertIsNotNone(node.created_time)
        self.assertIsNone(node.deleted_time)
        self.assertIsNone(node.updated_time)

        node.set_status(self.context, node.ACTIVE,
                        reason='Update succeeded')
        self.assertEqual('ACTIVE', node.status)
        self.assertEqual('Update succeeded', node.status_reason)
        self.assertIsNotNone(node.created_time)
        self.assertIsNone(node.deleted_time)
        self.assertIsNotNone(node.updated_time)

        node.set_status(self.context, node.ACTIVE)
        self.assertEqual('ACTIVE', node.status)
        self.assertIsNotNone(node.created_time)
        self.assertIsNone(node.deleted_time)
        self.assertIsNotNone(node.updated_time)

        # delete
        node.set_status(self.context, node.DELETING,
                        reason='Deletion in progress')
        self.assertEqual('DELETING', node.status)
        self.assertEqual('Deletion in progress', node.status_reason)
        self.assertIsNotNone(node.created_time)
        self.assertIsNone(node.deleted_time)

        node.set_status(self.context, node.DELETED,
                        reason='Deletion succeeded')
        self.assertEqual('DELETED', node.status)
        self.assertEqual('Deletion succeeded', node.status_reason)
        self.assertIsNotNone(node.created_time)
        self.assertIsNotNone(node.deleted_time)

    @mock.patch.object(profiles_base.Profile, 'get_details')
    def test_node_get_details(self, mock_details):
        node = nodem.Node('node1', self.profile.id, None)
        for physical_id in (None, ''):
            node.physical_id = physical_id
            self.assertEqual({}, node.get_details(self.context))
            self.assertEqual(0, mock_details.call_count)

        node.physical_id = 'FAKE_ID'
        mock_details.return_value = {'foo': 'bar'}
        res = node.get_details(self.context)
        mock_details.assert_called_once_with(self.context, node)
        self.assertEqual({'foo': 'bar'}, res)

    @mock.patch.object(eventm, 'warning')
    def test_node_handle_exception(self, mock_warning):
        ex = exception.ResourceStatusError(resource_id='FAKE_ID',
                                           status='FAKE_STATUS',
                                           reason='FAKE_REASON')
        node = nodem.Node('node1', self.profile.id, None, self.context)
        node.store(self.context)
        node._handle_exception(self.context, 'ACTION', 'STATUS', ex)
        db_node = db_api.node_get(self.context, node.id)
        self.assertEqual(node.ERROR, db_node.status)
        self.assertEqual('Profile failed in ACTIOing resource '
                         '(FAKE_ID) due to: %s' % six.text_type(ex),
                         db_node.status_reason)
        self.assertEqual('FAKE_ID', db_node.physical_id)
        mock_warning.assert_called_with(self.context, node, 'ACTION',
                                        'STATUS', six.text_type(ex))

        # Exception happens before physical node creation started.
        ex = exception.ResourceCreationFailure(rtype='stack',
                                               code=400,
                                               message='Bad request')
        node = nodem.Node('node1', self.profile.id, None, self.context)
        node.store(self.context)
        node._handle_exception(self.context, 'CREATE', 'STATUS', ex)
        db_node = db_api.node_get(self.context, node.id)
        self.assertEqual(node.ERROR, db_node.status)
        self.assertEqual('Profile failed in creating node due to: '
                         '%s' % six.text_type(ex), db_node.status_reason)
        self.assertEqual(None, db_node.physical_id)
        mock_warning.assert_called_with(self.context, node, 'CREATE',
                                        'STATUS', six.text_type(ex))

    @mock.patch.object(eventm, 'info')
    @mock.patch.object(nodem.Node, 'store')
    @mock.patch.object(nodem.Node, 'set_status')
    @mock.patch.object(profiles_base.Profile, 'create_object')
    def test_node_create(self, mock_create, mock_status, mock_store,
                         mock_event):
        node = nodem.Node('node1', self.profile.id, self.cluster.id,
                          self.context)
        physical_id = 'fake_id'
        mock_create.return_value = physical_id
        res = node.do_create(self.context)
        self.assertTrue(res)
        mock_status.assert_any_call(self.context, node.CREATING,
                                    reason='Creation in progress')
        mock_status.assert_any_call(self.context, node.ACTIVE,
                                    'Creation succeeded')
        mock_store.assert_called_once_with(self.context)
        mock_event.assert_called_once_with(self.context, node, 'create')
        self.assertEqual(physical_id, node.physical_id)

    def test_node_create_not_init(self):
        node = nodem.Node('node1', self.profile.id, self.cluster.id,
                          self.context)
        node.status = 'NOT_INIT'
        res = node.do_create(self.context)
        self.assertFalse(res)

    @mock.patch.object(eventm, 'info')
    @mock.patch.object(nodem.Node, 'set_status')
    @mock.patch.object(profiles_base.Profile, 'create_object')
    def test_node_create_not_created(self, mock_create, mock_status,
                                     mock_event):
        node = nodem.Node('node1', self.profile.id, self.cluster.id,
                          self.context)
        mock_create.return_value = None
        res = node.do_create(self.context)
        self.assertFalse(res)
        mock_status.assert_called_once_with(self.context, node.CREATING,
                                            reason='Creation in progress')
        mock_event.assert_called_once_with(self.context, node, 'create')

    @mock.patch.object(eventm, 'info')
    @mock.patch.object(nodem.Node, '_handle_exception')
    @mock.patch.object(nodem.Node, 'set_status')
    @mock.patch.object(profiles_base.Profile, 'create_object')
    def test_node_create_internal_error(self, mock_create, mock_status,
                                        mock_handle_exception,
                                        mock_event):
        ex = exception.InternalError(code=500, message='internal error')
        mock_create.side_effect = ex
        node = nodem.Node('node1', self.profile.id, self.cluster.id,
                          self.context)
        res = node.do_create(self.context)
        self.assertFalse(res)
        mock_handle_exception.assert_called_once_with(self.context,
                                                      'create', 'ERROR', ex)
        mock_event.assert_called_once_with(self.context, node, 'create')

    @mock.patch.object(eventm, 'info')
    @mock.patch.object(db_api, 'node_delete')
    @mock.patch.object(nodem.Node, 'set_status')
    @mock.patch.object(profiles_base.Profile, 'delete_object')
    def test_node_delete(self, mock_delete, mock_status, mock_db_delete,
                         mock_event):
        node = nodem.Node('node1', self.profile.id, self.cluster.id,
                          self.context)
        node.physical_id = 'fake_id'
        res = node.do_delete(self.context)
        self.assertTrue(res)
        mock_delete.assert_called_once_with(mock.ANY, node)
        mock_db_delete.assert_called_once_with(mock.ANY, node.id, False)
        mock_status.assert_called_once_with(self.context, node.DELETING,
                                            reason='Deletion in progress')
        mock_event.assert_called_once_with(self.context, node, 'delete')

    @mock.patch.object(db_api, 'node_delete')
    @mock.patch.object(profiles_base.Profile, 'delete_object')
    def test_node_delete_not_created(self, mock_delete, mock_db_delete):
        node = nodem.Node('node1', self.profile.id, self.cluster.id,
                          self.context)
        self.assertEqual('', node.physical_id)
        res = node.do_delete(self.context)
        self.assertTrue(res)
        self.assertFalse(mock_delete.called)
        self.assertTrue(mock_db_delete.called)

    @mock.patch.object(eventm, 'info')
    @mock.patch.object(nodem.Node, '_handle_exception')
    @mock.patch.object(nodem.Node, 'set_status')
    @mock.patch.object(profiles_base.Profile, 'delete_object')
    def test_node_delete_resource_status_error(self, mock_delete, mock_status,
                                               mock_handle_exception,
                                               mock_event):
        ex = exception.ResourceStatusError(resource_id='id', status='ERROR',
                                           reason='some reason')
        mock_delete.side_effect = ex
        node = nodem.Node('node1', self.profile.id, self.cluster.id,
                          self.context)
        node.physical_id = 'fake_id'
        res = node.do_delete(self.context)
        self.assertFalse(res)
        mock_delete.assert_called_once_with(self.context, node)
        mock_handle_exception.assert_called_once_with(self.context, 'delete',
                                                      'ERROR', ex)
        mock_status.assert_any_call(self.context, 'ERROR',
                                    reason='Deletion failed')
        mock_event.assert_called_once_with(self.context, node, 'delete')

    @mock.patch.object(nodem.Node, 'set_status')
    @mock.patch.object(profiles_base.Profile, 'update_object')
    def test_node_update(self, mock_update, mock_status):
        node = nodem.Node('node1', self.profile.id, self.cluster.id,
                          self.context)
        new_profile = self._create_profile('NEW_PROFILE_ID')
        node.physical_id = 'fake_id'
        res = node.do_update(self.context, {'new_profile_id': new_profile.id})
        self.assertTrue(res)
        mock_update.assert_called_once_with(self.context, node,
                                            new_profile.id)
        self.assertEqual('NEW_PROFILE_ID', node.profile_id)
        self.assertEqual('NEW_PROFILE_ID', node.rt['profile'].id)
        mock_status.assert_any_call(self.context, 'UPDATING',
                                    reason='Update in progress')
        mock_status.assert_any_call(self.context, 'ACTIVE',
                                    reason='Update succeeded')

    def test_node_update_not_created(self):
        node = nodem.Node('node1', self.profile.id, self.cluster.id,
                          self.context)
        self.assertEqual('', node.physical_id)
        res = node.do_update(self.context, 'new_profile_id')
        self.assertFalse(res)

    @mock.patch.object(nodem.Node, '_handle_exception')
    @mock.patch.object(nodem.Node, 'set_status')
    @mock.patch.object(profiles_base.Profile, 'update_object')
    def test_node_update_resource_status_error(self, mock_update, mock_status,
                                               mock_handle_exception):
        node = nodem.Node('node1', self.profile.id, self.cluster.id,
                          self.context)
        ex = exception.ResourceStatusError(resource_id='id', status='ERROR',
                                           reason='some reason')
        mock_update.side_effect = ex
        new_profile = self._create_profile('NEW_PROFILE_ID')
        node.physical_id = 'fake_id'
        res = node.do_update(self.context, {'new_profile_id': new_profile.id})
        self.assertFalse(res)
        mock_handle_exception.assert_called_once_with(self.context, 'update',
                                                      'ERROR', ex)
        self.assertNotEqual('NEW_PROFILE_ID', node.profile_id)

    @mock.patch.object(db_api, 'node_migrate')
    def test_node_join_same_cluster(self, mock_migrate):
        node = nodem.Node('node1', self.profile.id, self.cluster.id,
                          self.context)
        node.index = 1
        res = node.do_join(self.context, self.cluster.id)
        self.assertTrue(res)
        self.assertEqual(1, node.index)
        self.assertIsNone(node.updated_time)
        self.assertFalse(mock_migrate.called)

    @mock.patch.object(timeutils, 'utcnow')
    @mock.patch.object(profiles_base.Profile, 'join_cluster')
    @mock.patch.object(db_api, 'node_migrate')
    def test_node_join(self, mock_migrate, mock_join_cluster, mock_time):
        node = nodem.Node('node1', self.profile.id, self.cluster.id,
                          self.context)
        res = node.do_join(self.context, 'NEW_CLUSTER_ID')
        self.assertTrue(res)
        mock_migrate.assert_called_once_with(self.context, node.id,
                                             'NEW_CLUSTER_ID', mock_time())
        mock_join_cluster.assert_called_once_with(self.context, node,
                                                  'NEW_CLUSTER_ID')
        self.assertEqual('NEW_CLUSTER_ID', node.cluster_id)
        self.assertEqual(mock_migrate.return_value.index, node.index)
        self.assertIsNotNone(node.updated_time)

    @mock.patch.object(db_api, 'node_migrate')
    def test_node_leave_no_cluster(self, mock_migrate):
        node = nodem.Node('node1', self.profile.id, None, self.context)
        self.assertTrue(node.do_leave(self.context))
        self.assertFalse(mock_migrate.called)
        self.assertIsNone(node.cluster_id)
        self.assertIsNone(node.updated_time)

    @mock.patch.object(timeutils, 'utcnow')
    @mock.patch.object(profiles_base.Profile, 'leave_cluster')
    @mock.patch.object(db_api, 'node_migrate')
    def test_node_leave(self, mock_migrate, mock_leave_cluster, mock_time):
        node = nodem.Node('node1', self.profile.id, self.cluster.id,
                          self.context)
        res = node.do_leave(self.context)
        self.assertTrue(res)
        self.assertIsNone(node.cluster_id)
        self.assertIsNotNone(node.updated_time)
        self.assertEqual(-1, node.index)
        mock_migrate.assert_called_once_with(self.context, node.id,
                                             None, mock_time())
        mock_leave_cluster.assert_called_once_with(self.context, node)
