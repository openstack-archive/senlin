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
from oslo_serialization import jsonutils
from oslo_utils import uuidutils
import six

from senlin.common import consts
from senlin.common import exception
from senlin.engine import node as nodem
from senlin.objects import node as node_obj
from senlin.profiles import base as pb
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
        self.assertEqual(self.context.user_id, node_info.user)
        self.assertEqual(self.context.project_id, node_info.project)
        self.assertEqual(self.context.domain_id, node_info.domain)
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
        node = nodem.Node('node1', PROFILE_ID, "", user=self.context.user_id,
                          project=self.context.project_id)
        node_id = node.store(self.context)

        node.name = 'new_name'
        new_node_id = node.store(self.context)

        self.assertEqual(node_id, new_node_id)

    def test_node_load(self):
        ex = self.assertRaises(exception.ResourceNotFound,
                               nodem.Node.load,
                               self.context, 'non-existent', None)
        self.assertEqual("The node 'non-existent' could not be found.",
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
        ex = self.assertRaises(exception.ResourceNotFound,
                               nodem.Node.load,
                               new_ctx, x_node_id, None)
        self.assertEqual("The node '%s' could not be found." % x_node_id,
                         six.text_type(ex))

        res = nodem.Node.load(new_ctx, x_node_id, project_safe=False)
        self.assertIsNotNone(res)
        self.assertEqual(x_node_id, res.id)

    @mock.patch.object(nodem.Node, '_from_object')
    @mock.patch.object(node_obj.Node, 'get_all')
    def test_node_load_all(self, mock_get, mock_init):
        x_obj_1 = mock.Mock()
        x_obj_2 = mock.Mock()
        mock_get.return_value = [x_obj_1, x_obj_2]

        x_node_1 = mock.Mock()
        x_node_2 = mock.Mock()
        mock_init.side_effect = [x_node_1, x_node_2]

        result = nodem.Node.load_all(self.context)

        self.assertEqual([x_node_1, x_node_2], [n for n in result])
        mock_get.assert_called_once_with(self.context, cluster_id=None,
                                         limit=None, marker=None,
                                         sort=None, filters=None,
                                         project_safe=True)
        mock_init.assert_has_calls([
            mock.call(self.context, x_obj_1),
            mock.call(self.context, x_obj_2)])

    def test_node_set_status(self):
        node = nodem.Node('node1', PROFILE_ID, CLUSTER_ID, self.context)
        node.store(self.context)
        self.assertEqual(nodem.consts.NS_INIT, node.status)
        self.assertIsNotNone(node.init_at)
        self.assertIsNone(node.created_at)
        self.assertIsNone(node.updated_at)

        # create
        node.set_status(self.context, consts.NS_CREATING,
                        reason='Creation in progress')
        self.assertEqual('CREATING', node.status)
        self.assertEqual('Creation in progress', node.status_reason)
        self.assertIsNone(node.created_at)
        self.assertIsNone(node.updated_at)

        node.set_status(self.context, consts.NS_ACTIVE,
                        reason='Creation succeeded')
        self.assertEqual('ACTIVE', node.status)
        self.assertEqual('Creation succeeded', node.status_reason)
        self.assertIsNotNone(node.created_at)
        self.assertIsNotNone(node.updated_at)

        # update
        node.set_status(self.context, consts.NS_UPDATING,
                        reason='Update in progress')
        self.assertEqual('UPDATING', node.status)
        self.assertEqual('Update in progress', node.status_reason)
        self.assertIsNotNone(node.created_at)

        node.set_status(self.context, consts.NS_ACTIVE,
                        reason='Update succeeded')
        self.assertEqual('ACTIVE', node.status)
        self.assertEqual('Update succeeded', node.status_reason)
        self.assertIsNotNone(node.created_at)
        self.assertIsNotNone(node.updated_at)

        node.set_status(self.context, consts.NS_ACTIVE)
        self.assertEqual('ACTIVE', node.status)
        self.assertIsNotNone(node.created_at)
        self.assertIsNotNone(node.updated_at)

        # delete
        node.set_status(self.context, consts.NS_DELETING,
                        reason='Deletion in progress')
        self.assertEqual('DELETING', node.status)
        self.assertEqual('Deletion in progress', node.status_reason)
        self.assertIsNotNone(node.created_at)

    @mock.patch.object(pb.Profile, 'get_details')
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

    @mock.patch.object(nodem.Node, 'set_status')
    @mock.patch.object(pb.Profile, 'create_object')
    def test_node_create(self, mock_create, mock_status):
        node = nodem.Node('node1', PROFILE_ID, CLUSTER_ID, self.context)
        physical_id = 'd94d6333-82e6-4f87-b7ab-b786776df9d1'
        mock_create.return_value = physical_id
        res = node.do_create(self.context)
        self.assertTrue(res)
        mock_status.assert_any_call(self.context, consts.NS_CREATING,
                                    'Creation in progress')
        mock_status.assert_any_call(self.context, consts.NS_ACTIVE,
                                    'Creation succeeded',
                                    physical_id=physical_id)

    def test_node_create_not_init(self):
        node = nodem.Node('node1', PROFILE_ID, CLUSTER_ID, self.context)
        node.status = 'NOT_INIT'
        res = node.do_create(self.context)
        self.assertFalse(res)

    @mock.patch.object(nodem.Node, 'set_status')
    @mock.patch.object(pb.Profile, 'create_object')
    def test_node_create_not_created(self, mock_create, mock_status):

        node = nodem.Node('node1', PROFILE_ID, CLUSTER_ID, self.context)
        mock_create.side_effect = exception.EResourceCreation(
            type='PROFILE', message='Boom', resource_id='test_id')

        res = node.do_create(self.context)

        self.assertFalse(res)
        mock_status.assert_any_call(self.context, consts.NS_CREATING,
                                    'Creation in progress')
        mock_status.assert_any_call(self.context, consts.NS_ERROR,
                                    'Failed in creating PROFILE: Boom.',
                                    physical_id='test_id')

    @mock.patch.object(node_obj.Node, 'delete')
    @mock.patch.object(nodem.Node, 'set_status')
    @mock.patch.object(pb.Profile, 'delete_object')
    def test_node_delete(self, mock_delete, mock_status, mock_db_delete):
        node = nodem.Node('node1', PROFILE_ID, CLUSTER_ID, self.context)
        node.physical_id = uuidutils.generate_uuid()
        node.id = uuidutils.generate_uuid()
        mock_db_delete.return_value = True

        res = node.do_delete(self.context)

        self.assertTrue(res)
        mock_delete.assert_called_once_with(self.context, node)
        mock_db_delete.assert_called_once_with(self.context, node.id)
        mock_status.assert_called_once_with(self.context, consts.NS_DELETING,
                                            'Deletion in progress')

    @mock.patch.object(node_obj.Node, 'delete')
    @mock.patch.object(nodem.Node, 'set_status')
    @mock.patch.object(pb.Profile, 'delete_object')
    def test_node_delete_no_physical_id(self, mock_delete, mock_status,
                                        mock_db_delete):
        node = nodem.Node('node1', PROFILE_ID, CLUSTER_ID, self.context)
        node.id = uuidutils.generate_uuid()
        self.assertIsNone(node.physical_id)
        mock_db_delete.return_value = True

        res = node.do_delete(self.context)

        self.assertTrue(res)
        mock_status.assert_called_once_with(self.context, consts.NS_DELETING,
                                            "Deletion in progress")
        self.assertTrue(mock_delete.called)
        mock_db_delete.assert_called_once_with(self.context, node.id)

    @mock.patch.object(nodem.Node, 'set_status')
    @mock.patch.object(pb.Profile, 'delete_object')
    def test_node_delete_EResourceDeletion(self, mock_delete, mock_status):
        ex = exception.EResourceDeletion(type='PROFILE', id='NODE_ID',
                                         message='Too Bad')
        mock_delete.side_effect = ex
        node = nodem.Node('node1', PROFILE_ID, CLUSTER_ID, self.context)
        node.physical_id = uuidutils.generate_uuid()

        res = node.do_delete(self.context)

        self.assertFalse(res)
        mock_delete.assert_called_once_with(self.context, node)
        mock_status.assert_has_calls([
            mock.call(self.context, consts.NS_DELETING,
                      "Deletion in progress"),
            mock.call(self.context, consts.NS_ERROR,
                      "Failed in deleting PROFILE 'NODE_ID': Too Bad.")
        ])

    @mock.patch.object(node_obj.Node, 'update')
    @mock.patch.object(pb.Profile, 'update_object')
    def test_node_update_new_profile(self, mock_update, mock_db):
        node = nodem.Node('node1', PROFILE_ID, CLUSTER_ID, self.context,
                          physical_id=uuidutils.generate_uuid())
        node.id = node.store(self.context)
        new_id = uuidutils.generate_uuid()
        utils.create_profile(self.context, new_id)
        mock_update.return_value = True

        res = node.do_update(self.context, {'new_profile_id': new_id})

        self.assertTrue(res)
        mock_update.assert_called_once_with(self.context, node, new_id)
        self.assertEqual(new_id, node.profile_id)
        self.assertEqual(new_id, node.rt['profile'].id)
        mock_db.assert_has_calls([
            mock.call(self.context, node.id,
                      {'status': consts.NS_UPDATING,
                       'status_reason': 'Update in progress'}),
            mock.call(self.context, node.id,
                      {'status': consts.NS_ACTIVE,
                       'status_reason': 'Update succeeded',
                       'profile_id': new_id,
                       'updated_at': mock.ANY})
        ])

    @mock.patch.object(pb.Profile, 'update_object')
    @mock.patch.object(node_obj.Node, 'update')
    def test_node_update_name(self, mock_db, mock_update):
        node = nodem.Node('node1', PROFILE_ID, CLUSTER_ID, self.context)
        node.store(self.context)

        physical_id = uuidutils.generate_uuid()
        node.physical_id = physical_id

        res = node.do_update(self.context, {'name': 'new_name',
                                            'role': 'new_role',
                                            'metadata': {'k': {'m': 'v'}},
                                            'bogus': 'foo'})

        self.assertTrue(res)
        self.assertEqual('new_name', node.name)
        mock_db.assert_has_calls([
            mock.call(self.context, node.id,
                      {'status': 'UPDATING',
                       'status_reason': 'Update in progress'}),
            mock.call(self.context, node.id,
                      {'status': 'ACTIVE',
                       'status_reason': 'Update succeeded',
                       'name': 'new_name',
                       'role': 'new_role',
                       'metadata': {'k': {'m': 'v'}},
                       'updated_at': mock.ANY})
        ])
        self.assertEqual(0, mock_update.call_count)

    def test_node_update_not_created(self):
        node = nodem.Node('node1', PROFILE_ID, CLUSTER_ID, self.context)
        self.assertIsNone(node.physical_id)
        new_profile_id = '71d8f4dd-1ef9-4308-b7ae-03298b04449e'
        res = node.do_update(self.context, new_profile_id)
        self.assertFalse(res)

    @mock.patch.object(pb.Profile, 'update_object')
    @mock.patch.object(node_obj.Node, 'update')
    def test_node_update_EResourceUpdate(self, mock_db, mock_update):
        node = nodem.Node('node1', PROFILE_ID, CLUSTER_ID, self.context)
        node.physical_id = uuidutils.generate_uuid()
        node.id = uuidutils.generate_uuid()

        ex = exception.EResourceUpdate(type='PROFILE', id='ID',
                                       message='reason')
        mock_update.side_effect = ex
        new_id = uuidutils.generate_uuid()
        utils.create_profile(self.context, new_id)

        res = node.do_update(self.context, {'new_profile_id': new_id})

        self.assertFalse(res)
        self.assertNotEqual(new_id, node.profile_id)
        mock_db.assert_has_calls([
            mock.call(
                self.context, node.id,
                {"status": "UPDATING", "status_reason": "Update in progress"}
            ),
            mock.call(
                self.context, node.id,
                {"status": "ERROR",
                 "status_reason": "Failed in updating PROFILE 'ID': reason.",
                 "updated_at": mock.ANY}
            )
        ])
        self.assertEqual(1, mock_update.call_count)

    @mock.patch.object(node_obj.Node, 'migrate')
    def test_node_join_same_cluster(self, mock_migrate):
        node = nodem.Node('node1', PROFILE_ID, CLUSTER_ID, self.context)
        node.index = 1
        res = node.do_join(self.context, CLUSTER_ID)
        self.assertTrue(res)
        self.assertEqual(1, node.index)
        self.assertIsNone(node.updated_at)
        self.assertFalse(mock_migrate.called)

    @mock.patch.object(pb.Profile, 'join_cluster')
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

    @mock.patch.object(node_obj.Node, 'migrate')
    @mock.patch.object(pb.Profile, 'join_cluster')
    def test_node_join_fail_profile_call(self, mock_join, mock_migrate):
        node = nodem.Node('node1', PROFILE_ID, None, self.context)
        node.id = uuidutils.generate_uuid()
        mock_join.return_value = False
        cluster_id = 'fb8bca7a-a82b-4442-a40f-92d3e3cfb0b9'

        res = node.do_join(self.context, cluster_id)

        self.assertFalse(res)
        mock_join.assert_called_once_with(self.context, node, cluster_id)
        mock_migrate.assert_has_calls([
            mock.call(self.context, node.id, cluster_id, mock.ANY),
            mock.call(self.context, node.id, None, mock.ANY),
        ])
        self.assertEqual('', node.cluster_id)
        self.assertEqual(-1, node.index)

    @mock.patch.object(node_obj.Node, 'migrate')
    def test_node_leave_no_cluster(self, mock_migrate):
        node = nodem.Node('node1', PROFILE_ID, '', self.context)
        self.assertTrue(node.do_leave(self.context))
        self.assertFalse(mock_migrate.called)
        self.assertEqual('', node.cluster_id)
        self.assertIsNone(node.updated_at)

    @mock.patch.object(pb.Profile, 'leave_cluster')
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

    @mock.patch.object(pb.Profile, 'leave_cluster')
    def test_node_leave_fail_update_server_metadata(self, mock_leave):
        node = nodem.Node('node1', PROFILE_ID, CLUSTER_ID, self.context,
                          index=1)
        mock_leave.return_value = False
        res = node.do_leave(self.context)
        self.assertFalse(res)
        self.assertNotEqual('', node.cluster_id)
        self.assertIsNone(node.updated_at)
        self.assertEqual(1, node.index)

    @mock.patch.object(nodem.Node, 'set_status')
    @mock.patch.object(pb.Profile, 'check_object')
    def test_node_check(self, mock_check, mock_status):
        node = nodem.Node('node1', PROFILE_ID, '')
        node.status = consts.NS_ACTIVE
        node.physical_id = 'd94d6333-82e6-4f87-b7ab-b786776df9d1'
        mock_check.return_value = True
        res = node.do_check(self.context)

        self.assertTrue(res)
        mock_check.assert_called_once_with(self.context, node)
        mock_status.assert_called_once_with(self.context, consts.NS_ACTIVE,
                                            'Check: Node is ACTIVE.')

    @mock.patch.object(nodem.Node, 'set_status')
    @mock.patch.object(pb.Profile, 'check_object')
    def test_node_check_warning(self, mock_check, mock_status):
        node = nodem.Node('node1', PROFILE_ID, '')
        node.status = consts.NS_WARNING
        node.status_reason = 'bad news'
        node.physical_id = 'd94d6333-82e6-4f87-b7ab-b786776df9d1'
        mock_check.return_value = True

        res = node.do_check(self.context)

        self.assertTrue(res)
        mock_check.assert_called_once_with(self.context, node)
        msg = ("Check: Physical object is ACTIVE but the node status was "
               "WARNING. %s") % node.status_reason
        mock_status.assert_called_once_with(self.context, consts.NS_WARNING,
                                            msg)

    @mock.patch.object(nodem.Node, 'set_status')
    @mock.patch.object(pb.Profile, 'check_object')
    def test_node_check_not_active(self, mock_check, mock_status):
        node = nodem.Node('node1', PROFILE_ID, '')
        node.status = consts.NS_WARNING
        node.physical_id = 'd94d6333-82e6-4f87-b7ab-b786776df9d1'
        mock_check.return_value = False

        res = node.do_check(self.context)

        self.assertTrue(res)
        mock_status.assert_called_once_with(self.context, consts.NS_ERROR,
                                            'Check: Node is not ACTIVE.')

    @mock.patch.object(nodem.Node, 'set_status')
    @mock.patch.object(pb.Profile, 'check_object')
    def test_node_check_check_with_exc(self, mock_check, mock_status):
        node = nodem.Node('node1', PROFILE_ID, '')
        node.physical_id = 'd94d6333-82e6-4f87-b7ab-b786776df9d1'
        err = exception.EResourceOperation(op='checking', type='server',
                                           id=node.physical_id,
                                           message='failed get')
        mock_check.side_effect = err

        res = node.do_check(self.context)

        self.assertFalse(res)
        mock_status.assert_called_once_with(
            self.context,
            consts.NS_ERROR,
            "Failed in checking server '%s': failed get." % node.physical_id)

    def test_node_check_no_physical_id(self):
        node = nodem.Node('node1', PROFILE_ID, '')

        res = node.do_check(self.context)

        self.assertFalse(res)

    @mock.patch.object(nodem.Node, 'set_status')
    @mock.patch.object(pb.Profile, 'check_object')
    def test_node_check_no_server(self, mock_check, mock_status):
        node = nodem.Node('node1', PROFILE_ID, '')
        node.physical_id = 'd94d6333-82e6-4f87-b7ab-b786776df9d1'

        err = exception.EServerNotFound(type='server',
                                        id=node.physical_id,
                                        message='No Server found')
        mock_check.side_effect = err

        res = node.do_check(self.context)

        self.assertTrue(res)
        mock_status.assert_called_once_with(
            self.context, consts.NS_ERROR,
            "Failed in found server '%s': No Server found."
            % node.physical_id,
            physical_id=None)

    @mock.patch.object(nodem.Node, 'set_status')
    @mock.patch.object(pb.Profile, 'recover_object')
    def test_node_recover_new_object(self, mock_recover, mock_status):
        def set_status(*args, **kwargs):
            if args[1] == 'ACTIVE':
                node.physical_id = new_id
                node.data = {'recovery': 'RECREATE'}

        node = nodem.Node('node1', PROFILE_ID, '')
        node.physical_id = 'd94d6333-82e6-4f87-b7ab-b786776df9d1'
        new_id = '166db83b-b4a4-49ef-96a8-6c0fdd882d1a'

        # action = node_action.NodeAction(node.id, 'ACTION', self.ctx)

        mock_recover.return_value = new_id
        mock_status.side_effect = set_status
        action = mock.Mock()
        action.inputs = {'operation': ['SWIM', 'DANCE']}

        res = node.do_recover(self.context, action)

        self.assertTrue(res)
        mock_recover.assert_called_once_with(
            self.context, node, **action.inputs)
        self.assertEqual('node1', node.name)
        self.assertEqual(new_id, node.physical_id)
        self.assertEqual(PROFILE_ID, node.profile_id)
        self.assertEqual({'recovery': 'RECREATE'}, node.data)
        mock_status.assert_has_calls([
            mock.call(self.context, 'RECOVERING',
                      reason='Recovery in progress'),
            mock.call(self.context, consts.NS_ACTIVE,
                      reason='Recovery succeeded',
                      physical_id=new_id,
                      data={'recovery': 'RECREATE'})])

    @mock.patch.object(nodem.Node, 'set_status')
    @mock.patch.object(pb.Profile, 'recover_object')
    def test_node_recover_in_place(self, mock_recover, mock_status):
        node = nodem.Node('node1', PROFILE_ID, None)
        node.physical_id = 'd94d6333-82e6-4f87-b7ab-b786776df9d1'
        mock_recover.return_value = node.physical_id
        action = mock.Mock(inputs={})

        res = node.do_recover(self.context, action)

        self.assertTrue(res)
        mock_recover.assert_called_once_with(self.context, node)
        self.assertEqual('node1', node.name)
        self.assertEqual(PROFILE_ID, node.profile_id)
        mock_status.assert_has_calls([
            mock.call(self.context, 'RECOVERING',
                      reason='Recovery in progress'),
            mock.call(self.context, consts.NS_ACTIVE,
                      reason='Recovery succeeded')])

    @mock.patch.object(nodem.Node, 'set_status')
    def test_node_recover_check_active(self, mock_status):
        node = nodem.Node('node1', PROFILE_ID, None)
        node.physical_id = 'd94d6333-82e6-4f87-b7ab-b786776df9d1'
        node.status = 'ACTIVE'
        mock_check = self.patchobject(pb.Profile, 'check_object')
        mock_check.return_value = True
        action = mock.Mock(inputs={'check': True})

        res = node.do_recover(self.context, action)

        self.assertTrue(res)
        mock_check.assert_called_once_with(self.context, node)
        mock_status.assert_called_once_with(self.context, consts.NS_ACTIVE,
                                            reason='Recover: Node is ACTIVE.')

    @mock.patch.object(nodem.Node, 'set_status')
    @mock.patch.object(pb.Profile, 'recover_object')
    def test_node_recover_check_error(self, mock_recover, mock_status):
        def set_status(*args, **kwargs):
            if args[1] == 'ACTIVE':
                node.physical_id = new_id
                node.data = {'recovery': 'RECREATE'}

        node = nodem.Node('node1', PROFILE_ID, '')
        node.physical_id = 'd94d6333-82e6-4f87-b7ab-b786776df9d1'
        new_id = '166db83b-b4a4-49ef-96a8-6c0fdd882d1a'
        mock_recover.return_value = new_id
        mock_status.side_effect = set_status
        mock_check = self.patchobject(pb.Profile, 'check_object')
        mock_check.return_value = False
        action = mock.Mock(inputs={'check': True})

        res = node.do_recover(self.context, action)

        self.assertTrue(res)
        mock_check.assert_called_once_with(self.context, node)
        mock_recover.assert_called_once_with(
            self.context, node, **action.inputs)
        self.assertEqual('node1', node.name)
        self.assertEqual(new_id, node.physical_id)
        self.assertEqual(PROFILE_ID, node.profile_id)
        mock_status.assert_has_calls([
            mock.call(self.context, 'RECOVERING',
                      reason='Recovery in progress'),
            mock.call(self.context, consts.NS_ACTIVE,
                      reason='Recovery succeeded',
                      physical_id=new_id,
                      data={'recovery': 'RECREATE'})])

    @mock.patch.object(nodem.Node, 'set_status')
    @mock.patch.object(pb.Profile, 'recover_object')
    def test_node_recover_recreate(self, mock_recover, mock_status):
        def set_status(*args, **kwargs):
            if args[1] == 'ACTIVE':
                node.physical_id = new_id
                node.data = {'recovery': 'RECREATE'}

        node = nodem.Node('node1', PROFILE_ID, '', id='fake')
        node.physical_id = 'd94d6333-82e6-4f87-b7ab-b786776df9d1'
        new_id = '166db83b-b4a4-49ef-96a8-6c0fdd882d1a'
        mock_recover.return_value = new_id
        mock_status.side_effect = set_status
        mock_check = self.patchobject(pb.Profile, 'check_object')
        mock_check.return_value = False
        action = mock.Mock(
            outputs={}, inputs={'operation': [{'name': 'RECREATE'}],
                                'check': True})

        res = node.do_recover(self.context, action)

        self.assertTrue(res)
        mock_check.assert_called_once_with(self.context, node)
        mock_recover.assert_called_once_with(
            self.context, node, **action.inputs)
        self.assertEqual('node1', node.name)
        self.assertEqual(new_id, node.physical_id)
        self.assertEqual(PROFILE_ID, node.profile_id)
        mock_status.assert_has_calls([
            mock.call(self.context, 'RECOVERING',
                      reason='Recovery in progress'),
            mock.call(self.context, consts.NS_ACTIVE,
                      reason='Recovery succeeded',
                      physical_id=new_id,
                      data={'recovery': 'RECREATE'})])

    @mock.patch.object(nodem.Node, 'set_status')
    @mock.patch.object(pb.Profile, 'recover_object')
    def test_node_recover_mult_rebuild(self, mock_recover, mock_status):
        def set_status(*args, **kwargs):
            if args[1] == 'ACTIVE':
                node.physical_id = new_id
                node.data = {'recovery': 'RECREATE'}

        node = nodem.Node('node1', PROFILE_ID, '', id='fake')
        node.physical_id = 'd94d6333-82e6-4f87-b7ab-b786776df9d1'
        new_id = '166db83b-b4a4-49ef-96a8-6c0fdd882d1a'
        mock_recover.return_value = new_id
        mock_status.side_effect = set_status
        mock_check = self.patchobject(pb.Profile, 'check_object')
        mock_check.return_value = False
        action = mock.Mock(
            outputs={}, inputs={'operation': [{'name': 'REBOOT'},
                                              {'name': 'REBUILD'}],
                                'check': True})

        res = node.do_recover(self.context, action)

        self.assertTrue(res)
        mock_check.assert_called_once_with(self.context, node)
        mock_recover.assert_called_once_with(
            self.context, node, **action.inputs)
        self.assertEqual('node1', node.name)
        self.assertEqual(new_id, node.physical_id)
        self.assertEqual(PROFILE_ID, node.profile_id)
        mock_status.assert_has_calls([
            mock.call(self.context, 'RECOVERING',
                      reason='Recovery in progress'),
            mock.call(self.context, consts.NS_ACTIVE,
                      reason='Recovery succeeded',
                      physical_id=new_id,
                      data={'recovery': 'RECREATE'})])

    @mock.patch.object(nodem.Node, 'set_status')
    @mock.patch.object(pb.Profile, 'recover_object')
    def test_node_recover_check_exception(self, mock_recover, mock_status):
        def set_status(*args, **kwargs):
            if args[1] == 'ACTIVE':
                node.physical_id = new_id
                node.data = {'recovery': 'RECREATE'}

        node = nodem.Node('node1', PROFILE_ID, '')
        node.physical_id = 'd94d6333-82e6-4f87-b7ab-b786776df9d1'
        new_id = '166db83b-b4a4-49ef-96a8-6c0fdd882d1a'
        mock_recover.return_value = new_id
        mock_status.side_effect = set_status
        mock_check = self.patchobject(pb.Profile, 'check_object')
        mock_check.side_effect = exception.EResourceOperation(
            op='checking',
            type='server',
            id=node.physical_id,
            reason='Boom!'
        )
        action = mock.Mock(inputs={'operation': ['boom'],
                                   'check': True})

        res = node.do_recover(self.context, action)

        self.assertTrue(res)
        mock_check.assert_called_once_with(self.context, node)
        mock_recover.assert_called_once_with(
            self.context, node, **action.inputs)
        self.assertEqual('node1', node.name)
        self.assertEqual(new_id, node.physical_id)
        self.assertEqual(PROFILE_ID, node.profile_id)
        mock_status.assert_has_calls([
            mock.call(self.context, 'RECOVERING',
                      reason='Recovery in progress'),
            mock.call(self.context, consts.NS_ACTIVE,
                      reason='Recovery succeeded',
                      physical_id=new_id,
                      data={'recovery': 'RECREATE'})])

    @mock.patch.object(nodem.Node, 'set_status')
    @mock.patch.object(pb.Profile, 'recover_object')
    def test_node_recover_failed_recover(self, mock_recover, mock_status):
        node = nodem.Node('node1', PROFILE_ID, None)
        node.physical_id = 'd94d6333-82e6-4f87-b7ab-b786776df9d1'
        mock_recover.return_value = None
        action = mock.Mock(inputs={'operation': [{'name': 'RECREATE'}]})

        res = node.do_recover(self.context, action)

        self.assertFalse(res)
        mock_status.assert_has_calls([
            mock.call(self.context, 'RECOVERING',
                      reason='Recovery in progress'),
            mock.call(self.context, consts.NS_ERROR,
                      reason='Recovery failed')])

    def test_node_recover_no_physical_id(self):
        node = nodem.Node('node1', PROFILE_ID, None)
        action = mock.Mock()

        res = node.do_recover(self.context, action)

        self.assertFalse(res)

    @mock.patch.object(nodem.Node, 'set_status')
    def test_node_recover_operation_not_support(self, mock_set_status):
        node = nodem.Node('node1', PROFILE_ID, None)
        node.physical_id = 'd94d6333-82e6-4f87-b7ab-b786776df9d1'
        action = mock.Mock(
            outputs={}, inputs={'operation': [{'name': 'foo'}]})

        res = node.do_recover(self.context, action)
        self.assertEqual({}, action.outputs)
        self.assertFalse(res)

    @mock.patch.object(nodem.Node, 'set_status')
    def test_node_operation(self, mock_set_status):
        node = nodem.Node('node1', PROFILE_ID, '')
        node.physical_id = 'd94d6333-82e6-4f87-b7ab-b786776df9d1'
        x_profile = mock.Mock()
        x_profile.handle_dance = mock.Mock(return_value=True)
        node.rt['profile'] = x_profile

        inputs = {'operation': 'dance', 'params': {'style': 'tango'}}
        res = node.do_operation(self.context, **inputs)

        self.assertTrue(res)
        mock_set_status.assert_has_calls([
            mock.call(self.context, consts.NS_OPERATING,
                      reason="Operation 'dance' in progress"),
            mock.call(self.context, consts.NS_ACTIVE,
                      reason="Operation 'dance' succeeded")
        ])
        x_profile.handle_dance.assert_called_once_with(node, style='tango')

    def test_node_operation_no_physical_id(self):
        node = nodem.Node('node1', PROFILE_ID, None)
        inputs = {'operation': 'dance', 'params': {'style': 'tango'}}

        res = node.do_operation(self.context, **inputs)

        self.assertFalse(res)

    @mock.patch.object(nodem.Node, 'set_status')
    def test_node_operation_failed_op(self, mock_set_status):
        node = nodem.Node('node1', PROFILE_ID, '')
        node.physical_id = 'd94d6333-82e6-4f87-b7ab-b786776df9d1'
        x_profile = mock.Mock()
        err = exception.EResourceOperation(
            op='dance', type='container', id='test_id', message='Boom')
        x_profile.handle_dance = mock.Mock(side_effect=err)
        node.rt['profile'] = x_profile

        inputs = {'operation': 'dance', 'params': {'style': 'tango'}}
        res = node.do_operation(self.context, **inputs)

        self.assertFalse(res)
        mock_set_status.assert_has_calls([
            mock.call(self.context, consts.NS_OPERATING,
                      reason="Operation 'dance' in progress"),
            mock.call(self.context, consts.NS_ERROR,
                      reason="Failed in dance container 'test_id': Boom.")
        ])
        x_profile.handle_dance.assert_called_once_with(node, style='tango')

    def test_run_workflow(self):
        node = nodem.Node('node1', PROFILE_ID, 'FAKE_CLUSTER')
        node.physical_id = 'FAKE_NODE'

        wfc = mock.Mock()
        wfc.workflow_find.return_value = None
        wfc.workflow_create = mock.Mock()
        wfc.execution_create = mock.Mock()
        x_profile = mock.Mock()
        x_profile.workflow = mock.Mock(return_value=wfc)
        node.rt['profile'] = x_profile

        options = {
            'workflow_name': 'foo',
            'inputs': {
                'definition': {
                    'bar': 'baz'
                },
                'FAKE_KEY1': 'FAKE_VALUE1',
                'FAKE_KEY2': 'FAKE_VALUE2',
            }
        }

        res = node.run_workflow(**options)

        self.assertTrue(res)
        x_profile.workflow.assert_called_once_with(node)
        wfc.workflow_find.assert_called_once_with('foo')
        wfc.workflow_create.assert_called_once_with(
            {'bar': 'baz'}, scope='private')

        final_dict = {
            'FAKE_KEY1': 'FAKE_VALUE1',
            'FAKE_KEY2': 'FAKE_VALUE2',
            'cluster_id': 'FAKE_CLUSTER',
            'node_id': 'FAKE_NODE',
        }
        final_inputs = jsonutils.dumps(final_dict)
        wfc.execution_create.assert_called_once_with('foo', final_inputs)

    def test_run_workflow_no_physical_id(self):
        node = nodem.Node('node1', PROFILE_ID, 'FAKE_CLUSTER')
        node.physical_id = None

        res = node.run_workflow()

        self.assertFalse(res)

    def test_run_workflow_workflow_is_found(self):
        node = nodem.Node('node1', PROFILE_ID, 'FAKE_CLUSTER')
        node.physical_id = 'FAKE_NODE'

        wfc = mock.Mock()
        wfc.workflow_find.return_value = mock.Mock(definition={'bar': 'baz'})
        wfc.workflow_create = mock.Mock()
        wfc.execution_create = mock.Mock()
        x_profile = mock.Mock()
        x_profile.workflow = mock.Mock(return_value=wfc)
        node.rt['profile'] = x_profile

        options = {
            'workflow_name': 'foo',
            'inputs': {
                'FAKE_KEY1': 'FAKE_VALUE1',
                'FAKE_KEY2': 'FAKE_VALUE2',
            }
        }

        res = node.run_workflow(**options)

        self.assertTrue(res)
        x_profile.workflow.assert_called_once_with(node)
        wfc.workflow_find.assert_called_once_with('foo')
        self.assertEqual(0, wfc.workflow_create.call_count)
        final_dict = {
            'FAKE_KEY1': 'FAKE_VALUE1',
            'FAKE_KEY2': 'FAKE_VALUE2',
            'cluster_id': 'FAKE_CLUSTER',
            'node_id': 'FAKE_NODE',
        }
        final_inputs = jsonutils.dumps(final_dict)
        wfc.execution_create.assert_called_once_with('foo', final_inputs)

    def test_run_workflow_failed_creation(self):
        node = nodem.Node('node1', PROFILE_ID, 'FAKE_CLUSTER')
        node.physical_id = 'FAKE_NODE'

        wfc = mock.Mock()
        wfc.workflow_find.return_value = None
        err = exception.InternalError(message='boom')
        wfc.workflow_create.side_effect = err
        wfc.execution_create = mock.Mock()
        x_profile = mock.Mock()
        x_profile.workflow = mock.Mock(return_value=wfc)
        node.rt['profile'] = x_profile

        options = {
            'workflow_name': 'foo',
            'inputs': {
                'definition': {'bar': 'baz'},
                'FAKE_KEY1': 'FAKE_VALUE1',
                'FAKE_KEY2': 'FAKE_VALUE2',
            }
        }

        ex = self.assertRaises(exception.EResourceOperation,
                               node.run_workflow,
                               **options)

        self.assertEqual("Failed in executing workflow 'foo': boom.",
                         six.text_type(ex))
        x_profile.workflow.assert_called_once_with(node)
        wfc.workflow_find.assert_called_once_with('foo')
        wfc.workflow_create.assert_called_once_with(
            {'bar': 'baz'}, scope='private')
        self.assertEqual(0, wfc.execution_create.call_count)

    def test_run_workflow_failed_execution(self):
        node = nodem.Node('node1', PROFILE_ID, 'FAKE_CLUSTER')
        node.physical_id = 'FAKE_NODE'

        wfc = mock.Mock()
        wfc.workflow_find.return_value = None
        wfc.workflow_create = mock.Mock()
        err = exception.InternalError(message='boom')
        wfc.execution_create.side_effect = err
        x_profile = mock.Mock()
        x_profile.workflow = mock.Mock(return_value=wfc)
        node.rt['profile'] = x_profile

        options = {
            'workflow_name': 'foo',
            'inputs': {
                'definition': {'bar': 'baz'},
                'FAKE_KEY1': 'FAKE_VALUE1',
                'FAKE_KEY2': 'FAKE_VALUE2',
            }
        }

        ex = self.assertRaises(exception.EResourceOperation,
                               node.run_workflow,
                               **options)

        self.assertEqual("Failed in executing workflow 'foo': boom.",
                         six.text_type(ex))
        x_profile.workflow.assert_called_once_with(node)
        wfc.workflow_find.assert_called_once_with('foo')
        wfc.workflow_create.assert_called_once_with(
            {'bar': 'baz'}, scope='private')
        final_dict = {
            'FAKE_KEY1': 'FAKE_VALUE1',
            'FAKE_KEY2': 'FAKE_VALUE2',
            'cluster_id': 'FAKE_CLUSTER',
            'node_id': 'FAKE_NODE',
        }
        final_inputs = jsonutils.dumps(final_dict)
        wfc.execution_create.assert_called_once_with('foo', final_inputs)
