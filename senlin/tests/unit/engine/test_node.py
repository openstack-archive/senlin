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

from senlin.common import exception
from senlin.common.i18n import _
from senlin.common import utils as common_utils
from senlin.engine import node as nodem
from senlin.objects import node as node_obj
from senlin.objects import profile as profile_obj
from senlin.profiles import base as profiles_base
from senlin.tests.unit.common import base
from senlin.tests.unit.common import utils

PROFILE_ID = 'aa5f86b8-e52b-4f2b-828a-4c14c770938d'
CLUSTER_ID = '2c5139a6-24ba-4a6f-bd53-a268f61536de'
NODE_ID = '60efdaa1-06c2-4fcf-ae44-17a2d85ff3ea'


class TestNode(base.SenlinTestCase):

    def setUp(self):
        super(TestNode, self).setUp()
        self.context = utils.dummy_context(project='node_test_project')
        self.profile = utils.create_profile(self.context, PROFILE_ID)
        self.cluster = utils.create_cluster(self.context, CLUSTER_ID,
                                            PROFILE_ID)

    def test_node_init(self):
        node = nodem.Node('node1', PROFILE_ID, CLUSTER_ID, role='first_node')
        self.assertIsNone(node.id)
        self.assertEqual('node1', node.name)
        self.assertIsNone(node.physical_id)
        self.assertEqual(PROFILE_ID, node.profile_id)
        self.assertEqual('', node.user)
        self.assertEqual('', node.project)
        self.assertEqual('', node.domain)
        self.assertEqual(CLUSTER_ID, node.cluster_id)
        self.assertEqual(-1, node.index)
        self.assertEqual('first_node', node.role)

        self.assertIsNone(node.init_at)
        self.assertIsNone(node.created_at)
        self.assertIsNone(node.updated_at)

        self.assertEqual('INIT', node.status)
        self.assertEqual('Initializing', node.status_reason)
        self.assertEqual({}, node.data)
        self.assertEqual({}, node.metadata)
        self.assertEqual({}, node.rt)

    def test_node_init_random_name(self):
        node = nodem.Node(None, PROFILE_ID, None)
        self.assertIsNotNone(node.name)
        self.assertEqual(13, len(node.name))

    def test_node_store_init(self):
        node = nodem.Node('node1', PROFILE_ID, CLUSTER_ID, self.context,
                          role='first_node', index=1)
        self.assertIsNone(node.id)
        node_id = node.store(self.context)
        self.assertIsNotNone(node_id)

        node_info = node_obj.Node.get(self.context, node_id)
        self.assertIsNotNone(node_info)
        self.assertEqual('node1', node_info.name)
        self.assertIsNone(node_info.physical_id)
        self.assertEqual(CLUSTER_ID, node_info.cluster_id)
        self.assertEqual(PROFILE_ID, node_info.profile_id)
        self.assertEqual(self.context.user, node_info.user)
        self.assertEqual(self.context.project, node_info.project)
        self.assertEqual(self.context.domain, node_info.domain)
        self.assertEqual(1, node_info.index)
        self.assertEqual('first_node', node.role)

        self.assertIsNotNone(node_info.init_at)
        self.assertIsNone(node_info.created_at)
        self.assertIsNone(node_info.updated_at)

        self.assertEqual('INIT', node_info.status)
        self.assertEqual('Initializing', node_info.status_reason)
        self.assertEqual({}, node_info.metadata)
        self.assertEqual({}, node_info.data)

    def test_node_store_update(self):
        node = nodem.Node('node1', PROFILE_ID, None)
        node_id = node.store(self.context)

        node.name = 'new_name'
        new_node_id = node.store(self.context)

        self.assertEqual(node_id, new_node_id)

    def test_node_load(self):
        ex = self.assertRaises(exception.NodeNotFound,
                               nodem.Node.load,
                               self.context, 'non-existent', None)
        self.assertEqual('The node (non-existent) could not be found.',
                         six.text_type(ex))

        x_node_id = 'ee96c490-2dee-40c8-8919-4c64b89e326c'
        node = utils.create_node(self.context, x_node_id, PROFILE_ID,
                                 CLUSTER_ID)
        node_info = nodem.Node.load(self.context, x_node_id)

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

        self.assertEqual(node.init_at, node_info.init_at)
        self.assertEqual(node.created_at, node_info.created_at)
        self.assertEqual(node.updated_at, node_info.updated_at)

        self.assertEqual(node.status, node_info.status)
        self.assertEqual(node.status_reason, node_info.status_reason)
        self.assertEqual(node.metadata, node_info.metadata)
        self.assertEqual(node.data, node_info.data)
        self.assertEqual(self.profile.name, node_info.rt['profile'].name)

    def test_node_load_diff_project(self):
        x_node_id = 'c06840c5-f4e4-49ae-8143-9da5b4c73f38'
        utils.create_node(self.context, x_node_id, PROFILE_ID, CLUSTER_ID)

        new_ctx = utils.dummy_context(project='a-different-project')
        ex = self.assertRaises(exception.NodeNotFound,
                               nodem.Node.load,
                               new_ctx, x_node_id, None)
        self.assertEqual('The node (%s) could not be found.' % x_node_id,
                         six.text_type(ex))

        res = nodem.Node.load(new_ctx, x_node_id, project_safe=False)
        self.assertIsNotNone(res)
        self.assertEqual(x_node_id, res.id)

    def test_node_load_all(self):
        node_info = nodem.Node.load_all(self.context)
        self.assertEqual([], [c for c in node_info])
        x_node_id1 = 'e7ec30c4-4dbf-45ac-a6b5-6c675c58d892'
        x_node_id2 = '9d87b415-a572-407f-ab55-21a0f0073ee4'

        utils.create_node(self.context, x_node_id1, PROFILE_ID, CLUSTER_ID)
        utils.create_node(self.context, x_node_id2, PROFILE_ID, CLUSTER_ID)

        # NOTE: we don't test all other parameters because the db api tests
        #       already covered that
        nodes = nodem.Node.load_all(self.context)
        self.assertEqual(2, len(nodes))
        self.assertEqual(x_node_id1, nodes[0].id)
        self.assertEqual(x_node_id2, nodes[1].id)

    def test_node_to_dict(self):
        x_node_id = '16e70db8-4f70-4883-96be-cf40264a5abd'
        node = utils.create_node(self.context, x_node_id, PROFILE_ID,
                                 CLUSTER_ID)
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
            'init_at': common_utils.isotime(node.init_at),
            'created_at': common_utils.isotime(node.created_at),
            'updated_at': common_utils.isotime(node.updated_at),
            'status': node.status,
            'status_reason': node.status_reason,
            'data': node.data,
            'metadata': node.metadata,
            'profile_name': self.profile.name,
        }
        result = nodem.Node.load(self.context, x_node_id)
        dt = result.to_dict()
        self.assertEqual(expected, dt)

    @mock.patch.object(profile_obj.Profile, 'get')
    def test_node_to_dict_no_profile(self, mock_profile_get):
        x_node_id = '11ad5c3d-e1e5-4ed8-8fe3-2938b63a11cb'
        node = utils.create_node(self.context, x_node_id, PROFILE_ID,
                                 CLUSTER_ID)
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
            'init_at': common_utils.isotime(node.init_at),
            'created_at': common_utils.isotime(node.created_at),
            'updated_at': common_utils.isotime(node.updated_at),
            'status': node.status,
            'status_reason': node.status_reason,
            'data': node.data,
            'metadata': node.metadata,
            'profile_name': 'Unknown',
        }
        mock_profile_get.return_value = None
        result = nodem.Node.load(self.context, x_node_id)
        dt = result.to_dict()
        self.assertEqual(expected, dt)

    def test_node_set_status(self):
        node = nodem.Node('node1', PROFILE_ID, CLUSTER_ID, self.context)
        node.store(self.context)
        self.assertEqual(nodem.Node.INIT, node.status)
        self.assertIsNotNone(node.init_at)
        self.assertIsNone(node.created_at)
        self.assertIsNone(node.updated_at)

        # create
        node.set_status(self.context, node.CREATING,
                        reason='Creation in progress')
        self.assertEqual('CREATING', node.status)
        self.assertEqual('Creation in progress', node.status_reason)
        self.assertIsNone(node.created_at)
        self.assertIsNone(node.updated_at)

        node.set_status(self.context, node.ACTIVE,
                        reason='Creation succeeded')
        self.assertEqual('ACTIVE', node.status)
        self.assertEqual('Creation succeeded', node.status_reason)
        self.assertIsNotNone(node.created_at)
        self.assertIsNone(node.updated_at)

        # update
        node.set_status(self.context, node.UPDATING,
                        reason='Update in progress')
        self.assertEqual('UPDATING', node.status)
        self.assertEqual('Update in progress', node.status_reason)
        self.assertIsNotNone(node.created_at)
        self.assertIsNone(node.updated_at)

        node.set_status(self.context, node.ACTIVE,
                        reason='Update succeeded')
        self.assertEqual('ACTIVE', node.status)
        self.assertEqual('Update succeeded', node.status_reason)
        self.assertIsNotNone(node.created_at)
        self.assertIsNotNone(node.updated_at)

        node.set_status(self.context, node.ACTIVE)
        self.assertEqual('ACTIVE', node.status)
        self.assertIsNotNone(node.created_at)
        self.assertIsNotNone(node.updated_at)

        # delete
        node.set_status(self.context, node.DELETING,
                        reason='Deletion in progress')
        self.assertEqual('DELETING', node.status)
        self.assertEqual('Deletion in progress', node.status_reason)
        self.assertIsNotNone(node.created_at)

    @mock.patch.object(profiles_base.Profile, 'get_details')
    def test_node_get_details(self, mock_details):
        node = nodem.Node('node1', CLUSTER_ID, None)
        for physical_id in (None, ''):
            node.physical_id = physical_id
            self.assertEqual({}, node.get_details(self.context))
            self.assertEqual(0, mock_details.call_count)

        fake_id = 'd94d6333-82e6-4f87-b7ab-b786776df9d1'
        node.physical_id = fake_id
        mock_details.return_value = {'foo': 'bar'}
        res = node.get_details(self.context)
        mock_details.assert_called_once_with(self.context, node)
        self.assertEqual({'foo': 'bar'}, res)

    def test_node_handle_exception(self):
        fake_id = 'd94d6333-82e6-4f87-b7ab-b786776df9d1'
        ex = exception.ResourceStatusError(resource_id=fake_id,
                                           status='FAKE_STATUS',
                                           reason='FAKE_REASON')
        node = nodem.Node('node1', PROFILE_ID, None, self.context)
        node.store(self.context)
        node._handle_exception(self.context, 'ACTION', 'STATUS', ex)
        db_node = node_obj.Node.get(self.context, node.id)
        self.assertEqual(node.ERROR, db_node.status)
        self.assertEqual('Profile failed in ACTIOing resource '
                         '(%s) due to: %s' % (fake_id, six.text_type(ex)),
                         db_node.status_reason)
        self.assertEqual(fake_id, db_node.physical_id)

        # Exception happens before physical node creation started.
        ex = exception.ResourceCreationFailure(rtype='stack',
                                               code=400,
                                               message='Bad request')
        node = nodem.Node('node1', PROFILE_ID, None, self.context)
        node.store(self.context)
        node._handle_exception(self.context, 'CREATE', 'STATUS', ex)
        db_node = node_obj.Node.get(self.context, node.id)
        self.assertEqual(node.ERROR, db_node.status)
        self.assertEqual('Profile failed in creating node due to: '
                         '%s' % six.text_type(ex), db_node.status_reason)
        self.assertIsNone(db_node.physical_id)

    @mock.patch.object(nodem.Node, 'store')
    @mock.patch.object(nodem.Node, 'set_status')
    @mock.patch.object(profiles_base.Profile, 'create_object')
    def test_node_create(self, mock_create, mock_status, mock_store):
        node = nodem.Node('node1', PROFILE_ID, CLUSTER_ID, self.context)
        physical_id = 'd94d6333-82e6-4f87-b7ab-b786776df9d1'
        mock_create.return_value = physical_id
        res = node.do_create(self.context)
        self.assertTrue(res)
        mock_status.assert_any_call(self.context, node.CREATING,
                                    reason='Creation in progress')
        mock_status.assert_any_call(self.context, node.ACTIVE,
                                    'Creation succeeded')
        mock_store.assert_called_once_with(self.context)
        self.assertEqual(physical_id, node.physical_id)

    def test_node_create_not_init(self):
        node = nodem.Node('node1', PROFILE_ID, CLUSTER_ID, self.context)
        node.status = 'NOT_INIT'
        res = node.do_create(self.context)
        self.assertFalse(res)

    @mock.patch.object(nodem.Node, 'set_status')
    @mock.patch.object(profiles_base.Profile, 'create_object')
    def test_node_create_not_created(self, mock_create, mock_status):

        node = nodem.Node('node1', PROFILE_ID, CLUSTER_ID, self.context)
        mock_create.return_value = None
        res = node.do_create(self.context)
        self.assertFalse(res)
        mock_status.assert_called_once_with(self.context, node.CREATING,
                                            reason='Creation in progress')

    @mock.patch.object(nodem.Node, 'store')
    @mock.patch.object(nodem.Node, 'set_status')
    @mock.patch.object(profiles_base.Profile, 'create_object')
    def test_node_create_internal_error(self, mock_create, mock_status,
                                        mock_store):
        ex = exception.InternalError(code=500, message='internal error')
        mock_create.side_effect = ex
        node = nodem.Node('node1', PROFILE_ID, CLUSTER_ID, self.context)
        res = node.do_create(self.context)
        self.assertFalse(res)
        mock_status.assert_any_call(self.context, node.CREATING,
                                    reason='Creation in progress')
        reason = _('Profile failed in creating node due to: %(msg)s') % {
            'msg': six.text_type(ex)}
        mock_status.assert_any_call(self.context, node.ERROR, reason)

    @mock.patch.object(node_obj.Node, 'delete')
    @mock.patch.object(nodem.Node, 'set_status')
    @mock.patch.object(profiles_base.Profile, 'delete_object')
    def test_node_delete(self, mock_delete, mock_status, mock_db_delete):
        node = nodem.Node('node1', PROFILE_ID, CLUSTER_ID, self.context)
        node.physical_id = 'd94d6333-82e6-4f87-b7ab-b786776df9d1'
        node.id = NODE_ID
        res = node.do_delete(self.context)
        self.assertTrue(res)
        mock_delete.assert_called_once_with(mock.ANY, node)
        mock_db_delete.assert_called_once_with(mock.ANY, node.id)
        mock_status.assert_called_once_with(self.context, node.DELETING,
                                            reason='Deletion in progress')

    @mock.patch.object(node_obj.Node, 'delete')
    @mock.patch.object(profiles_base.Profile, 'delete_object')
    def test_node_delete_not_created(self, mock_delete, mock_db_delete):
        node = nodem.Node('node1', PROFILE_ID, CLUSTER_ID, self.context)
        self.assertIsNone(node.physical_id)
        res = node.do_delete(self.context)
        self.assertTrue(res)
        self.assertFalse(mock_delete.called)
        self.assertTrue(mock_db_delete.called)

    @mock.patch.object(nodem.Node, '_handle_exception')
    @mock.patch.object(nodem.Node, 'set_status')
    @mock.patch.object(profiles_base.Profile, 'delete_object')
    def test_node_delete_resource_status_error(self, mock_delete, mock_status,
                                               mock_handle_exception):
        ex = exception.ResourceStatusError(resource_id='id', status='ERROR',
                                           reason='some reason')
        mock_delete.side_effect = ex
        node = nodem.Node('node1', PROFILE_ID, CLUSTER_ID, self.context)
        node.physical_id = 'd94d6333-82e6-4f87-b7ab-b786776df9d1'
        res = node.do_delete(self.context)
        self.assertFalse(res)
        mock_delete.assert_called_once_with(self.context, node)
        mock_handle_exception.assert_called_once_with(self.context, 'delete',
                                                      'ERROR', ex)
        mock_status.assert_any_call(self.context, 'ERROR',
                                    reason='Deletion failed')

    @mock.patch.object(nodem.Node, 'set_status')
    @mock.patch.object(profiles_base.Profile, 'update_object')
    def test_node_update_new_profile(self, mock_update, mock_status):
        node = nodem.Node('node1', PROFILE_ID, CLUSTER_ID, self.context)
        new_id = '71d8f4dd-1ef9-4308-b7ae-03298b04449e'
        new_profile = utils.create_profile(self.context, new_id)
        node.physical_id = 'd94d6333-82e6-4f87-b7ab-b786776df9d1'
        res = node.do_update(self.context, {'new_profile_id': new_profile.id})
        self.assertTrue(res)
        mock_update.assert_called_once_with(self.context, node,
                                            new_profile.id)
        self.assertEqual(new_id, node.profile_id)
        self.assertEqual(new_id, node.rt['profile'].id)
        mock_status.assert_any_call(self.context, 'UPDATING',
                                    reason='Update in progress')
        mock_status.assert_any_call(self.context, 'ACTIVE',
                                    reason='Update succeeded')

    @mock.patch.object(nodem.Node, 'set_status')
    def test_node_update_name(self, mock_status):
        node = nodem.Node('node1', PROFILE_ID, CLUSTER_ID, self.context)
        node.physical_id = 'd94d6333-82e6-4f87-b7ab-b786776df9d1'
        res = node.do_update(self.context, {'name': 'new_name'})
        self.assertTrue(res)
        self.assertEqual(node.name, 'new_name')
        mock_status.assert_any_call(self.context, 'UPDATING',
                                    reason='Update in progress')
        mock_status.assert_any_call(self.context, 'ACTIVE',
                                    reason='Update succeeded')

    def test_node_update_not_created(self):
        node = nodem.Node('node1', PROFILE_ID, CLUSTER_ID, self.context)
        self.assertIsNone(node.physical_id)
        new_profile_id = '71d8f4dd-1ef9-4308-b7ae-03298b04449e'
        res = node.do_update(self.context, new_profile_id)
        self.assertFalse(res)

    @mock.patch.object(nodem.Node, '_handle_exception')
    @mock.patch.object(nodem.Node, 'set_status')
    @mock.patch.object(profiles_base.Profile, 'update_object')
    def test_node_update_resource_status_error(self, mock_update, mock_status,
                                               mock_handle_exception):
        node = nodem.Node('node1', PROFILE_ID, CLUSTER_ID, self.context)
        ex = exception.ResourceStatusError(resource_id='id', status='ERROR',
                                           reason='some reason')
        mock_update.side_effect = ex
        new_id = '71d8f4dd-1ef9-4308-b7ae-03298b04449e'
        new_profile = utils.create_profile(self.context, new_id)
        node.physical_id = 'd94d6333-82e6-4f87-b7ab-b786776df9d1'
        res = node.do_update(self.context, {'new_profile_id': new_profile.id})
        self.assertFalse(res)
        mock_handle_exception.assert_called_once_with(self.context, 'update',
                                                      'ERROR', ex)
        self.assertNotEqual(new_id, node.profile_id)

    @mock.patch.object(node_obj.Node, 'migrate')
    def test_node_join_same_cluster(self, mock_migrate):
        node = nodem.Node('node1', PROFILE_ID, CLUSTER_ID, self.context)
        node.index = 1
        res = node.do_join(self.context, CLUSTER_ID)
        self.assertTrue(res)
        self.assertEqual(1, node.index)
        self.assertIsNone(node.updated_at)
        self.assertFalse(mock_migrate.called)

    @mock.patch.object(profiles_base.Profile, 'join_cluster')
    @mock.patch.object(node_obj.Node, 'migrate')
    def test_node_join(self, mock_migrate, mock_join_cluster):
        node = nodem.Node('node1', PROFILE_ID, CLUSTER_ID, self.context)
        mock_join_cluster.return_value = True
        cluster_id = 'fb8bca7a-a82b-4442-a40f-92d3e3cfb0b9'
        res = node.do_join(self.context, cluster_id)
        self.assertTrue(res)
        mock_migrate.assert_called_once_with(self.context, node.id,
                                             cluster_id, mock.ANY)
        mock_join_cluster.assert_called_once_with(self.context, node,
                                                  cluster_id)
        self.assertEqual(cluster_id, node.cluster_id)
        self.assertEqual(mock_migrate.return_value.index, node.index)
        self.assertIsNotNone(node.updated_at)

    @mock.patch.object(profiles_base.Profile, 'join_cluster')
    def test_node_join_fail_update_server_metadata(self, mock_join):
        node = nodem.Node('node1', PROFILE_ID, None, self.context)
        mock_join.return_value = False
        cluster_id = 'fb8bca7a-a82b-4442-a40f-92d3e3cfb0b9'
        res = node.do_join(self.context, cluster_id)
        self.assertFalse(res)
        self.assertEqual('', node.cluster_id)
        self.assertEqual(-1, node.index)
        self.assertIsNone(node.updated_at)
        mock_join.assert_called_once_with(self.context, node, cluster_id)

    @mock.patch.object(node_obj.Node, 'migrate')
    def test_node_leave_no_cluster(self, mock_migrate):
        node = nodem.Node('node1', PROFILE_ID, '', self.context)
        self.assertTrue(node.do_leave(self.context))
        self.assertFalse(mock_migrate.called)
        self.assertEqual('', node.cluster_id)
        self.assertIsNone(node.updated_at)

    @mock.patch.object(profiles_base.Profile, 'leave_cluster')
    @mock.patch.object(node_obj.Node, 'migrate')
    def test_node_leave(self, mock_migrate, mock_leave_cluster):
        node = nodem.Node('node1', PROFILE_ID, CLUSTER_ID, self.context)
        mock_leave_cluster.return_value = True
        res = node.do_leave(self.context)
        self.assertTrue(res)
        self.assertEqual('', node.cluster_id)
        self.assertIsNotNone(node.updated_at)
        self.assertEqual(-1, node.index)
        mock_migrate.assert_called_once_with(self.context, node.id,
                                             None, mock.ANY)
        mock_leave_cluster.assert_called_once_with(self.context, node)

    @mock.patch.object(profiles_base.Profile, 'leave_cluster')
    def test_node_leave_fail_update_server_metadata(self, mock_leave):
        node = nodem.Node('node1', PROFILE_ID, CLUSTER_ID, self.context,
                          index=1)
        mock_leave.return_value = False
        res = node.do_leave(self.context)
        self.assertFalse(res)
        self.assertNotEqual('', node.cluster_id)
        self.assertIsNone(node.updated_at)
        self.assertEqual(1, node.index)

    @mock.patch.object(profiles_base.Profile, 'check_object')
    def test_node_check(self, mock_check):
        node = nodem.Node('node1', PROFILE_ID, '')
        node.physical_id = 'd94d6333-82e6-4f87-b7ab-b786776df9d1'
        mock_check.return_value = True

        res = node.do_check(self.context)

        self.assertTrue(res)
        mock_check.assert_called_once_with(self.context, node)

    @mock.patch.object(nodem.Node, 'store')
    @mock.patch.object(profiles_base.Profile, 'check_object')
    def test_node_check_failed_check(self, mock_check, mock_store):
        node = nodem.Node('node1', PROFILE_ID, '')
        node.physical_id = 'd94d6333-82e6-4f87-b7ab-b786776df9d1'
        mock_check.return_value = False

        res = node.do_check(self.context)

        self.assertFalse(res)
        self.assertEqual('ERROR', node.status)

    def test_node_check_no_physical_id(self):
        node = nodem.Node('node1', PROFILE_ID, '')

        res = node.do_check(self.context)

        self.assertFalse(res)

    @mock.patch.object(nodem.Node, 'set_status')
    @mock.patch.object(profiles_base.Profile, 'recover_object')
    def test_node_recover_new_object(self, mock_recover, mock_status):
        node = nodem.Node('node1', PROFILE_ID, '')
        node.physical_id = 'd94d6333-82e6-4f87-b7ab-b786776df9d1'
        new_id = '166db83b-b4a4-49ef-96a8-6c0fdd882d1a'
        mock_recover.return_value = new_id

        res = node.do_recover(self.context)

        self.assertTrue(res)
        mock_recover.assert_called_once_with(self.context, node)
        self.assertEqual('node1', node.name)
        self.assertEqual(new_id, node.physical_id)
        self.assertEqual(PROFILE_ID, node.profile_id)
        mock_status.assert_has_calls([
            mock.call(self.context, 'RECOVERING',
                      reason='Recover in progress'),
            mock.call(self.context, node.ACTIVE,
                      reason='Recover succeeded')])

    @mock.patch.object(nodem.Node, 'set_status')
    @mock.patch.object(profiles_base.Profile, 'recover_object')
    def test_node_recover_in_place(self, mock_recover, mock_status):
        node = nodem.Node('node1', PROFILE_ID, None)
        node.physical_id = 'd94d6333-82e6-4f87-b7ab-b786776df9d1'
        new_id = '166db83b-b4a4-49ef-96a8-6c0fdd882d1a'
        mock_recover.return_value = new_id

        res = node.do_recover(self.context)

        self.assertTrue(res)
        mock_recover.assert_called_once_with(self.context, node)
        self.assertEqual('node1', node.name)
        self.assertEqual(new_id, node.physical_id)
        self.assertEqual(PROFILE_ID, node.profile_id)
        mock_status.assert_has_calls([
            mock.call(self.context, 'RECOVERING',
                      reason='Recover in progress'),
            mock.call(self.context, node.ACTIVE,
                      reason='Recover succeeded')])

    @mock.patch.object(nodem.Node, 'set_status')
    @mock.patch.object(profiles_base.Profile, 'recover_object')
    def test_node_recover_failed_recover(self, mock_recover, mock_status):
        node = nodem.Node('node1', PROFILE_ID, None)
        node.physical_id = 'd94d6333-82e6-4f87-b7ab-b786776df9d1'
        mock_recover.return_value = None

        res = node.do_recover(self.context)

        self.assertFalse(res)
        mock_status.assert_has_calls([
            mock.call(self.context, 'RECOVERING',
                      reason='Recover in progress'),
            mock.call(self.context, node.ERROR,
                      reason='Recover failed')])

    def test_node_recover_no_physical_id(self):
        node = nodem.Node('node1', PROFILE_ID, None)

        res = node.do_recover(self.context)

        self.assertFalse(res)

    @mock.patch.object(nodem.Node, 'set_status')
    def test_node_recover_operation_not_support(self, mock_set_status):
        node = nodem.Node('node1', PROFILE_ID, None)
        node.physical_id = 'd94d6333-82e6-4f87-b7ab-b786776df9d1'

        params = {'operation': 'foo'}
        res = node.do_recover(self.context, **params)

        self.assertFalse(res)
