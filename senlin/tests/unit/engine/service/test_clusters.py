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
from senlin.common import scaleutils as su
from senlin.common import utils as common_utils
from senlin.engine.actions import base as am
from senlin.engine.actions import cluster_action as ca
from senlin.engine import dispatcher
from senlin.engine import node as nm
from senlin.engine import service
from senlin.objects import action as ao
from senlin.objects import base as obj_base
from senlin.objects import cluster as co
from senlin.objects import cluster_policy as cpo
from senlin.objects import node as no
from senlin.objects import profile as po
from senlin.objects import receiver as ro
from senlin.objects.requests import clusters as orco
from senlin.tests.unit.common import base
from senlin.tests.unit.common import utils


class ClusterTest(base.SenlinTestCase):

    def setUp(self):
        super(ClusterTest, self).setUp()

        self.ctx = utils.dummy_context(project='cluster_test_project')
        self.eng = service.EngineService('host-a', 'topic-a')

    @mock.patch.object(co.Cluster, 'count_all')
    def test_check_cluster_quota(self, mock_count):
        mock_count.return_value = 10
        cfg.CONF.set_override('max_clusters_per_project', 11)

        res = self.eng.check_cluster_quota(self.ctx)

        self.assertIsNone(res)
        mock_count.assert_called_once_with(self.ctx)

    @mock.patch.object(co.Cluster, 'count_all')
    def test_check_cluster_quota_failed(self, mock_count):
        mock_count.return_value = 11
        cfg.CONF.set_override('max_clusters_per_project', 11)

        ex = self.assertRaises(exc.Forbidden,
                               self.eng.check_cluster_quota, self.ctx)
        self.assertEqual("You are not authorized to complete this "
                         "operation.",
                         six.text_type(ex))

    def _prepare_request(self, req):
        mock_cls = self.patchobject(obj_base.SenlinObject,
                                    'obj_class_from_name')
        req.update({'senlin_object.name': 'RequestClass',
                    'senlin_object.version': '1.0'})
        req_base = mock.Mock()
        mock_cls.return_value = req_base
        req_obj = mock.Mock()
        for k, v in req.items():
            setattr(req_obj, k, v)
        req_base.obj_from_primitive.return_value = req_obj

    @mock.patch.object(co.Cluster, 'get_all')
    def test_cluster_list(self, mock_get):
        x_obj_1 = mock.Mock()
        x_obj_1.to_dict.return_value = {'k': 'v1'}
        x_obj_2 = mock.Mock()
        x_obj_2.to_dict.return_value = {'k': 'v2'}
        mock_get.return_value = [x_obj_1, x_obj_2]
        req = orco.ClusterListRequest(project_safe=True)

        result = self.eng.cluster_list(self.ctx, req.obj_to_primitive())

        self.assertEqual([{'k': 'v1'}, {'k': 'v2'}], result)
        mock_get.assert_called_once_with(self.ctx, project_safe=True)

    @mock.patch.object(co.Cluster, 'get_all')
    def test_cluster_list_with_params(self, mock_get):
        mock_get.return_value = []
        marker = uuidutils.generate_uuid()
        req = {
            'limit': 10,
            'marker': marker,
            'name': ['test_cluster'],
            'status': ['ACTIVE'],
            'sort': 'name:asc',
            'project_safe': True
        }
        self._prepare_request(req)

        result = self.eng.cluster_list(self.ctx, req)

        self.assertEqual([], result)
        mock_get.assert_called_once_with(
            self.ctx, limit=10, marker=marker, sort='name:asc',
            filters={'name': ['test_cluster'], 'status': ['ACTIVE']},
            project_safe=True)

    @mock.patch.object(service.EngineService, 'check_cluster_quota')
    @mock.patch.object(su, 'check_size_params')
    @mock.patch.object(am.Action, 'create')
    @mock.patch.object(co.Cluster, "create")
    @mock.patch.object(po.Profile, 'find')
    @mock.patch.object(dispatcher, 'start_action')
    def test_cluster_create(self, notify, mock_profile, mock_cluster,
                            mock_action, mock_check, mock_quota):
        x_profile = mock.Mock(id='PROFILE_ID')
        mock_profile.return_value = x_profile
        x_cluster = mock.Mock(id='12345678ABC')
        x_cluster.to_dict.return_value = {'foo': 'bar'}
        mock_cluster.return_value = x_cluster
        mock_action.return_value = 'ACTION_ID'
        mock_check.return_value = None
        mock_quota.return_value = None
        req = orco.ClusterCreateRequestBody(name='C1', profile_id='PROFILE',
                                            desired_capacity=3)

        # do it
        result = self.eng.cluster_create(self.ctx, req.obj_to_primitive())

        self.assertEqual({'action': 'ACTION_ID', 'foo': 'bar'}, result)
        mock_profile.assert_called_once_with(self.ctx, 'PROFILE')
        mock_check.assert_called_once_with(None, 3, None, None, True)
        mock_cluster.assert_called_once_with(
            self.ctx,
            dict(name='C1', desired_capacity=3, profile_id='PROFILE_ID',
                 min_size=0, max_size=-1, timeout=3600, metadata={},
                 dependents={}, data={}, next_index=1, status='INIT',
                 config={},
                 status_reason='Initializing', user=self.ctx.user_id,
                 project=self.ctx.project_id, domain=self.ctx.domain_id))
        mock_action.assert_called_once_with(
            self.ctx,
            '12345678ABC', 'CLUSTER_CREATE',
            name='cluster_create_12345678',
            cause=consts.CAUSE_RPC,
            status=am.Action.READY,
        )
        notify.assert_called_once_with()

    @mock.patch.object(service.EngineService, 'check_cluster_quota')
    @mock.patch.object(su, 'check_size_params')
    @mock.patch.object(am.Action, 'create')
    @mock.patch.object(co.Cluster, "create")
    @mock.patch.object(po.Profile, 'find')
    @mock.patch.object(dispatcher, 'start_action')
    def test_cluster_create_desired_null(self, notify, mock_profile,
                                         mock_cluster, mock_action,
                                         mock_check, mock_quota):
        x_profile = mock.Mock(id='PROFILE_ID')
        mock_profile.return_value = x_profile
        x_cluster = mock.Mock(id='12345678ABC')
        x_cluster.to_dict.return_value = {'foo': 'bar'}
        mock_cluster.return_value = x_cluster
        mock_action.return_value = 'ACTION_ID'
        mock_check.return_value = None
        mock_quota.return_value = None
        req = orco.ClusterCreateRequestBody(name='C1', profile_id='PROFILE',
                                            min_size=1, max_size=5,
                                            config={'k1': 'v1'})

        # do it
        result = self.eng.cluster_create(self.ctx, req.obj_to_primitive())

        self.assertEqual({'action': 'ACTION_ID', 'foo': 'bar'}, result)
        mock_profile.assert_called_once_with(self.ctx, 'PROFILE')
        mock_check.assert_called_once_with(None, 1, 1, 5, True)
        mock_cluster.assert_called_once_with(
            self.ctx,
            dict(name='C1', desired_capacity=1, profile_id='PROFILE_ID',
                 min_size=1, max_size=5, timeout=3600, metadata={},
                 dependents={}, data={}, next_index=1, status='INIT',
                 config={'k1': 'v1'},
                 status_reason='Initializing', user=self.ctx.user_id,
                 project=self.ctx.project_id, domain=self.ctx.domain_id))
        mock_action.assert_called_once_with(
            self.ctx,
            '12345678ABC', 'CLUSTER_CREATE',
            name='cluster_create_12345678',
            cause=consts.CAUSE_RPC,
            status=am.Action.READY,
        )
        notify.assert_called_once_with()

    @mock.patch.object(service.EngineService, 'check_cluster_quota')
    def test_cluster_create_exceeding_quota(self, mock_quota):
        mock_quota.side_effect = exc.Forbidden()
        req = {'profile_id': 'PROFILE', 'name': 'CLUSTER'}
        self._prepare_request(req)

        ex = self.assertRaises(rpc.ExpectedException,
                               self.eng.cluster_create,
                               self.ctx, req)

        self.assertEqual(exc.Forbidden, ex.exc_info[0])
        self.assertEqual("You are not authorized to complete this "
                         "operation.",
                         six.text_type(ex.exc_info[1]))
        mock_quota.assert_called_once_with(self.ctx)

    @mock.patch.object(service.EngineService, 'check_cluster_quota')
    @mock.patch.object(co.Cluster, 'get_by_name')
    def test_cluster_create_duplicate_name(self, mock_get, mock_quota):
        cfg.CONF.set_override('name_unique', True)
        mock_quota.return_value = None
        mock_get.return_value = mock.Mock()
        req = {'profile_id': 'PROFILE', 'name': 'CLUSTER'}
        self._prepare_request(req)

        ex = self.assertRaises(rpc.ExpectedException,
                               self.eng.cluster_create,
                               self.ctx, req)

        self.assertEqual(exc.BadRequest, ex.exc_info[0])
        self.assertEqual(_("a cluster named 'CLUSTER' already exists."),
                         six.text_type(ex.exc_info[1]))
        mock_get.assert_called_once_with(self.ctx, 'CLUSTER')

    @mock.patch.object(service.EngineService, 'check_cluster_quota')
    @mock.patch.object(po.Profile, 'find')
    def test_cluster_create_profile_not_found(self, mock_find, mock_quota):
        mock_quota.return_value = None
        mock_find.side_effect = exc.ResourceNotFound(type='profile',
                                                     id='Bogus')
        req = {'profile_id': 'Bogus', 'name': 'CLUSTER'}
        self._prepare_request(req)
        ex = self.assertRaises(rpc.ExpectedException,
                               self.eng.cluster_create,
                               self.ctx, req)

        self.assertEqual(exc.BadRequest, ex.exc_info[0])
        self.assertEqual("The specified profile 'Bogus' could not "
                         "be found.", six.text_type(ex.exc_info[1]))
        mock_find.assert_called_once_with(self.ctx, 'Bogus')

    @mock.patch.object(service.EngineService, 'check_cluster_quota')
    @mock.patch.object(po.Profile, 'find')
    @mock.patch.object(su, 'check_size_params')
    def test_cluster_create_failed_checking(self, mock_check, mock_find,
                                            mock_quota):
        mock_quota.return_value = None
        mock_find.return_value = mock.Mock()
        mock_check.return_value = 'INVALID'
        req = {'profile_id': 'PROFILE', 'name': 'CLUSTER'}
        self._prepare_request(req)

        ex = self.assertRaises(rpc.ExpectedException,
                               self.eng.cluster_create,
                               self.ctx, req)

        self.assertEqual(exc.BadRequest, ex.exc_info[0])
        self.assertEqual("INVALID.", six.text_type(ex.exc_info[1]))
        mock_find.assert_called_once_with(self.ctx, 'PROFILE')

    @mock.patch.object(co.Cluster, 'find')
    def test_cluster_get(self, mock_find):
        x_cluster = mock.Mock()
        x_cluster.to_dict.return_value = {'foo': 'bar'}
        mock_find.return_value = x_cluster
        req = orco.ClusterGetRequest(identity='C1')

        result = self.eng.cluster_get(self.ctx, req.obj_to_primitive())

        self.assertEqual({'foo': 'bar'}, result)
        mock_find.assert_called_once_with(self.ctx, 'C1')

    @mock.patch.object(co.Cluster, 'find')
    def test_cluster_get_not_found(self, mock_find):
        mock_find.side_effect = exc.ResourceNotFound(type='cluster',
                                                     id='Bogus')
        req = {'identity': 'CLUSTER'}
        self._prepare_request(req)

        ex = self.assertRaises(rpc.ExpectedException,
                               self.eng.cluster_get,
                               self.ctx, req)
        self.assertEqual(exc.ResourceNotFound, ex.exc_info[0])

    @mock.patch.object(am.Action, 'create')
    @mock.patch.object(po.Profile, 'find')
    @mock.patch.object(co.Cluster, 'find')
    @mock.patch.object(dispatcher, 'start_action')
    def test_cluster_update(self, notify, mock_find, mock_profile,
                            mock_action):
        x_cluster = mock.Mock(id='12345678AB', status='ACTIVE',
                              profile_id='OLD_PROFILE',
                              metadata={'A': 'B'})
        x_cluster.to_dict.return_value = {'foo': 'bar'}
        mock_find.return_value = x_cluster
        old_profile = mock.Mock(type='FAKE_TYPE', id='ID_OLD')
        new_profile = mock.Mock(type='FAKE_TYPE', id='ID_NEW')
        mock_profile.side_effect = [old_profile, new_profile]
        mock_action.return_value = 'ACTION_ID'
        req = orco.ClusterUpdateRequest(identity='FAKE_ID', name='new_name',
                                        profile_id='NEW_PROFILE',
                                        metadata={'B': 'A'}, timeout=120,
                                        config={'k1': 'v1'})

        # do it
        result = self.eng.cluster_update(self.ctx, req.obj_to_primitive())

        self.assertEqual({'action': 'ACTION_ID', 'foo': 'bar'}, result)
        mock_find.assert_called_once_with(self.ctx, 'FAKE_ID')
        mock_profile.assert_has_calls([
            mock.call(self.ctx, 'OLD_PROFILE'),
            mock.call(self.ctx, 'NEW_PROFILE'),
        ])
        mock_action.assert_called_once_with(
            self.ctx, '12345678AB', 'CLUSTER_UPDATE',
            name='cluster_update_12345678',
            cause=consts.CAUSE_RPC,
            status=am.Action.READY,
            inputs={
                'new_profile_id': 'ID_NEW',
                'metadata': {
                    'B': 'A',
                },
                'timeout': 120,
                'name': 'new_name',
                'config': {
                    'k1': 'v1',
                },
            }
        )

    @mock.patch.object(co.Cluster, 'find')
    def test_cluster_update_cluster_not_found(self, mock_find):
        mock_find.side_effect = exc.ResourceNotFound(type='cluster',
                                                     id='Bogus')
        req = {'identity': 'Bogus', 'name': 'new-name'}
        self._prepare_request(req)
        ex = self.assertRaises(rpc.ExpectedException,
                               self.eng.cluster_update,
                               self.ctx, req)
        self.assertEqual(exc.ResourceNotFound, ex.exc_info[0])

    @mock.patch.object(co.Cluster, 'find')
    def test_cluster_update_cluster_bad_status(self, mock_find):
        x_cluster = mock.Mock(status='ERROR')
        mock_find.return_value = x_cluster
        req = {'identity': 'CLUSTER', 'name': 'new-name'}
        self._prepare_request(req)

        self.assertEqual(consts.CS_ERROR, x_cluster.status)
        ex = self.assertRaises(rpc.ExpectedException,
                               self.eng.cluster_update,
                               self.ctx, req)

        self.assertEqual(exc.FeatureNotSupported, ex.exc_info[0])
        self.assertEqual('Updating a cluster in error state is not supported.',
                         six.text_type(ex.exc_info[1]))
        mock_find.assert_called_once_with(self.ctx, 'CLUSTER')

    @mock.patch.object(po.Profile, 'find')
    @mock.patch.object(co.Cluster, 'find')
    def test_cluster_update_profile_not_found(self, mock_find, mock_profile):
        mock_find.return_value = mock.Mock(status='ACTIVE',
                                           profile_id='OLD_ID')
        mock_profile.side_effect = [
            mock.Mock(type='FAKE_TYPE', id='OLD_ID'),
            exc.ResourceNotFound(type='profile', id='Bogus')
        ]
        req = orco.ClusterUpdateRequest(identity='CLUSTER', profile_id='Bogus')

        ex = self.assertRaises(rpc.ExpectedException,
                               self.eng.cluster_update,
                               self.ctx, req.obj_to_primitive())

        self.assertEqual(exc.BadRequest, ex.exc_info[0])
        self.assertEqual("The specified profile 'Bogus' could not be found.",
                         six.text_type(ex.exc_info[1]))
        mock_find.assert_called_once_with(self.ctx, 'CLUSTER')
        mock_profile.assert_has_calls([
            mock.call(self.ctx, 'OLD_ID'),
            mock.call(self.ctx, 'Bogus'),
        ])

    @mock.patch.object(po.Profile, 'find')
    @mock.patch.object(co.Cluster, 'find')
    def test_cluster_update_diff_profile_type(self, mock_find, mock_profile):
        x_obj = mock.Mock(status='ACTIVE', profile_id='OLD_ID')
        mock_find.return_value = x_obj
        mock_profile.side_effect = [
            mock.Mock(type='FAKE_TYPE', id='OLD_ID'),
            mock.Mock(type='DIFF_TYPE', id='NEW_ID'),
        ]
        req = orco.ClusterUpdateRequest(identity='CLUSTER',
                                        profile_id='NEW_PROFILE')

        ex = self.assertRaises(rpc.ExpectedException,
                               self.eng.cluster_update,
                               self.ctx, req.obj_to_primitive())

        self.assertEqual(exc.BadRequest, ex.exc_info[0])
        mock_find.assert_called_once_with(self.ctx, 'CLUSTER')
        mock_profile.assert_has_calls([
            mock.call(self.ctx, 'OLD_ID'),
            mock.call(self.ctx, 'NEW_PROFILE'),
        ])

    @mock.patch.object(am.Action, 'create')
    @mock.patch.object(po.Profile, 'find')
    @mock.patch.object(co.Cluster, 'find')
    @mock.patch.object(dispatcher, 'start_action')
    def test_cluster_update_same_profile(self, notify, mock_find,
                                         mock_profile, mock_action):
        x_cluster = mock.Mock(id='12345678AB', status='ACTIVE',
                              profile_id='OLD_PROFILE')
        x_cluster.to_dict.return_value = {'foo': 'bar'}
        mock_find.return_value = x_cluster
        old_profile = mock.Mock(type='FAKE_TYPE', id='ID_OLD')
        new_profile = mock.Mock(type='FAKE_TYPE', id='ID_OLD')
        mock_profile.side_effect = [old_profile, new_profile]
        mock_action.return_value = 'ACTION_ID'
        req = orco.ClusterUpdateRequest(identity='FAKE_ID', name='NEW_NAME',
                                        profile_id='NEW_PROFILE')

        # do it
        result = self.eng.cluster_update(self.ctx, req.obj_to_primitive())

        self.assertEqual({'action': 'ACTION_ID', 'foo': 'bar'}, result)
        mock_find.assert_called_once_with(self.ctx, 'FAKE_ID')
        mock_profile.assert_has_calls([
            mock.call(self.ctx, 'OLD_PROFILE'),
            mock.call(self.ctx, 'NEW_PROFILE'),
        ])
        mock_action.assert_called_once_with(
            self.ctx, '12345678AB', 'CLUSTER_UPDATE',
            name='cluster_update_12345678',
            cause=consts.CAUSE_RPC,
            status=am.Action.READY,
            inputs={
                # Note profile_id is not shown in the inputs
                'name': 'NEW_NAME',
            },
        )
        notify.assert_called_once_with()

    @mock.patch.object(am.Action, 'create')
    @mock.patch.object(co.Cluster, 'find')
    @mock.patch.object(dispatcher, 'start_action')
    def test_cluster_update_same_metadata(self, notify, mock_find,
                                          mock_action):
        x_cluster = mock.Mock(id='12345678AB', status='ACTIVE',
                              metadata={'K': 'V'})
        x_cluster.to_dict.return_value = {'foo': 'bar'}
        mock_find.return_value = x_cluster
        mock_action.return_value = 'ACTION_ID'
        req = orco.ClusterUpdateRequest(identity='FAKE_ID', name='NEW_NAME',
                                        metadata={'K': 'V'})

        # do it
        result = self.eng.cluster_update(self.ctx, req.obj_to_primitive())

        self.assertEqual({'action': 'ACTION_ID', 'foo': 'bar'}, result)
        mock_find.assert_called_once_with(self.ctx, 'FAKE_ID')
        mock_action.assert_called_once_with(
            self.ctx, '12345678AB', 'CLUSTER_UPDATE',
            name='cluster_update_12345678',
            status=am.Action.READY,
            cause=consts.CAUSE_RPC,
            inputs={
                # Note metadata is not included in the inputs
                'name': 'NEW_NAME',
            },
        )
        notify.assert_called_once_with()

    @mock.patch.object(am.Action, 'create')
    @mock.patch.object(co.Cluster, 'find')
    @mock.patch.object(dispatcher, 'start_action')
    def test_cluster_update_same_timeout(self, notify, mock_find,
                                         mock_action):
        x_cluster = mock.Mock(id='12345678AB', status='ACTIVE',
                              timeout=10)
        x_cluster.to_dict.return_value = {'foo': 'bar'}
        x_cluster.timeout = 10
        mock_find.return_value = x_cluster
        mock_action.return_value = 'ACTION_ID'
        req = orco.ClusterUpdateRequest(identity='FAKE_ID', name='NEW_NAME',
                                        timeout=10)

        # do it
        result = self.eng.cluster_update(self.ctx, req.obj_to_primitive())

        self.assertEqual({'action': 'ACTION_ID', 'foo': 'bar'}, result)
        mock_find.assert_called_once_with(self.ctx, 'FAKE_ID')
        mock_action.assert_called_once_with(
            self.ctx, '12345678AB', 'CLUSTER_UPDATE',
            name='cluster_update_12345678',
            status=am.Action.READY,
            cause=consts.CAUSE_RPC,
            inputs={
                # Note timeout is not included in the inputs
                'name': 'NEW_NAME',
            },
        )
        notify.assert_called_once_with()

    @mock.patch.object(am.Action, 'create')
    @mock.patch.object(co.Cluster, 'find')
    @mock.patch.object(dispatcher, 'start_action')
    def test_cluster_update_same_name(self, notify, mock_find,
                                      mock_action):
        x_cluster = mock.Mock(id='12345678AB', status='ACTIVE',
                              name='OLD_NAME', timeout=10)
        x_cluster.name = 'OLD_NAME'
        x_cluster.to_dict.return_value = {'foo': 'bar'}
        mock_find.return_value = x_cluster
        mock_action.return_value = 'ACTION_ID'
        req = orco.ClusterUpdateRequest(identity='FAKE_ID', name='OLD_NAME',
                                        timeout=100)

        # do it
        result = self.eng.cluster_update(self.ctx, req.obj_to_primitive())

        self.assertEqual({'action': 'ACTION_ID', 'foo': 'bar'}, result)
        mock_find.assert_called_once_with(self.ctx, 'FAKE_ID')
        mock_action.assert_called_once_with(
            self.ctx, '12345678AB', 'CLUSTER_UPDATE',
            name='cluster_update_12345678',
            status=am.Action.READY,
            cause=consts.CAUSE_RPC,
            inputs={
                # Note name is not included in the inputs
                'timeout': 100,
            },
        )
        notify.assert_called_once_with()

    @mock.patch.object(co.Cluster, 'find')
    def test_cluster_update_all_property_same(self, mock_find):
        x_cluster = mock.Mock(id='12345678AB', status='ACTIVE',
                              name='OLD_NAME', timeout=10)
        x_cluster.name = 'OLD_NAME'
        x_cluster.timeout = 10
        mock_find.return_value = x_cluster

        # Notice that name and timeout are all not changed.
        req = orco.ClusterUpdateRequest(identity='CLUSTER', name='OLD_NAME',
                                        timeout=10)

        ex = self.assertRaises(rpc.ExpectedException,
                               self.eng.cluster_update,
                               self.ctx, req.obj_to_primitive())

        self.assertEqual(exc.BadRequest, ex.exc_info[0])
        self.assertEqual('', six.text_type(ex))

    @mock.patch.object(co.Cluster, 'find')
    def test_cluster_update_no_property_updated(self, mock_find):
        x_cluster = mock.Mock(status='ACTIVE', profile_id='OLD_ID')
        mock_find.return_value = x_cluster
        req = orco.ClusterUpdateRequest(identity='CLUSTER')

        ex = self.assertRaises(rpc.ExpectedException,
                               self.eng.cluster_update,
                               self.ctx, req.obj_to_primitive())

        self.assertEqual(exc.BadRequest, ex.exc_info[0])
        self.assertEqual('', six.text_type(ex))

    @mock.patch.object(co.Cluster, 'find')
    def test_cluster_add_nodes_cluster_not_found(self, mock_find):
        mock_find.side_effect = exc.ResourceNotFound(type='cluster',
                                                     id='Bogus')
        req = {'identity': 'Bogus', 'nodes': ['n1', 'n2']}
        self._prepare_request(req)

        ex = self.assertRaises(rpc.ExpectedException,
                               self.eng.cluster_add_nodes,
                               self.ctx, req)

        self.assertEqual(exc.ResourceNotFound, ex.exc_info[0])
        self.assertEqual("The cluster 'Bogus' could not be found.",
                         six.text_type(ex.exc_info[1]))
        mock_find.assert_called_once_with(self.ctx, 'Bogus')

    @mock.patch.object(su, 'check_size_params')
    @mock.patch.object(am.Action, 'create')
    @mock.patch.object(po.Profile, 'get')
    @mock.patch.object(no.Node, 'find')
    @mock.patch.object(co.Cluster, 'find')
    @mock.patch.object(dispatcher, 'start_action')
    def test_cluster_add_nodes(self, notify, mock_find, mock_node,
                               mock_profile, mock_action, mock_check):
        x_cluster = mock.Mock(id='12345678AB', profile_id='FAKE_ID',
                              desired_capacity=4)
        mock_find.return_value = x_cluster
        mock_profile.return_value = mock.Mock(type='FAKE_TYPE')
        x_node_1 = mock.Mock(id='NODE1', cluster_id='', status='ACTIVE',
                             profile_id='FAKE_ID_1')
        x_node_2 = mock.Mock(id='NODE2', cluster_id='', status='ACTIVE',
                             profile_id='FAKE_ID_1')
        mock_node.side_effect = [x_node_1, x_node_2]
        mock_action.return_value = 'ACTION_ID'
        mock_check.return_value = None
        req = orco.ClusterAddNodesRequest(identity='C1',
                                          nodes=['NODE_A', 'NODE_B'])

        result = self.eng.cluster_add_nodes(self.ctx, req.obj_to_primitive())

        self.assertEqual({'action': 'ACTION_ID'}, result)
        mock_find.assert_called_once_with(self.ctx, 'C1')
        mock_node.assert_has_calls([
            mock.call(self.ctx, 'NODE_A'),
            mock.call(self.ctx, 'NODE_B'),
        ])
        mock_check.assert_called_once_with(x_cluster, 6, strict=True)
        mock_action.assert_called_once_with(
            self.ctx, '12345678AB', consts.CLUSTER_ADD_NODES,
            name='cluster_add_nodes_12345678',
            cause=consts.CAUSE_RPC,
            status=am.Action.READY,
            inputs={'nodes': ['NODE1', 'NODE2']},
        )
        self.assertEqual(3, mock_profile.call_count)
        notify.assert_called_once_with()

    @mock.patch.object(po.Profile, 'get')
    @mock.patch.object(no.Node, 'find')
    @mock.patch.object(co.Cluster, 'find')
    def test_cluster_add_nodes_nodes_not_found(self, mock_find, mock_node,
                                               mock_profile):
        mock_find.return_value = mock.Mock(id='1234', profile_id='FAKE_ID')
        mock_profile.return_value = mock.Mock(type='FAKE_TYPE')
        mock_node.side_effect = exc.ResourceNotFound(type='node', id='NODE1')
        req = {'identity': 'CLUSTER', 'nodes': ['NODE1']}
        self._prepare_request(req)

        ex = self.assertRaises(rpc.ExpectedException,
                               self.eng.cluster_add_nodes,
                               self.ctx, req)

        self.assertEqual(exc.BadRequest, ex.exc_info[0])
        self.assertEqual("Nodes not found: ['NODE1'].",
                         six.text_type(ex.exc_info[1]))
        mock_find.assert_called_once_with(self.ctx, 'CLUSTER')
        mock_profile.assert_called_once_with(self.ctx, 'FAKE_ID',
                                             project_safe=True)
        mock_node.assert_called_once_with(self.ctx, 'NODE1')

    @mock.patch.object(po.Profile, 'get')
    @mock.patch.object(no.Node, 'find')
    @mock.patch.object(co.Cluster, 'find')
    def test_cluster_add_nodes_bad_status(self, mock_find, mock_node,
                                          mock_profile):
        mock_find.return_value = mock.Mock(id='1234', profile_id='FAKE_ID')
        mock_profile.return_value = mock.Mock(type='FAKE_TYPE')
        mock_node.return_value = mock.Mock(
            id='NODE2', cluster_id='', status='ERROR')
        req = {'identity': 'CLUSTER', 'nodes': ['NODE2']}
        self._prepare_request(req)

        ex = self.assertRaises(rpc.ExpectedException,
                               self.eng.cluster_add_nodes,
                               self.ctx, req)

        self.assertEqual(exc.BadRequest, ex.exc_info[0])
        self.assertEqual("Nodes are not ACTIVE: ['NODE2'].",
                         six.text_type(ex.exc_info[1]))

        mock_find.assert_called_once_with(self.ctx, 'CLUSTER')
        self.assertEqual(2, mock_profile.call_count)
        mock_node.assert_called_once_with(self.ctx, 'NODE2')

    @mock.patch.object(po.Profile, 'get')
    @mock.patch.object(no.Node, 'find')
    @mock.patch.object(co.Cluster, 'find')
    def test_cluster_add_nodes_node_already_owned(self, mock_find,
                                                  mock_node, mock_profile):

        mock_find.return_value = mock.Mock(id='1234', profile_id='FAKE_ID')
        mock_profile.return_value = mock.Mock(type='FAKE_TYPE')
        mock_node.return_value = mock.Mock(id='NODE3', status='ACTIVE',
                                           cluster_id='OTHER')
        req = {'identity': 'CLUSTER', 'nodes': ['NODE3']}
        self._prepare_request(req)

        ex = self.assertRaises(rpc.ExpectedException,
                               self.eng.cluster_add_nodes,
                               self.ctx, req)

        self.assertEqual(exc.BadRequest, ex.exc_info[0])
        self.assertEqual("Nodes ['NODE3'] already owned by some cluster.",
                         six.text_type(ex.exc_info[1]))

        mock_find.assert_called_once_with(self.ctx, 'CLUSTER')
        self.assertEqual(2, mock_profile.call_count)
        mock_node.assert_called_once_with(self.ctx, 'NODE3')

    @mock.patch.object(po.Profile, 'get')
    @mock.patch.object(no.Node, 'find')
    @mock.patch.object(co.Cluster, 'find')
    def test_cluster_add_nodes_node_profile_type_not_match(
            self, mock_find, mock_node, mock_profile):

        mock_find.return_value = mock.Mock(id='1234', profile_id='FAKE_ID')
        mock_profile.side_effect = [
            mock.Mock(type='FAKE_TYPE_1'),
            mock.Mock(type='FAKE_TYPE_2'),
        ]
        mock_node.return_value = mock.Mock(id='NODE4', status='ACTIVE',
                                           cluster_id='', profile_id='DIFF')
        req = {'identity': 'CLUSTER', 'nodes': ['NODE4']}
        self._prepare_request(req)

        ex = self.assertRaises(rpc.ExpectedException,
                               self.eng.cluster_add_nodes,
                               self.ctx, req)

        self.assertEqual(exc.BadRequest, ex.exc_info[0])
        self.assertEqual("Profile type of nodes ['NODE4'] does not "
                         "match that of the cluster.",
                         six.text_type(ex.exc_info[1]))
        mock_find.assert_called_once_with(self.ctx, 'CLUSTER')
        mock_profile.assert_has_calls([
            mock.call(self.ctx, 'FAKE_ID', project_safe=True),
            mock.call(self.ctx, 'DIFF', project_safe=True),
        ])
        mock_node.assert_called_once_with(self.ctx, 'NODE4')

    @mock.patch.object(po.Profile, 'get')
    @mock.patch.object(no.Node, 'find')
    @mock.patch.object(co.Cluster, 'find')
    def test_cluster_add_nodes_mult_err(self, mock_find, mock_node,
                                        mock_profile):
        mock_find.return_value = mock.Mock(id='1234', profile_id='FAKE_ID')
        mock_profile.return_value = mock.Mock(type='FAKE_TYPE')
        mock_node.return_value = mock.Mock(id='NODE2', status='ERROR')
        req = {'identity': 'CLUSTER', 'nodes': ['NODE2']}
        self._prepare_request(req)

        ex = self.assertRaises(rpc.ExpectedException,
                               self.eng.cluster_add_nodes,
                               self.ctx, req)

        self.assertEqual(exc.BadRequest, ex.exc_info[0])
        msg1 = _("Nodes ['NODE2'] already owned by some cluster.")
        msg2 = _("Nodes are not ACTIVE: ['NODE2'].")
        self.assertIn(msg1, six.text_type(ex.exc_info[1]))
        self.assertIn(msg2, six.text_type(ex.exc_info[1]))

        mock_find.assert_called_once_with(self.ctx, 'CLUSTER')
        self.assertEqual(2, mock_profile.call_count)
        mock_node.assert_called_once_with(self.ctx, 'NODE2')

    @mock.patch.object(po.Profile, 'get')
    @mock.patch.object(su, 'check_size_params')
    @mock.patch.object(no.Node, 'find')
    @mock.patch.object(co.Cluster, 'find')
    def test_cluster_add_nodes_failed_checking(self, mock_find, mock_node,
                                               mock_check, mock_profile):
        x_cluster = mock.Mock(id='12345678AB', profile_id='FAKE_PROFILE',
                              desired_capacity=2)
        mock_find.return_value = x_cluster
        mock_profile.return_value = mock.Mock(type='FAKE_TYPE')
        x_node_1 = mock.Mock(id='NODE1', cluster_id='', status='ACTIVE',
                             profile_id='FAKE_PROFILE_1')
        x_node_2 = mock.Mock(id='NODE2', cluster_id='', status='ACTIVE',
                             profile_id='FAKE_PROFILE_2')
        mock_node.side_effect = [x_node_1, x_node_2]
        mock_check.return_value = 'Failed size checking.'
        req = {'identity': 'C1', 'nodes': ['NODE_A', 'NODE_B']}
        self._prepare_request(req)

        ex = self.assertRaises(rpc.ExpectedException,
                               self.eng.cluster_add_nodes,
                               self.ctx, req)

        self.assertEqual(exc.BadRequest, ex.exc_info[0])
        self.assertEqual("Failed size checking.",
                         six.text_type(ex.exc_info[1]))

        mock_find.assert_called_once_with(self.ctx, 'C1')
        mock_profile.assert_has_calls([
            mock.call(self.ctx, 'FAKE_PROFILE', project_safe=True),
            mock.call(self.ctx, 'FAKE_PROFILE_1', project_safe=True),
            mock.call(self.ctx, 'FAKE_PROFILE_2', project_safe=True),
        ])
        mock_node.assert_has_calls([
            mock.call(self.ctx, 'NODE_A'),
            mock.call(self.ctx, 'NODE_B'),
        ])
        mock_check.assert_called_once_with(x_cluster, 4, strict=True)

    @mock.patch.object(su, 'check_size_params')
    @mock.patch.object(am.Action, 'create')
    @mock.patch.object(no.Node, 'find')
    @mock.patch.object(co.Cluster, 'find')
    @mock.patch.object(dispatcher, 'start_action')
    def test_cluster_del_nodes(self, notify, mock_find, mock_node,
                               mock_action, mock_check):
        x_cluster = mock.Mock(id='1234', desired_capacity=2)
        mock_find.return_value = x_cluster
        mock_node.return_value = mock.Mock(id='NODE2', cluster_id='1234',
                                           dependents={})
        mock_check.return_value = None
        mock_action.return_value = 'ACTION_ID'
        req = orco.ClusterDelNodesRequest(identity='CLUSTER', nodes=['NODE1'])

        result = self.eng.cluster_del_nodes(self.ctx, req.obj_to_primitive())

        self.assertEqual({'action': 'ACTION_ID'}, result)
        mock_find.assert_called_once_with(self.ctx, 'CLUSTER')
        mock_node.assert_called_once_with(self.ctx, 'NODE1')
        mock_check.asset_called_once_with(x_cluster, 1, strict=True)
        mock_action.assert_called_once_with(
            self.ctx, '1234', consts.CLUSTER_DEL_NODES,
            name='cluster_del_nodes_1234',
            status=am.Action.READY,
            cause=consts.CAUSE_RPC,
            inputs={
                'count': 1,
                'candidates': ['NODE2'],
            },
        )
        notify.assert_called_once_with()

    @mock.patch.object(co.Cluster, 'find')
    def test_cluster_del_nodes_cluster_not_found(self, mock_find):
        mock_find.side_effect = exc.ResourceNotFound(type='cluster',
                                                     id='Bogus')
        req = orco.ClusterDelNodesRequest(identity='Bogus', nodes=['NODE1'])

        ex = self.assertRaises(rpc.ExpectedException,
                               self.eng.cluster_del_nodes,
                               self.ctx, req.obj_to_primitive())

        self.assertEqual(exc.ResourceNotFound, ex.exc_info[0])
        self.assertEqual("The cluster 'Bogus' could not be found.",
                         six.text_type(ex.exc_info[1]))
        mock_find.assert_called_once_with(self.ctx, 'Bogus')

    @mock.patch.object(no.Node, 'find')
    @mock.patch.object(co.Cluster, 'find')
    def test_cluster_del_nodes_node_not_found(self, mock_find, mock_node):
        mock_find.return_value = mock.Mock()
        mock_node.side_effect = exc.ResourceNotFound(type='node', id='NODE1')
        req = orco.ClusterDelNodesRequest(identity='CLUSTER', nodes=['NODE1'])

        ex = self.assertRaises(rpc.ExpectedException,
                               self.eng.cluster_del_nodes,
                               self.ctx, req.obj_to_primitive())

        self.assertEqual(exc.BadRequest, ex.exc_info[0])
        self.assertIn("Nodes not found",
                      six.text_type(ex.exc_info[1]))
        mock_find.assert_called_once_with(self.ctx, 'CLUSTER')
        mock_node.assert_called_once_with(self.ctx, 'NODE1')

    @mock.patch.object(no.Node, 'find')
    @mock.patch.object(co.Cluster, 'find')
    def test_cluster_del_nodes_have_containers(self, mock_cluster, mock_node):
        mock_cluster.return_value = mock.Mock(id='CLUSTER1')
        dependents = {'nodes': ['container1']}
        node = mock.Mock(id='NODE1', dependents=dependents,
                         cluster_id='CLUSTER1')
        mock_node.return_value = node
        req = orco.ClusterDelNodesRequest(identity='CLUSTER', nodes=['NODE1'])
        ex = self.assertRaises(rpc.ExpectedException,
                               self.eng.cluster_del_nodes,
                               self.ctx, req.obj_to_primitive())
        self.assertEqual(exc.ResourceInUse, ex.exc_info[0])
        message = _("nodes ['NODE1'] are depended by other nodes, so can't be "
                    "deleted or become orphan nodes")
        self.assertIn(message, six.text_type(ex.exc_info[1]))

    @mock.patch.object(no.Node, 'find')
    @mock.patch.object(co.Cluster, 'find')
    def test_cluster_del_nodes_node_in_other_cluster(self, mock_find,
                                                     mock_node):
        mock_find.return_value = mock.Mock(id='1234')
        mock_node.return_value = mock.Mock(id='NODE2', cluster_id='5678')
        req = orco.ClusterDelNodesRequest(identity='CLUSTER', nodes=['NODE2'])

        ex = self.assertRaises(rpc.ExpectedException,
                               self.eng.cluster_del_nodes,
                               self.ctx, req.obj_to_primitive())

        self.assertEqual(exc.BadRequest, ex.exc_info[0])
        self.assertEqual("Nodes not members of specified cluster: ['NODE2'].",
                         six.text_type(ex.exc_info[1]))
        mock_find.assert_called_once_with(self.ctx, 'CLUSTER')
        mock_node.assert_called_once_with(self.ctx, 'NODE2')

    @mock.patch.object(no.Node, 'find')
    @mock.patch.object(co.Cluster, 'find')
    def test_cluster_del_nodes_mult_errors(self, mock_find, mock_node):
        mock_find.return_value = mock.Mock(id='1234')
        mock_node.side_effect = [mock.Mock(id='NODE1', cluster_id='5678'),
                                 exc.ResourceNotFound(type='node', id='NODE2')]
        req = orco.ClusterDelNodesRequest(identity='CLUSTER',
                                          nodes=['NODE1', 'NODE2'])

        ex = self.assertRaises(rpc.ExpectedException,
                               self.eng.cluster_del_nodes,
                               self.ctx, req.obj_to_primitive())

        self.assertEqual(exc.BadRequest, ex.exc_info[0])
        msg1 = _("Nodes not found:")
        msg2 = _("Nodes not members of specified cluster: ['NODE1'].")
        self.assertIn(msg1, six.text_type(ex.exc_info[1]))
        self.assertIn(msg2, six.text_type(ex.exc_info[1]))
        mock_find.assert_called_once_with(self.ctx, 'CLUSTER')
        self.assertEqual(2, mock_node.call_count)

    @mock.patch.object(no.Node, 'find')
    @mock.patch.object(co.Cluster, 'find')
    def test_cluster_del_nodes_orphan_nodes(self, mock_find, mock_node):
        mock_find.return_value = mock.Mock(id='1234')
        mock_node.return_value = mock.Mock(id='NODE3', cluster_id='')
        req = orco.ClusterDelNodesRequest(identity='CLUSTER', nodes=['NODE3'])

        ex = self.assertRaises(rpc.ExpectedException,
                               self.eng.cluster_del_nodes,
                               self.ctx, req.obj_to_primitive())

        self.assertEqual(exc.BadRequest, ex.exc_info[0])
        self.assertEqual("Nodes not members of specified cluster: ['NODE3'].",
                         six.text_type(ex.exc_info[1]))

        mock_find.assert_called_once_with(self.ctx, 'CLUSTER')
        mock_node.assert_called_once_with(self.ctx, 'NODE3')

    @mock.patch.object(su, 'check_size_params')
    @mock.patch.object(no.Node, 'find')
    @mock.patch.object(co.Cluster, 'find')
    def test_cluster_del_nodes_failed_checking(self, mock_find, mock_node,
                                               mock_check):
        x_cluster = mock.Mock(id='1234', desired_capacity=2)
        mock_find.return_value = x_cluster
        mock_node.return_value = mock.Mock(id='NODE2', cluster_id='1234',
                                           dependents={})
        mock_check.return_value = 'Failed size checking.'
        req = orco.ClusterDelNodesRequest(identity='CLUSTER', nodes=['NODE3'])

        ex = self.assertRaises(rpc.ExpectedException,
                               self.eng.cluster_del_nodes,
                               self.ctx, req.obj_to_primitive())

        self.assertEqual(exc.BadRequest, ex.exc_info[0])
        self.assertEqual("Failed size checking.",
                         six.text_type(ex.exc_info[1]))

        mock_find.assert_called_once_with(self.ctx, 'CLUSTER')
        mock_node.assert_called_once_with(self.ctx, 'NODE3')
        mock_check.assert_called_once_with(x_cluster, 1, strict=True)

    @mock.patch.object(no.Node, 'count_by_cluster')
    @mock.patch.object(su, 'calculate_desired')
    @mock.patch.object(su, 'check_size_params')
    @mock.patch.object(dispatcher, 'start_action')
    @mock.patch.object(am.Action, 'create')
    @mock.patch.object(co.Cluster, 'find')
    def test_cluster_resize_exact_capacity(self, mock_find, mock_action,
                                           notify, mock_check, mock_calc,
                                           mock_count):
        x_cluster = mock.Mock(id='12345678ABCDEFGH')
        mock_find.return_value = x_cluster
        mock_count.return_value = 3
        mock_calc.return_value = 5
        mock_check.return_value = None
        mock_action.return_value = 'ACTION_ID'
        req = orco.ClusterResizeRequest(
            identity='CLUSTER',
            adjustment_type=consts.EXACT_CAPACITY,
            number=5
        )

        res = self.eng.cluster_resize(self.ctx, req.obj_to_primitive())

        self.assertEqual({'action': 'ACTION_ID'}, res)
        mock_find.assert_called_once_with(self.ctx, 'CLUSTER')
        mock_calc.assert_called_once_with(3, consts.EXACT_CAPACITY, 5, None)
        mock_check.assert_called_once_with(x_cluster, 5, None, None, True)
        mock_action.assert_called_once_with(
            self.ctx, '12345678ABCDEFGH', consts.CLUSTER_RESIZE,
            name='cluster_resize_12345678',
            cause=consts.CAUSE_RPC,
            status=am.Action.READY,
            inputs={
                consts.ADJUSTMENT_TYPE: consts.EXACT_CAPACITY,
                consts.ADJUSTMENT_NUMBER: 5,
                consts.ADJUSTMENT_MIN_SIZE: None,
                consts.ADJUSTMENT_MAX_SIZE: None,
                consts.ADJUSTMENT_MIN_STEP: None,
                consts.ADJUSTMENT_STRICT: True
            },
        )
        notify.assert_called_once_with()

    @mock.patch.object(no.Node, 'count_by_cluster')
    @mock.patch.object(su, 'calculate_desired')
    @mock.patch.object(su, 'check_size_params')
    @mock.patch.object(dispatcher, 'start_action')
    @mock.patch.object(am.Action, 'create')
    @mock.patch.object(co.Cluster, 'find')
    def test_cluster_resize_change_in_capacity(self, mock_find, mock_action,
                                               notify, mock_check, mock_calc,
                                               mock_count):
        x_cluster = mock.Mock(id='12345678ABCDEFGH')
        mock_find.return_value = x_cluster
        mock_count.return_value = 2
        mock_calc.return_value = 7
        mock_check.return_value = None
        mock_action.return_value = 'ACTION_ID'
        req = orco.ClusterResizeRequest(
            identity='CLUSTER',
            adjustment_type=consts.CHANGE_IN_CAPACITY,
            number=5
        )

        res = self.eng.cluster_resize(self.ctx, req.obj_to_primitive())

        self.assertEqual({'action': 'ACTION_ID'}, res)
        mock_find.assert_called_once_with(self.ctx, 'CLUSTER')
        mock_calc.assert_called_once_with(2, consts.CHANGE_IN_CAPACITY, 5,
                                          None)
        mock_check.assert_called_once_with(x_cluster, 7, None, None, True)
        mock_action.assert_called_once_with(
            self.ctx, '12345678ABCDEFGH', consts.CLUSTER_RESIZE,
            name='cluster_resize_12345678',
            cause=consts.CAUSE_RPC,
            status=am.Action.READY,
            inputs={
                consts.ADJUSTMENT_TYPE: consts.CHANGE_IN_CAPACITY,
                consts.ADJUSTMENT_NUMBER: 5,
                consts.ADJUSTMENT_MIN_SIZE: None,
                consts.ADJUSTMENT_MAX_SIZE: None,
                consts.ADJUSTMENT_MIN_STEP: None,
                consts.ADJUSTMENT_STRICT: True
            },
        )
        notify.assert_called_once_with()

    @mock.patch.object(no.Node, 'count_by_cluster')
    @mock.patch.object(su, 'calculate_desired')
    @mock.patch.object(su, 'check_size_params')
    @mock.patch.object(dispatcher, 'start_action')
    @mock.patch.object(am.Action, 'create')
    @mock.patch.object(co.Cluster, 'find')
    def test_cluster_resize_change_in_percentage(self, mock_find, mock_action,
                                                 notify, mock_check,
                                                 mock_calc, mock_count):
        x_cluster = mock.Mock(id='12345678ABCDEFGH')
        mock_find.return_value = x_cluster
        mock_count.return_value = 10
        mock_calc.return_value = 8
        mock_check.return_value = None
        mock_action.return_value = 'ACTION_ID'
        req = orco.ClusterResizeRequest(
            identity='CLUSTER',
            adjustment_type=consts.CHANGE_IN_PERCENTAGE,
            number=15.81
        )

        res = self.eng.cluster_resize(self.ctx, req.obj_to_primitive())

        self.assertEqual({'action': 'ACTION_ID'}, res)
        mock_find.assert_called_once_with(self.ctx, 'CLUSTER')
        mock_calc.assert_called_once_with(10, consts.CHANGE_IN_PERCENTAGE,
                                          15.81, None)
        mock_check.assert_called_once_with(x_cluster, 8, None, None, True)
        mock_action.assert_called_once_with(
            self.ctx, '12345678ABCDEFGH', consts.CLUSTER_RESIZE,
            name='cluster_resize_12345678',
            cause=consts.CAUSE_RPC,
            status=am.Action.READY,
            inputs={
                consts.ADJUSTMENT_TYPE: consts.CHANGE_IN_PERCENTAGE,
                consts.ADJUSTMENT_NUMBER: 15.81,
                consts.ADJUSTMENT_MIN_SIZE: None,
                consts.ADJUSTMENT_MAX_SIZE: None,
                consts.ADJUSTMENT_MIN_STEP: None,
                consts.ADJUSTMENT_STRICT: True
            },
        )
        notify.assert_called_once_with()

    def test_cluster_resize_type_missing_number(self):
        req = orco.ClusterResizeRequest(
            identity='CLUSTER',
            adjustment_type=consts.EXACT_CAPACITY
        )

        ex = self.assertRaises(rpc.ExpectedException,
                               self.eng.cluster_resize,
                               self.ctx, req.obj_to_primitive())

        self.assertEqual(exc.BadRequest, ex.exc_info[0])
        self.assertEqual("Missing number value for size adjustment.",
                         six.text_type(ex.exc_info[1]))

    def test_cluster_resize_number_without_type(self):
        req = orco.ClusterResizeRequest(
            identity='CLUSTER',
            number=10
        )

        ex = self.assertRaises(rpc.ExpectedException,
                               self.eng.cluster_resize,
                               self.ctx, req.obj_to_primitive())
        self.assertEqual(exc.BadRequest, ex.exc_info[0])
        self.assertEqual("Missing adjustment_type "
                         "value for size adjustment.",
                         six.text_type(ex.exc_info[1]))

    def test_cluster_resize_bad_number_for_exact_capacity(self):
        req = orco.ClusterResizeRequest(
            identity='CLUSTER',
            adjustment_type=consts.EXACT_CAPACITY,
            number=-5
        )

        ex = self.assertRaises(rpc.ExpectedException,
                               self.eng.cluster_resize,
                               self.ctx, req.obj_to_primitive())

        self.assertEqual(exc.BadRequest, ex.exc_info[0])
        self.assertEqual("The 'number' must be positive integer for "
                         "adjustment type 'EXACT_CAPACITY'.",
                         six.text_type(ex.exc_info[1]))

    @mock.patch.object(co.Cluster, 'find')
    def test_cluster_resize_cluster_not_found(self, mock_find):
        req = orco.ClusterResizeRequest(
            identity='CLUSTER',
            adjustment_type=consts.EXACT_CAPACITY,
            number=10
        )
        mock_find.side_effect = exc.ResourceNotFound(type='cluster',
                                                     id='CLUSTER')

        ex = self.assertRaises(rpc.ExpectedException,
                               self.eng.cluster_resize,
                               self.ctx, req.obj_to_primitive())

        mock_find.assert_called_once_with(self.ctx, 'CLUSTER')
        self.assertEqual(exc.ResourceNotFound, ex.exc_info[0])
        self.assertEqual("The cluster 'CLUSTER' could not be found.",
                         six.text_type(ex.exc_info[1]))
        mock_find.assert_called_once_with(self.ctx, 'CLUSTER')

    @mock.patch.object(su, 'check_size_params')
    @mock.patch.object(no.Node, 'count_by_cluster')
    @mock.patch.object(co.Cluster, 'find')
    def test_cluster_resize_failing_size_check(self, mock_find, mock_count,
                                               mock_check):
        x_cluster = mock.Mock(id='CID')
        mock_find.return_value = x_cluster
        mock_count.return_value = 5
        mock_check.return_value = 'size check.'
        req = orco.ClusterResizeRequest(
            identity='CLUSTER',
            adjustment_type=consts.EXACT_CAPACITY,
            number=5
        )

        ex = self.assertRaises(rpc.ExpectedException,
                               self.eng.cluster_resize,
                               self.ctx, req.obj_to_primitive())

        mock_find.assert_called_once_with(self.ctx, 'CLUSTER')
        mock_count.assert_called_once_with(self.ctx, 'CID')
        mock_check.assert_called_once_with(x_cluster, 5, None, None, True)
        self.assertEqual(exc.BadRequest, ex.exc_info[0])
        self.assertEqual("size check.",
                         six.text_type(ex.exc_info[1]))

    @mock.patch.object(dispatcher, 'start_action')
    @mock.patch.object(am.Action, 'create')
    @mock.patch.object(su, 'check_size_params')
    @mock.patch.object(co.Cluster, 'find')
    def test_cluster_scale_out(self, mock_find, mock_check, mock_action,
                               notify):
        x_cluster = mock.Mock(id='12345678ABCDEFGH', desired_capacity=4)
        mock_find.return_value = x_cluster
        mock_check.return_value = None
        mock_action.return_value = 'ACTION_ID'
        req = orco.ClusterScaleOutRequest(identity='CLUSTER', count=1)

        result = self.eng.cluster_scale_out(self.ctx, req.obj_to_primitive())

        self.assertEqual({'action': 'ACTION_ID'}, result)
        mock_find.assert_called_once_with(self.ctx, 'CLUSTER')
        mock_check.assert_called_once_with(x_cluster, 5)
        mock_action.assert_called_once_with(
            self.ctx, '12345678ABCDEFGH', consts.CLUSTER_SCALE_OUT,
            name='cluster_scale_out_12345678',
            cause=consts.CAUSE_RPC,
            status=am.Action.READY,
            inputs={'count': 1},
        )
        notify.assert_called_once_with()

    @mock.patch.object(co.Cluster, 'find')
    def test_cluster_scale_out_cluster_not_found(self, mock_find):
        mock_find.side_effect = exc.ResourceNotFound(type='cluster',
                                                     id='Bogus')
        req = orco.ClusterScaleOutRequest(identity='Bogus', count=1)

        ex = self.assertRaises(rpc.ExpectedException,
                               self.eng.cluster_scale_out,
                               self.ctx, req.obj_to_primitive())

        self.assertEqual(exc.ResourceNotFound, ex.exc_info[0])
        self.assertEqual("The cluster 'Bogus' could not be found.",
                         six.text_type(ex.exc_info[1]))
        mock_find.assert_called_once_with(self.ctx, 'Bogus')

    @mock.patch.object(dispatcher, 'start_action')
    @mock.patch.object(am.Action, 'create')
    @mock.patch.object(co.Cluster, 'find')
    def test_cluster_scale_out_count_is_none(self, mock_find, mock_action,
                                             notify):
        mock_find.return_value = mock.Mock(id='12345678ABCDEFGH',
                                           desired_capacity=4)
        mock_action.return_value = 'ACTION_ID'
        req = orco.ClusterScaleOutRequest(identity='CLUSTER')

        result = self.eng.cluster_scale_out(self.ctx, req.obj_to_primitive())

        self.assertEqual({'action': 'ACTION_ID'}, result)
        mock_find.assert_called_once_with(self.ctx, 'CLUSTER')
        mock_action.assert_called_once_with(
            self.ctx, '12345678ABCDEFGH', consts.CLUSTER_SCALE_OUT,
            name='cluster_scale_out_12345678',
            cause=consts.CAUSE_RPC,
            status=am.Action.READY,
            inputs={},
        )
        notify.assert_called_once_with()

    @mock.patch.object(co.Cluster, 'find')
    def test_cluster_scale_out_count_zero(self, mock_find):
        mock_find.return_value = mock.Mock(desired_capacity=4)
        req = orco.ClusterScaleOutRequest(identity='CLUSTER', count=0)

        ex = self.assertRaises(rpc.ExpectedException,
                               self.eng.cluster_scale_out,
                               self.ctx, req.obj_to_primitive())

        self.assertEqual(exc.BadRequest, ex.exc_info[0])
        self.assertEqual("Count for scale-out request cannot be 0.",
                         six.text_type(ex.exc_info[1]))

    @mock.patch.object(su, 'check_size_params')
    @mock.patch.object(co.Cluster, 'find')
    def test_cluster_scale_out_failed_size_check(self, mock_find, mock_check):
        x_cluster = mock.Mock(desired_capacity=4)
        mock_find.return_value = x_cluster
        mock_check.return_value = 'size limit'
        req = orco.ClusterScaleOutRequest(identity='CLUSTER', count=2)

        ex = self.assertRaises(rpc.ExpectedException,
                               self.eng.cluster_scale_out,
                               self.ctx, req.obj_to_primitive())

        self.assertEqual(exc.BadRequest, ex.exc_info[0])
        self.assertEqual("size limit.",
                         six.text_type(ex.exc_info[1]))
        mock_find.assert_called_once_with(self.ctx, 'CLUSTER')
        mock_check.assert_called_once_with(x_cluster, 6)

    @mock.patch.object(dispatcher, 'start_action')
    @mock.patch.object(am.Action, 'create')
    @mock.patch.object(su, 'check_size_params')
    @mock.patch.object(co.Cluster, 'find')
    def test_cluster_scale_in(self, mock_find, mock_check, mock_action,
                              notify):
        x_cluster = mock.Mock(id='12345678ABCD', desired_capacity=4)
        mock_find.return_value = x_cluster
        mock_check.return_value = None
        mock_action.return_value = 'ACTION_ID'
        req = orco.ClusterScaleInRequest(identity='CLUSTER', count=2)

        result = self.eng.cluster_scale_in(self.ctx, req.obj_to_primitive())

        self.assertEqual({'action': 'ACTION_ID'}, result)
        mock_find.assert_called_once_with(self.ctx, 'CLUSTER')
        mock_check.assert_called_once_with(x_cluster, 2)
        mock_action.assert_called_once_with(
            self.ctx, '12345678ABCD', consts.CLUSTER_SCALE_IN,
            name='cluster_scale_in_12345678',
            cause=consts.CAUSE_RPC,
            status=am.Action.READY,
            inputs={'count': 2},
        )
        notify.assert_called_once_with()

    @mock.patch.object(co.Cluster, 'find')
    def test_cluster_scale_in_cluster_not_found(self, mock_find):
        mock_find.side_effect = exc.ResourceNotFound(type='cluster',
                                                     id='Bogus')
        req = orco.ClusterScaleInRequest(identity='Bogus', count=2)

        ex = self.assertRaises(rpc.ExpectedException,
                               self.eng.cluster_scale_in,
                               self.ctx, req.obj_to_primitive())

        self.assertEqual(exc.ResourceNotFound, ex.exc_info[0])
        self.assertEqual("The cluster 'Bogus' could not be found.",
                         six.text_type(ex.exc_info[1]))
        mock_find.assert_called_once_with(self.ctx, 'Bogus')

    @mock.patch.object(dispatcher, 'start_action')
    @mock.patch.object(am.Action, 'create')
    @mock.patch.object(co.Cluster, 'find')
    def test_cluster_scale_in_count_is_none(self, mock_find, mock_action,
                                            notify):
        mock_find.return_value = mock.Mock(id='FOO', desired_capacity=4)
        mock_action.return_value = 'ACTION_ID'
        req = orco.ClusterScaleInRequest(identity='CLUSTER')

        result = self.eng.cluster_scale_in(self.ctx, req.obj_to_primitive())

        self.assertEqual({'action': 'ACTION_ID'}, result)
        mock_find.assert_called_once_with(self.ctx, 'CLUSTER')
        mock_action.assert_called_once_with(
            self.ctx, 'FOO', consts.CLUSTER_SCALE_IN,
            name='cluster_scale_in_FOO',
            cause=consts.CAUSE_RPC,
            status=am.Action.READY,
            inputs={},
        )
        notify.assert_called_once_with()

    @mock.patch.object(co.Cluster, 'find')
    def test_cluster_scale_in_count_zero(self, mock_find):
        mock_find.return_value = mock.Mock(desired_capacity=4)
        req = orco.ClusterScaleInRequest(identity='CLUSTER', count=0)

        ex = self.assertRaises(rpc.ExpectedException,
                               self.eng.cluster_scale_in,
                               self.ctx, req.obj_to_primitive())

        self.assertEqual(exc.BadRequest, ex.exc_info[0])
        self.assertEqual("Count for scale-in request cannot be 0.",
                         six.text_type(ex.exc_info[1]))

    @mock.patch.object(su, 'check_size_params')
    @mock.patch.object(co.Cluster, 'find')
    def test_cluster_scale_in_failed_size_check(self, mock_find, mock_check):
        x_cluster = mock.Mock(desired_capacity=4)
        mock_find.return_value = x_cluster
        mock_check.return_value = 'size limit'
        req = orco.ClusterScaleInRequest(identity='FAKE_CLUSTER', count=2)

        ex = self.assertRaises(rpc.ExpectedException,
                               self.eng.cluster_scale_in,
                               self.ctx, req.obj_to_primitive())

        self.assertEqual(exc.BadRequest, ex.exc_info[0])
        self.assertEqual("size limit.",
                         six.text_type(ex.exc_info[1]))
        mock_find.assert_called_once_with(self.ctx, 'FAKE_CLUSTER')
        mock_check.assert_called_once_with(x_cluster, 2)

    @mock.patch.object(am.Action, 'create')
    @mock.patch.object(co.Cluster, 'find')
    @mock.patch.object(dispatcher, 'start_action')
    def test_cluster_check(self, notify, mock_find, mock_action):
        x_cluster = mock.Mock(id='CID', user='USER', project='PROJECT')
        mock_find.return_value = x_cluster
        mock_action.return_value = 'ACTION_ID'
        req = orco.ClusterCheckRequest(identity='C1', params={'foo': 'bar'})

        res = self.eng.cluster_check(self.ctx, req.obj_to_primitive())

        self.assertEqual({'action': 'ACTION_ID'}, res)
        mock_find.assert_called_once_with(self.ctx, 'C1')
        mock_action.assert_called_once_with(
            self.ctx, 'CID', consts.CLUSTER_CHECK,
            name='cluster_check_CID',
            cause=consts.CAUSE_RPC,
            status=am.Action.READY,
            inputs={'foo': 'bar'},
        )
        notify.assert_called_once_with()

    @mock.patch.object(ao.Action, 'delete_by_target')
    @mock.patch.object(am.Action, 'create')
    @mock.patch.object(co.Cluster, 'find')
    @mock.patch.object(dispatcher, 'start_action')
    def test_cluster_check_with_delete(self, notify, mock_find, mock_action,
                                       mock_delete):
        x_cluster = mock.Mock(id='CID', user='USER', project='PROJECT')
        mock_find.return_value = x_cluster
        mock_action.return_value = 'ACTION_ID'
        req = orco.ClusterCheckRequest(identity='C1',
                                       params={'delete_check_action': True})

        res = self.eng.cluster_check(self.ctx, req.obj_to_primitive())

        self.assertEqual({'action': 'ACTION_ID'}, res)
        mock_find.assert_called_once_with(self.ctx, 'C1')
        mock_delete.assert_called_once_with(
            self.ctx, 'CID', action=['CLUSTER_CHECK'],
            status=['SUCCEEDED', 'FAILED']
        )
        mock_action.assert_called_once_with(
            self.ctx, 'CID', consts.CLUSTER_CHECK,
            name='cluster_check_CID',
            cause=consts.CAUSE_RPC,
            status=am.Action.READY,
            inputs={'delete_check_action': True},
        )
        notify.assert_called_once_with()

    @mock.patch.object(am.Action, 'create')
    @mock.patch.object(co.Cluster, 'find')
    @mock.patch.object(dispatcher, 'start_action')
    def test_cluster_check_user_is_none(self, notify, mock_find, mock_action):
        x_cluster = mock.Mock(id='CID', project='PROJECT')
        mock_find.return_value = x_cluster
        mock_action.return_value = 'ACTION_ID'
        req = orco.ClusterCheckRequest(identity='C1')

        result = self.eng.cluster_check(self.ctx, req.obj_to_primitive())

        self.assertIsNotNone(x_cluster.user)
        self.assertEqual({'action': 'ACTION_ID'}, result)
        mock_find.assert_called_once_with(self.ctx, 'C1')
        mock_action.assert_called_once_with(
            self.ctx, 'CID', consts.CLUSTER_CHECK,
            name='cluster_check_CID',
            cause=consts.CAUSE_RPC,
            status=am.Action.READY,
            inputs={},
        )
        notify.assert_called_once_with()

    @mock.patch.object(am.Action, 'create')
    @mock.patch.object(co.Cluster, 'find')
    @mock.patch.object(dispatcher, 'start_action')
    def test_cluster_check_project_is_none(self, notify, mock_find,
                                           mock_action):
        x_cluster = mock.Mock(id='CID', user='USER')
        mock_find.return_value = x_cluster
        mock_action.return_value = 'ACTION_ID'
        req = orco.ClusterCheckRequest(identity='C1')

        result = self.eng.cluster_check(self.ctx, req.obj_to_primitive())

        self.assertIsNotNone(x_cluster.user)
        self.assertEqual({'action': 'ACTION_ID'}, result)
        mock_find.assert_called_once_with(self.ctx, 'C1')
        mock_action.assert_called_once_with(
            self.ctx, 'CID', consts.CLUSTER_CHECK,
            name='cluster_check_CID',
            cause=consts.CAUSE_RPC,
            status=am.Action.READY,
            inputs={},
        )
        notify.assert_called_once_with()

    @mock.patch.object(co.Cluster, 'find')
    def test_cluster_check_cluster_not_found(self, mock_find):
        mock_find.side_effect = exc.ResourceNotFound(type='cluster',
                                                     id='Bogus')
        req = orco.ClusterCheckRequest(identity='C1', params={'foo': 'bar'})

        ex = self.assertRaises(rpc.ExpectedException,
                               self.eng.cluster_check,
                               self.ctx, req.obj_to_primitive())

        self.assertEqual(exc.ResourceNotFound, ex.exc_info[0])
        self.assertEqual("The cluster 'Bogus' could not be found.",
                         six.text_type(ex.exc_info[1]))
        mock_find.assert_called_once_with(self.ctx, 'C1')

    @mock.patch.object(am.Action, 'create')
    @mock.patch.object(co.Cluster, 'find')
    @mock.patch.object(dispatcher, 'start_action')
    def test_cluster_recover(self, notify, mock_find, mock_action):
        x_cluster = mock.Mock(id='CID')
        mock_find.return_value = x_cluster
        mock_action.return_value = 'ACTION_ID'
        req = orco.ClusterRecoverRequest(identity='C1',
                                         params={'operation': 'RECREATE'})

        result = self.eng.cluster_recover(self.ctx, req.obj_to_primitive())

        self.assertEqual({'action': 'ACTION_ID'}, result)
        mock_find.assert_called_once_with(self.ctx, 'C1')
        mock_action.assert_called_once_with(
            self.ctx, 'CID', consts.CLUSTER_RECOVER,
            name='cluster_recover_CID',
            cause=consts.CAUSE_RPC,
            status=am.Action.READY,
            inputs={'operation': 'RECREATE'},
        )
        notify.assert_called_once_with()

    @mock.patch.object(co.Cluster, 'find')
    def test_cluster_recover_cluster_not_found(self, mock_find):
        mock_find.side_effect = exc.ResourceNotFound(type='cluster',
                                                     id='Bogus')
        req = orco.ClusterRecoverRequest(identity='Bogus')

        ex = self.assertRaises(rpc.ExpectedException,
                               self.eng.cluster_recover,
                               self.ctx, req.obj_to_primitive())

        self.assertEqual(exc.ResourceNotFound, ex.exc_info[0])
        self.assertEqual("The cluster 'Bogus' could not be found.",
                         six.text_type(ex.exc_info[1]))
        mock_find.assert_called_once_with(self.ctx, 'Bogus')

    @mock.patch.object(co.Cluster, 'find')
    def test_cluster_recover_invalid(self, mock_find):
        x_cluster = mock.Mock(id='CID')
        mock_find.return_value = x_cluster

        req = orco.ClusterRecoverRequest(identity='Bogus',
                                         params={'bad': 'fake'})

        ex = self.assertRaises(rpc.ExpectedException,
                               self.eng.cluster_recover,
                               self.ctx, req.obj_to_primitive())

        self.assertEqual(exc.BadRequest, ex.exc_info[0])
        self.assertEqual("Action parameter ['bad'] is not recognizable.",
                         six.text_type(ex.exc_info[1]))
        mock_find.assert_called_once_with(self.ctx, 'Bogus')

    @mock.patch.object(am.Action, 'create')
    @mock.patch.object(co.Cluster, 'find')
    @mock.patch.object(dispatcher, 'start_action')
    def test_cluster_recover_user_is_none(self, notify, mock_find,
                                          mock_action):
        x_cluster = mock.Mock(id='CID', project='PROJECT')
        mock_find.return_value = x_cluster
        mock_action.return_value = 'ACTION_ID'
        req = orco.ClusterRecoverRequest(identity='C1')

        result = self.eng.cluster_recover(self.ctx, req.obj_to_primitive())

        self.assertIsNotNone(x_cluster.user)
        self.assertEqual({'action': 'ACTION_ID'}, result)
        mock_find.assert_called_once_with(self.ctx, 'C1')
        mock_action.assert_called_once_with(
            self.ctx, 'CID', consts.CLUSTER_RECOVER,
            name='cluster_recover_CID',
            cause=consts.CAUSE_RPC,
            status=am.Action.READY,
            inputs={},
        )
        notify.assert_called_once_with()

    @mock.patch.object(no.Node, 'find')
    @mock.patch.object(po.Profile, 'get')
    def test__validate_replace_nodes(self, mock_profile, mock_node):
        cluster = mock.Mock(id='CID', profile_id='FAKE_ID')
        mock_profile.return_value = mock.Mock(type='FAKE_TYPE')
        mock_node.side_effect = [
            mock.Mock(id='OLD_ID', cluster_id='CID'),
            mock.Mock(id='NEW_ID', cluster_id='', status=consts.NS_ACTIVE,
                      profile_id='FAKE_ID_1')
        ]

        # do it
        res = self.eng._validate_replace_nodes(self.ctx, cluster,
                                               {'OLD_NODE': 'NEW_NODE'})

        self.assertEqual({'OLD_ID': 'NEW_ID'}, res)
        mock_node.assert_has_calls([
            mock.call(self.ctx, 'OLD_NODE'),
            mock.call(self.ctx, 'NEW_NODE'),
        ])
        mock_profile.assert_has_calls([
            mock.call(self.ctx, 'FAKE_ID', project_safe=True),
            mock.call(self.ctx, 'FAKE_ID_1', project_safe=True)
        ])

    @mock.patch.object(no.Node, 'find')
    @mock.patch.object(po.Profile, 'get')
    def test__validate_replace_nodes_old_missing(self, mock_profile,
                                                 mock_node):
        c = mock.Mock(id='CID', profile_id='FAKE_ID')
        mock_node.side_effect = exc.ResourceNotFound(type='node', id='OLD')

        # do it
        ex = self.assertRaises(exc.BadRequest,
                               self.eng._validate_replace_nodes,
                               self.ctx, c, {'OLD': 'NEW'})

        self.assertIn("Original nodes not found: ['OLD']", six.text_type(ex))
        mock_node.assert_called_once_with(self.ctx, 'OLD')

    @mock.patch.object(no.Node, 'find')
    @mock.patch.object(po.Profile, 'get')
    def test__validate_replace_nodes_new_missing(self, mock_profile,
                                                 mock_node):
        c = mock.Mock(id='CID', profile_id='FAKE_ID')
        mock_node.side_effect = [
            mock.Mock(),
            exc.ResourceNotFound(type='node', id='NEW')
        ]

        # do it
        ex = self.assertRaises(exc.BadRequest,
                               self.eng._validate_replace_nodes,
                               self.ctx, c, {'OLD': 'NEW'})

        self.assertIn("Replacement nodes not found: ['NEW']",
                      six.text_type(ex))
        mock_node.assert_has_calls([
            mock.call(self.ctx, 'OLD'),
            mock.call(self.ctx, 'NEW')
        ])

    @mock.patch.object(no.Node, 'find')
    @mock.patch.object(po.Profile, 'get')
    def test__validate_replace_nodes_old_not_member(self, mock_profile,
                                                    mock_node):
        c = mock.Mock(id='CID', profile_id='FAKE_ID')
        mock_node.side_effect = [
            mock.Mock(cluster_id='OTHER'),
            mock.Mock(cluster_id=''),
        ]

        # do it
        ex = self.assertRaises(exc.BadRequest,
                               self.eng._validate_replace_nodes,
                               self.ctx, c, {'OLD': 'NEW'})

        self.assertIn("The specified nodes ['OLD'] to be replaced are not "
                      "members of the cluster CID.", six.text_type(ex))
        mock_node.assert_has_calls([
            mock.call(self.ctx, 'OLD'),
            mock.call(self.ctx, 'NEW')
        ])

    @mock.patch.object(no.Node, 'find')
    @mock.patch.object(po.Profile, 'get')
    def test__validate_replace_nodes_new_not_orphan(self, mock_profile,
                                                    mock_node):
        c = mock.Mock(id='CID', profile_id='FAKE_ID')
        mock_node.side_effect = [
            mock.Mock(cluster_id='CID'),
            mock.Mock(cluster_id='OTHER'),
        ]

        # do it
        ex = self.assertRaises(exc.BadRequest,
                               self.eng._validate_replace_nodes,
                               self.ctx, c, {'OLD': 'NEW'})

        self.assertIn("Nodes ['NEW'] already member of a cluster.",
                      six.text_type(ex))
        mock_node.assert_has_calls([
            mock.call(self.ctx, 'OLD'),
            mock.call(self.ctx, 'NEW')
        ])

    @mock.patch.object(no.Node, 'find')
    @mock.patch.object(po.Profile, 'get')
    def test__validate_replace_nodes_new_bad_status(self, mock_profile,
                                                    mock_node):
        c = mock.Mock(id='CID', profile_id='FAKE_ID')
        mock_node.side_effect = [
            mock.Mock(cluster_id='CID'),
            mock.Mock(cluster_id='', status=consts.NS_ERROR),
        ]

        # do it
        ex = self.assertRaises(exc.BadRequest,
                               self.eng._validate_replace_nodes,
                               self.ctx, c, {'OLD': 'NEW'})

        self.assertIn("Nodes are not ACTIVE: ['NEW'].", six.text_type(ex))
        mock_node.assert_has_calls([
            mock.call(self.ctx, 'OLD'),
            mock.call(self.ctx, 'NEW')
        ])

    @mock.patch.object(no.Node, 'find')
    @mock.patch.object(po.Profile, 'get')
    def test__validate_replace_nodes_mult_err(self, mock_profile,
                                              mock_node):
        c = mock.Mock(id='CID', profile_id='FAKE_ID')
        mock_node.side_effect = [
            mock.Mock(id='OLD1', cluster_id='CID'),
            mock.Mock(id='NEW1', cluster_id='OTHER', status=consts.NS_ERROR),
        ]

        # do it
        ex = self.assertRaises(exc.BadRequest,
                               self.eng._validate_replace_nodes,
                               self.ctx, c, {'OLD1': 'NEW1'})

        msg1 = _("Nodes ['NEW1'] already member of a cluster.")
        msg2 = _("Nodes are not ACTIVE: ['NEW1'].")
        self.assertIn(msg1, six.text_type(ex))
        self.assertIn(msg2, six.text_type(ex))
        mock_node.assert_has_calls([
            mock.call(self.ctx, 'OLD1'),
            mock.call(self.ctx, 'NEW1'),
        ])

    @mock.patch.object(no.Node, 'find')
    @mock.patch.object(po.Profile, 'get')
    def test__validate_replace_nodes_new_profile_type_mismatch(
            self, mock_profile, mock_node):
        c = mock.Mock(id='CID', profile_id='FAKE_CLUSTER_PROFILE')
        mock_profile.side_effect = [
            mock.Mock(type='FAKE_TYPE'),  # for cluster
            mock.Mock(type='FAKE_TYPE_1'),  # for node
        ]
        mock_node.side_effect = [
            mock.Mock(cluster_id='CID'),
            mock.Mock(cluster_id='', status=consts.NS_ACTIVE,
                      profile_id='FAKE_NODE_PROFILE'),
        ]

        # do it
        ex = self.assertRaises(exc.BadRequest,
                               self.eng._validate_replace_nodes,
                               self.ctx, c, {'OLD': 'NEW'})

        self.assertIn("Profile type of nodes ['NEW'] do not match that of "
                      "the cluster.", six.text_type(ex))
        mock_node.assert_has_calls([
            mock.call(self.ctx, 'OLD'),
            mock.call(self.ctx, 'NEW')
        ])
        mock_profile.assert_has_calls([
            mock.call(self.ctx, 'FAKE_CLUSTER_PROFILE', project_safe=True),
            mock.call(self.ctx, 'FAKE_NODE_PROFILE', project_safe=True)
        ])

    @mock.patch.object(am.Action, 'create')
    @mock.patch.object(service.EngineService, '_validate_replace_nodes')
    @mock.patch.object(no.Node, 'find')
    @mock.patch.object(po.Profile, 'find')
    @mock.patch.object(co.Cluster, 'find')
    @mock.patch.object(dispatcher, 'start_action')
    def test_cluster_replace_nodes(self, notify, mock_find,
                                   mock_profile, mock_node,
                                   mock_validate, mock_action):
        cluster = mock.Mock(id='CID', profile_id='FAKE_ID')
        mock_find.return_value = cluster
        mock_profile.return_value = mock.Mock(type='FAKE_TYPE')
        old_node = mock.Mock(id='ORIGIN', cluster_id='CID', status='ACTIVE')
        new_node = mock.Mock(id='REPLACE', cluster_id='', status='ACTIVE',
                             profile_id='FAKE_ID_1')
        mock_node.side_effect = [old_node, new_node]
        mock_action.return_value = 'ACTION_ID'
        param = {'ORIGINAL': 'REPLACE'}
        mock_validate.return_value = param
        req = orco.ClusterReplaceNodesRequest(identity='CLUSTER', nodes=param)

        # do it
        res = self.eng.cluster_replace_nodes(self.ctx, req.obj_to_primitive())

        # verify
        self.assertEqual({'action': 'ACTION_ID'}, res)
        mock_find.assert_called_once_with(self.ctx, 'CLUSTER')
        mock_validate.assert_called_once_with(self.ctx, cluster, param)
        mock_action.assert_called_once_with(
            self.ctx, 'CID', consts.CLUSTER_REPLACE_NODES,
            name='cluster_replace_nodes_CID',
            cause=consts.CAUSE_RPC,
            status=am.Action.READY,
            inputs={'ORIGINAL': 'REPLACE'})
        notify.assert_called_once_with()

    @mock.patch.object(service.EngineService, '_validate_replace_nodes')
    @mock.patch.object(co.Cluster, 'find')
    def test_cluster_replace_nodes_failed_validate(self, mock_find, mock_chk):
        nodes = {'OLD': 'NEW'}
        cluster = mock.Mock()
        mock_find.return_value = cluster
        mock_chk.side_effect = exc.BadRequest(msg='failed')
        req = orco.ClusterReplaceNodesRequest(identity='CLUSTER', nodes=nodes)

        # do it
        ex = self.assertRaises(rpc.ExpectedException,
                               self.eng.cluster_replace_nodes,
                               self.ctx, req.obj_to_primitive())

        self.assertEqual(exc.BadRequest, ex.exc_info[0])
        self.assertEqual("failed.", six.text_type(ex.exc_info[1]))
        mock_find.assert_called_once_with(self.ctx, 'CLUSTER')
        mock_chk.assert_called_once_with(self.ctx, cluster, nodes)

    @mock.patch.object(nm.Node, 'load')
    @mock.patch.object(no.Node, 'get_all_by_cluster')
    @mock.patch.object(co.Cluster, 'find')
    def test_cluster_collect(self, mock_find, mock_get, mock_load):
        x_cluster = mock.Mock(id='FAKE_CLUSTER')
        mock_find.return_value = x_cluster
        x_obj_1 = mock.Mock(id='NODE1', physical_id='PHYID1')
        x_obj_1.to_dict.return_value = {'name': 'node1'}
        x_obj_2 = mock.Mock(id='NODE2', physical_id='PHYID2')
        x_obj_2.to_dict.return_value = {'name': 'node2'}
        x_node_1 = mock.Mock()
        x_node_2 = mock.Mock()
        x_node_1.get_details.return_value = {'ip': '1.2.3.4'}
        x_node_2.get_details.return_value = {'ip': '5.6.7.8'}
        mock_get.return_value = [x_obj_1, x_obj_2]
        mock_load.side_effect = [x_node_1, x_node_2]
        req = orco.ClusterCollectRequest(identity='CLUSTER_ID',
                                         path='details.ip')

        res = self.eng.cluster_collect(self.ctx, req.obj_to_primitive())

        self.assertIn('cluster_attributes', res)
        self.assertIn({'id': 'NODE1', 'value': '1.2.3.4'},
                      res['cluster_attributes'])
        self.assertIn({'id': 'NODE2', 'value': '5.6.7.8'},
                      res['cluster_attributes'])
        mock_find.assert_called_once_with(self.ctx, 'CLUSTER_ID')
        mock_get.assert_called_once_with(self.ctx, 'FAKE_CLUSTER')
        mock_load.assert_has_calls([
            mock.call(self.ctx, db_node=x_obj_1),
            mock.call(self.ctx, db_node=x_obj_2)
        ])
        x_obj_1.to_dict.assert_called_once_with()
        x_node_1.get_details.assert_called_once_with(self.ctx)
        x_obj_2.to_dict.assert_called_once_with()
        x_node_2.get_details.assert_called_once_with(self.ctx)

    @mock.patch.object(co.Cluster, 'find')
    @mock.patch.object(common_utils, 'get_path_parser')
    def test_cluster_collect_bad_path(self, mock_parser, mock_find):
        mock_parser.side_effect = exc.BadRequest(msg='Boom')
        req = orco.ClusterCollectRequest(identity='CLUSTER_ID', path='foo.bar')

        err = self.assertRaises(rpc.ExpectedException,
                                self.eng.cluster_collect,
                                self.ctx, req.obj_to_primitive())

        self.assertEqual(exc.BadRequest, err.exc_info[0])
        mock_parser.assert_called_once_with('foo.bar')
        self.assertEqual(0, mock_find.call_count)

    @mock.patch.object(no.Node, 'get_all_by_cluster')
    @mock.patch.object(co.Cluster, 'find')
    def test_cluster_collect_cluster_not_found(self, mock_find, mock_get):
        cid = 'FAKE_CLUSTER'
        mock_find.side_effect = exc.ResourceNotFound(type='cluster', id=cid)
        req = orco.ClusterCollectRequest(identity=cid, path='foo.bar')

        err = self.assertRaises(rpc.ExpectedException,
                                self.eng.cluster_collect,
                                self.ctx, req.obj_to_primitive())

        self.assertEqual(exc.ResourceNotFound, err.exc_info[0])
        mock_find.assert_called_once_with(self.ctx, cid)
        self.assertEqual(0, mock_get.call_count)

    @mock.patch.object(no.Node, 'get_all_by_cluster')
    @mock.patch.object(co.Cluster, 'find')
    def test_cluster_collect_no_nodes(self, mock_find, mock_get):
        x_cluster = mock.Mock(id='FAKE_CLUSTER')
        mock_find.return_value = x_cluster
        mock_get.return_value = []
        req = orco.ClusterCollectRequest(identity='CLUSTER_ID', path='barr')

        res = self.eng.cluster_collect(self.ctx, req.obj_to_primitive())

        self.assertEqual({'cluster_attributes': []}, res)
        mock_find.assert_called_once_with(self.ctx, 'CLUSTER_ID')
        mock_get.assert_called_once_with(self.ctx, 'FAKE_CLUSTER')

    @mock.patch.object(no.Node, 'get_all_by_cluster')
    @mock.patch.object(co.Cluster, 'find')
    def test_cluster_collect_no_details(self, mock_find, mock_get):
        x_cluster = mock.Mock(id='FAKE_CLUSTER')
        mock_find.return_value = x_cluster
        x_node_1 = mock.Mock(id='NODE1', physical_id=None)
        x_node_1.to_dict.return_value = {'name': 'node1'}
        x_node_2 = mock.Mock(id='NODE2', physical_id=None)
        x_node_2.to_dict.return_value = {'name': 'node2'}
        mock_get.return_value = [x_node_1, x_node_2]
        req = orco.ClusterCollectRequest(identity='CLUSTER_ID', path='name')

        res = self.eng.cluster_collect(self.ctx, req.obj_to_primitive())

        self.assertIn('cluster_attributes', res)
        self.assertIn({'id': 'NODE1', 'value': 'node1'},
                      res['cluster_attributes'])
        self.assertIn({'id': 'NODE2', 'value': 'node2'},
                      res['cluster_attributes'])
        mock_find.assert_called_once_with(self.ctx, 'CLUSTER_ID')
        mock_get.assert_called_once_with(self.ctx, 'FAKE_CLUSTER')
        x_node_1.to_dict.assert_called_once_with()
        self.assertEqual(0, x_node_1.get_details.call_count)
        x_node_2.to_dict.assert_called_once_with()
        self.assertEqual(0, x_node_2.get_details.call_count)

    @mock.patch.object(no.Node, 'get_all_by_cluster')
    @mock.patch.object(co.Cluster, 'find')
    def test_cluster_collect_no_match(self, mock_find, mock_get):
        x_cluster = mock.Mock(id='FAKE_CLUSTER')
        mock_find.return_value = x_cluster
        x_node_1 = mock.Mock(physical_id=None)
        x_node_1.to_dict.return_value = {'name': 'node1'}
        x_node_2 = mock.Mock(physical_id=None)
        x_node_2.to_dict.return_value = {'name': 'node2'}
        mock_get.return_value = [x_node_1, x_node_2]
        req = orco.ClusterCollectRequest(identity='CLUSTER_ID', path='bogus')

        res = self.eng.cluster_collect(self.ctx, req.obj_to_primitive())

        self.assertEqual({'cluster_attributes': []}, res)
        mock_find.assert_called_once_with(self.ctx, 'CLUSTER_ID')
        mock_get.assert_called_once_with(self.ctx, 'FAKE_CLUSTER')
        x_node_1.to_dict.assert_called_once_with()
        self.assertEqual(0, x_node_1.get_details.call_count)
        x_node_2.to_dict.assert_called_once_with()
        self.assertEqual(0, x_node_2.get_details.call_count)

    @mock.patch.object(am.Action, 'create')
    @mock.patch.object(ro.Receiver, 'get_all')
    @mock.patch.object(cpo.ClusterPolicy, 'get_all')
    @mock.patch.object(co.Cluster, 'find')
    @mock.patch.object(dispatcher, 'start_action')
    def test_cluster_delete(self, notify, mock_find, mock_policies,
                            mock_receivers, mock_action):
        x_obj = mock.Mock(id='12345678AB', status='ACTIVE', dependents={})
        mock_find.return_value = x_obj
        mock_policies.return_value = []
        mock_receivers.return_value = []
        mock_action.return_value = 'ACTION_ID'
        req = orco.ClusterDeleteRequest(identity='IDENTITY', force=False)

        result = self.eng.cluster_delete(self.ctx, req.obj_to_primitive())

        self.assertEqual({'action': 'ACTION_ID'}, result)
        mock_find.assert_called_once_with(self.ctx, 'IDENTITY')
        mock_policies.assert_called_once_with(self.ctx, '12345678AB')
        mock_receivers.assert_called_once_with(
            self.ctx, filters={'cluster_id': '12345678AB'})
        mock_action.assert_called_once_with(
            self.ctx, '12345678AB', 'CLUSTER_DELETE',
            name='cluster_delete_12345678',
            cause=consts.CAUSE_RPC,
            status=am.Action.READY)

        notify.assert_called_once_with()

    @mock.patch.object(co.Cluster, 'find')
    def test_cluster_delete_with_containers(self, mock_find):
        dependents = {'profiles': ['profile1']}
        cluster = mock.Mock(id='cluster1', status='ACTIVE',
                            dependents=dependents)
        mock_find.return_value = cluster
        req = orco.ClusterDeleteRequest(identity='FAKE_CLUSTER',
                                        force=False)

        ex = self.assertRaises(rpc.ExpectedException,
                               self.eng.cluster_delete,
                               self.ctx, req.obj_to_primitive())

        msg = _("The cluster 'FAKE_CLUSTER' cannot be deleted: still "
                "referenced by profile(s): ['profile1'].")
        self.assertEqual(exc.ResourceInUse, ex.exc_info[0])
        self.assertEqual(msg, six.text_type(ex.exc_info[1]))

    @mock.patch.object(co.Cluster, 'find')
    def test_cluster_delete_not_found(self, mock_find):
        mock_find.side_effect = exc.ResourceNotFound(type='cluster',
                                                     id='Bogus')
        req = orco.ClusterDeleteRequest(identity='Bogus',
                                        force=False)

        ex = self.assertRaises(rpc.ExpectedException,
                               self.eng.cluster_delete,
                               self.ctx, req.obj_to_primitive())

        self.assertEqual(exc.ResourceNotFound, ex.exc_info[0])
        self.assertEqual("The cluster 'Bogus' could not be found.",
                         six.text_type(ex.exc_info[1]))

    @mock.patch.object(co.Cluster, 'find')
    def test_cluster_delete_improper_status(self, mock_find):
        for bad_status in [consts.CS_CREATING, consts.CS_UPDATING,
                           consts.CS_DELETING, consts.CS_RECOVERING]:
            fake_cluster = mock.Mock(id='12345678AB', status=bad_status)
            mock_find.return_value = fake_cluster
            req = orco.ClusterDeleteRequest(identity='BUSY',
                                            force=False)

            ex = self.assertRaises(rpc.ExpectedException,
                                   self.eng.cluster_delete,
                                   self.ctx, req.obj_to_primitive())

            self.assertEqual(exc.ActionInProgress, ex.exc_info[0])
            self.assertEqual(
                "The cluster 'BUSY' is in status %s." % bad_status,
                six.text_type(ex.exc_info[1]))

    @mock.patch.object(cpo.ClusterPolicy, 'get_all')
    @mock.patch.object(co.Cluster, 'find')
    def test_cluster_delete_policy_attached(self, mock_find, mock_policies):
        x_obj = mock.Mock(id='12345678AB', dependents={})
        mock_find.return_value = x_obj
        mock_policies.return_value = [mock.Mock()]
        req = orco.ClusterDeleteRequest(identity='IDENTITY',
                                        force=False)

        ex = self.assertRaises(rpc.ExpectedException,
                               self.eng.cluster_delete,
                               self.ctx, req.obj_to_primitive())

        self.assertEqual(exc.ResourceInUse, ex.exc_info[0])
        expected_msg = _("The cluster 'IDENTITY' cannot be deleted: "
                         "there is still policy(s) attached to it.")
        self.assertEqual(expected_msg, six.text_type(ex.exc_info[1]))
        mock_find.assert_called_once_with(self.ctx, 'IDENTITY')
        mock_policies.assert_called_once_with(self.ctx, '12345678AB')

    @mock.patch.object(ro.Receiver, 'get_all')
    @mock.patch.object(cpo.ClusterPolicy, 'get_all')
    @mock.patch.object(co.Cluster, 'find')
    def test_cluster_delete_with_receiver(self, mock_find, mock_policies,
                                          mock_receivers):
        x_obj = mock.Mock(id='12345678AB', dependents={})
        mock_find.return_value = x_obj
        mock_policies.return_value = []
        mock_receivers.return_value = [mock.Mock()]
        req = orco.ClusterDeleteRequest(identity='IDENTITY',
                                        force=False)

        ex = self.assertRaises(rpc.ExpectedException,
                               self.eng.cluster_delete,
                               self.ctx, req.obj_to_primitive())

        self.assertEqual(exc.ResourceInUse, ex.exc_info[0])
        expected_msg = _("The cluster 'IDENTITY' cannot be deleted: "
                         "there is still receiver(s) associated with it.")
        self.assertEqual(expected_msg, six.text_type(ex.exc_info[1]))
        mock_find.assert_called_once_with(self.ctx, 'IDENTITY')
        mock_policies.assert_called_once_with(self.ctx, '12345678AB')
        mock_receivers.assert_called_once_with(
            self.ctx, filters={'cluster_id': '12345678AB'})

    @mock.patch.object(ro.Receiver, 'get_all')
    @mock.patch.object(cpo.ClusterPolicy, 'get_all')
    @mock.patch.object(co.Cluster, 'find')
    def test_cluster_delete_mult_err(self, mock_find, mock_policies,
                                     mock_receivers):
        x_obj = mock.Mock(id='12345678AB', dependents={})
        mock_find.return_value = x_obj
        mock_policies.return_value = [mock.Mock()]
        mock_receivers.return_value = [mock.Mock()]
        req = orco.ClusterDeleteRequest(identity='IDENTITY',
                                        force=False)

        ex = self.assertRaises(rpc.ExpectedException,
                               self.eng.cluster_delete,
                               self.ctx, req.obj_to_primitive())

        self.assertEqual(exc.ResourceInUse, ex.exc_info[0])
        self.assertIn('there is still policy(s) attached to it.',
                      six.text_type(ex.exc_info[1]))
        self.assertIn('there is still receiver(s) associated with it.',
                      six.text_type(ex.exc_info[1]))
        mock_find.assert_called_once_with(self.ctx, 'IDENTITY')
        mock_policies.assert_called_once_with(self.ctx, '12345678AB')
        mock_receivers.assert_called_once_with(
            self.ctx, filters={'cluster_id': '12345678AB'})

    @mock.patch.object(am.Action, 'create')
    @mock.patch.object(ro.Receiver, 'get_all')
    @mock.patch.object(cpo.ClusterPolicy, 'get_all')
    @mock.patch.object(co.Cluster, 'find')
    @mock.patch.object(dispatcher, 'start_action')
    def test_cluster_delete_force(self, notify, mock_find, mock_policies,
                                  mock_receivers, mock_action):
        for bad_status in [consts.CS_CREATING, consts.CS_UPDATING,
                           consts.CS_DELETING, consts.CS_RECOVERING]:
            x_obj = mock.Mock(id='12345678AB', status=bad_status,
                              dependents={})
            mock_find.return_value = x_obj
            mock_policies.return_value = []
            mock_receivers.return_value = []
            mock_action.return_value = 'ACTION_ID'
            req = orco.ClusterDeleteRequest(identity='IDENTITY', force=True)

            result = self.eng.cluster_delete(self.ctx, req.obj_to_primitive())

            self.assertEqual({'action': 'ACTION_ID'}, result)
            mock_find.assert_called_with(self.ctx, 'IDENTITY')
            mock_policies.assert_called_with(self.ctx, '12345678AB')
            mock_receivers.assert_called_with(
                self.ctx, filters={'cluster_id': '12345678AB'})
            mock_action.assert_called_with(
                self.ctx, '12345678AB', 'CLUSTER_DELETE',
                name='cluster_delete_12345678',
                cause=consts.CAUSE_RPC,
                status=am.Action.READY)

            notify.assert_called_with()

    @mock.patch.object(ca, 'CompleteLifecycleProc')
    def test_cluster_complete_lifecycle(self, mock_lifecycle):
        req = orco.ClusterCompleteLifecycleRequest(
            identity='CLUSTER', lifecycle_action_token='NODE_ACTION_ID')

        # do it
        res = self.eng.cluster_complete_lifecycle(self.ctx,
                                                  req.obj_to_primitive())

        # verify
        self.assertEqual({'action': 'NODE_ACTION_ID'}, res)
        mock_lifecycle.assert_called_once_with(self.ctx, 'NODE_ACTION_ID')
