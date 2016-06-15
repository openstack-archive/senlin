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
from senlin.engine import cluster as cm
from senlin.engine import dispatcher
from senlin.engine import node as nm
from senlin.engine import service
from senlin.objects import cluster as co
from senlin.objects import cluster_policy as cpo
from senlin.objects import receiver as ro
from senlin.tests.unit.common import base
from senlin.tests.unit.common import utils


class ClusterTest(base.SenlinTestCase):

    def setUp(self):
        super(ClusterTest, self).setUp()

        self.ctx = utils.dummy_context(project='cluster_test_project')
        self.eng = service.EngineService('host-a', 'topic-a')

    @mock.patch.object(co.Cluster, 'get')
    def test_cluster_find_by_uuid(self, mock_get):
        x_cluster = mock.Mock()
        mock_get.return_value = x_cluster

        aid = uuidutils.generate_uuid()
        result = self.eng.cluster_find(self.ctx, aid)

        self.assertEqual(x_cluster, result)
        mock_get.assert_called_once_with(self.ctx, aid, project_safe=True)

    @mock.patch.object(co.Cluster, 'get_by_name')
    @mock.patch.object(co.Cluster, 'get')
    def test_cluster_find_by_uuid_as_name(self, mock_get, mock_get_name):
        x_cluster = mock.Mock()
        mock_get_name.return_value = x_cluster
        mock_get.return_value = None

        aid = uuidutils.generate_uuid()
        result = self.eng.cluster_find(self.ctx, aid, False)

        self.assertEqual(x_cluster, result)
        mock_get.assert_called_once_with(self.ctx, aid, project_safe=False)
        mock_get_name.assert_called_once_with(self.ctx, aid,
                                              project_safe=False)

    @mock.patch.object(co.Cluster, 'get_by_name')
    def test_cluster_find_by_name(self, mock_get_name):
        x_cluster = mock.Mock()
        mock_get_name.return_value = x_cluster

        aid = 'this-is-not-uuid'
        result = self.eng.cluster_find(self.ctx, aid)

        self.assertEqual(x_cluster, result)
        mock_get_name.assert_called_once_with(self.ctx, aid, project_safe=True)

    @mock.patch.object(co.Cluster, 'get_by_short_id')
    @mock.patch.object(co.Cluster, 'get_by_name')
    def test_cluster_find_by_shortid(self, mock_get_name, mock_get_shortid):
        x_cluster = mock.Mock()
        mock_get_shortid.return_value = x_cluster
        mock_get_name.return_value = None

        aid = 'abcd-1234-abcd'
        result = self.eng.cluster_find(self.ctx, aid, False)

        self.assertEqual(x_cluster, result)
        mock_get_name.assert_called_once_with(self.ctx, aid,
                                              project_safe=False)
        mock_get_shortid.assert_called_once_with(self.ctx, aid,
                                                 project_safe=False)

    @mock.patch.object(co.Cluster, 'get_by_name')
    def test_cluster_find_not_found(self, mock_get_name):
        mock_get_name.return_value = None

        ex = self.assertRaises(exc.ClusterNotFound,
                               self.eng.cluster_find,
                               self.ctx, 'bogus')

        self.assertEqual('The cluster (bogus) could not be found.',
                         six.text_type(ex))
        mock_get_name.assert_called_once_with(self.ctx, 'bogus',
                                              project_safe=True)

    @mock.patch.object(cm.Cluster, 'load_all')
    def test_cluster_list(self, mock_load):
        x_obj_1 = mock.Mock()
        x_obj_1.to_dict.return_value = {'k': 'v1'}
        x_obj_2 = mock.Mock()
        x_obj_2.to_dict.return_value = {'k': 'v2'}
        mock_load.return_value = [x_obj_1, x_obj_2]

        result = self.eng.cluster_list(self.ctx)

        self.assertEqual([{'k': 'v1'}, {'k': 'v2'}], result)
        mock_load.assert_called_once_with(self.ctx, limit=None, marker=None,
                                          filters=None, sort=None,
                                          project_safe=True)

    @mock.patch.object(cm.Cluster, 'load_all')
    def test_cluster_list_with_params(self, mock_load):
        mock_load.return_value = []

        result = self.eng.cluster_list(self.ctx, limit=10, marker='KEY',
                                       filters={'foo': 'bar'}, sort='name:asc',
                                       project_safe=True)

        self.assertEqual([], result)
        mock_load.assert_called_once_with(self.ctx, limit=10, marker='KEY',
                                          filters={'foo': 'bar'},
                                          sort='name:asc',
                                          project_safe=True)

    def test_cluster_list_bad_param(self):
        ex = self.assertRaises(rpc.ExpectedException,
                               self.eng.cluster_list,
                               self.ctx, limit='no')
        self.assertEqual(exc.InvalidParameter, ex.exc_info[0])

        ex = self.assertRaises(rpc.ExpectedException,
                               self.eng.cluster_list,
                               self.ctx, sort='crazykey')
        self.assertEqual(exc.InvalidParameter, ex.exc_info[0])

        ex = self.assertRaises(rpc.ExpectedException,
                               self.eng.cluster_list,
                               self.ctx, project_safe='no')
        self.assertEqual(exc.InvalidParameter, ex.exc_info[0])

    @mock.patch.object(cm.Cluster, 'load_all')
    def test_cluster_list_with_project_safe(self, mock_load):
        mock_load.return_value = []

        result = self.eng.cluster_list(self.ctx)
        self.assertEqual([], result)
        mock_load.assert_called_once_with(self.ctx, filters=None, limit=None,
                                          sort=None, marker=None,
                                          project_safe=True)
        mock_load.reset_mock()

        ex = self.assertRaises(rpc.ExpectedException,
                               self.eng.cluster_list,
                               self.ctx, project_safe=False)
        self.assertEqual(exc.Forbidden, ex.exc_info[0])

        self.ctx.is_admin = True

        result = self.eng.cluster_list(self.ctx)
        self.assertEqual([], result)
        mock_load.assert_called_once_with(self.ctx, filters=None, limit=None,
                                          sort=None, marker=None,
                                          project_safe=True)
        mock_load.reset_mock()

        result = self.eng.cluster_list(self.ctx, project_safe=True)
        self.assertEqual([], result)
        mock_load.assert_called_once_with(self.ctx, filters=None, limit=None,
                                          sort=None, marker=None,
                                          project_safe=True)
        mock_load.reset_mock()

        result = self.eng.cluster_list(self.ctx, project_safe=False)
        self.assertEqual([], result)
        mock_load.assert_called_once_with(self.ctx, filters=None, limit=None,
                                          sort=None, marker=None,
                                          project_safe=False)

    @mock.patch.object(cm.Cluster, 'load')
    @mock.patch.object(service.EngineService, 'cluster_find')
    def test_cluster_get(self, mock_find, mock_load):
        x_obj = mock.Mock()
        mock_find.return_value = x_obj
        x_cluster = mock.Mock()
        x_cluster.to_dict.return_value = {'foo': 'bar'}
        mock_load.return_value = x_cluster

        result = self.eng.cluster_get(self.ctx, 'CLUSTER')

        self.assertEqual({'foo': 'bar'}, result)
        mock_find.assert_called_once_with(self.ctx, 'CLUSTER')
        mock_load.assert_called_once_with(self.ctx, dbcluster=x_obj)

    @mock.patch.object(service.EngineService, 'cluster_find')
    def test_cluster_get_not_found(self, mock_find):
        mock_find.side_effect = exc.ClusterNotFound(cluster='Bogus')

        ex = self.assertRaises(rpc.ExpectedException,
                               self.eng.cluster_get,
                               self.ctx, 'Bogus')
        self.assertEqual(exc.ClusterNotFound, ex.exc_info[0])

    @mock.patch.object(service.EngineService, 'check_cluster_quota')
    @mock.patch.object(su, 'check_size_params')
    @mock.patch.object(am.Action, 'create')
    @mock.patch("senlin.engine.cluster.Cluster")
    @mock.patch.object(service.EngineService, 'profile_find')
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

        result = self.eng.cluster_create(self.ctx, 'C1', 3, 'PROFILE')

        self.assertEqual({'action': 'ACTION_ID', 'foo': 'bar'}, result)
        mock_profile.assert_called_once_with(self.ctx, 'PROFILE')
        mock_check.assert_called_once_with(None, 3, None, None, True)
        mock_cluster.assert_called_once_with(
            'C1', 3, 'PROFILE_ID',
            min_size=None, max_size=None, timeout=3600, metadata=None,
            user=self.ctx.user, project=self.ctx.project,
            domain=self.ctx.domain)
        x_cluster.store.assert_called_once_with(self.ctx)
        mock_action.assert_called_once_with(
            self.ctx,
            '12345678ABC', 'CLUSTER_CREATE',
            name='cluster_create_12345678',
            cause=am.CAUSE_RPC,
            status=am.Action.READY,
        )
        notify.assert_called_once_with()

    @mock.patch.object(co.Cluster, 'count_all')
    def test_check_cluster_quota(self, mock_count):
        mock_count.return_value = 10
        cfg.CONF.set_override('max_clusters_per_project', 11,
                              enforce_type=True)

        res = self.eng.check_cluster_quota(self.ctx)

        self.assertIsNone(res)
        mock_count.assert_called_once_with(self.ctx)

    @mock.patch.object(co.Cluster, 'count_all')
    def test_check_cluster_quota_failed(self, mock_count):
        mock_count.return_value = 11
        cfg.CONF.set_override('max_clusters_per_project', 11,
                              enforce_type=True)

        ex = self.assertRaises(exc.Forbidden,
                               self.eng.check_cluster_quota, self.ctx)
        self.assertEqual("You are not authorized to complete this "
                         "operation.",
                         six.text_type(ex))

    @mock.patch.object(service.EngineService, 'check_cluster_quota')
    def test_cluster_create_exceeding_quota(self, mock_quota):
        mock_quota.side_effect = exc.Forbidden()

        ex = self.assertRaises(rpc.ExpectedException,
                               self.eng.cluster_create,
                               self.ctx, 'CLUSTER', 123, 'PROFILE')

        self.assertEqual(exc.Forbidden, ex.exc_info[0])
        self.assertEqual("You are not authorized to complete this "
                         "operation.",
                         six.text_type(ex.exc_info[1]))
        mock_quota.assert_called_once_with(self.ctx)

    @mock.patch.object(service.EngineService, 'check_cluster_quota')
    @mock.patch.object(co.Cluster, 'get_by_name')
    def test_cluster_create_already_exists(self, mock_get, mock_quota):
        mock_quota.return_value = None
        cfg.CONF.set_override('name_unique', True, enforce_type=True)

        x_cluster = mock.Mock()
        mock_get.return_value = x_cluster

        ex = self.assertRaises(rpc.ExpectedException,
                               self.eng.cluster_create,
                               self.ctx, 'CLUSTER', 123, 'PROFILE')

        self.assertEqual(exc.BadRequest, ex.exc_info[0])
        self.assertEqual(_("The request is malformed: The cluster (CLUSTER) "
                           "already exists."),
                         six.text_type(ex.exc_info[1]))
        mock_get.assert_called_once_with(self.ctx, 'CLUSTER')

    @mock.patch.object(service.EngineService, 'check_cluster_quota')
    @mock.patch.object(service.EngineService, 'profile_find')
    def test_cluster_create_profile_not_found(self, mock_find, mock_quota):
        mock_quota.return_value = None
        mock_find.side_effect = exc.ProfileNotFound(profile='Bogus')

        ex = self.assertRaises(rpc.ExpectedException,
                               self.eng.cluster_create,
                               self.ctx, 'CLUSTER', 2, 'Bogus')

        self.assertEqual(exc.BadRequest, ex.exc_info[0])
        self.assertEqual("The request is malformed: "
                         "The specified profile 'Bogus' is not found.",
                         six.text_type(ex.exc_info[1]))
        mock_find.assert_called_once_with(self.ctx, 'Bogus')

    @mock.patch.object(service.EngineService, 'check_cluster_quota')
    @mock.patch.object(service.EngineService, 'profile_find')
    def test_cluster_create_bad_desired_capacity(self, mock_find, mock_quota):
        mock_quota.return_value = None
        mock_find.return_value = mock.Mock()

        ex = self.assertRaises(rpc.ExpectedException,
                               self.eng.cluster_create,
                               self.ctx, 'CLUSTER', -2, 'PROFILE')

        self.assertEqual(exc.InvalidParameter, ex.exc_info[0])
        self.assertEqual("Invalid value '-2' specified for 'desired_capacity'",
                         six.text_type(ex.exc_info[1]))
        mock_find.assert_called_once_with(self.ctx, 'PROFILE')

    @mock.patch.object(service.EngineService, 'check_cluster_quota')
    @mock.patch.object(service.EngineService, 'profile_find')
    def test_cluster_create_bad_min_size(self, mock_find, mock_quota):
        mock_quota.return_value = None
        mock_find.return_value = mock.Mock()

        ex = self.assertRaises(rpc.ExpectedException,
                               self.eng.cluster_create,
                               self.ctx, 'CLUSTER', 2, 'PROFILE', min_size=-1)

        self.assertEqual(exc.InvalidParameter, ex.exc_info[0])
        self.assertEqual("Invalid value '-1' specified for 'min_size'",
                         six.text_type(ex.exc_info[1]))
        mock_find.assert_called_once_with(self.ctx, 'PROFILE')

    @mock.patch.object(service.EngineService, 'check_cluster_quota')
    @mock.patch.object(service.EngineService, 'profile_find')
    def test_cluster_create_bad_max_size(self, mock_find, mock_quota):
        mock_quota.return_value = None
        mock_find.return_value = mock.Mock()

        ex = self.assertRaises(rpc.ExpectedException,
                               self.eng.cluster_create,
                               self.ctx, 'CLUSTER', 2, 'PROFILE',
                               max_size='BIG')

        self.assertEqual(exc.InvalidParameter, ex.exc_info[0])
        self.assertEqual("Invalid value 'BIG' specified for 'max_size'",
                         six.text_type(ex.exc_info[1]))
        mock_find.assert_called_once_with(self.ctx, 'PROFILE')

    @mock.patch.object(service.EngineService, 'check_cluster_quota')
    @mock.patch.object(service.EngineService, 'profile_find')
    def test_cluster_create_bad_timeout(self, mock_find, mock_quota):
        mock_quota.return_value = None
        mock_find.return_value = mock.Mock()

        ex = self.assertRaises(rpc.ExpectedException,
                               self.eng.cluster_create,
                               self.ctx, 'CLUSTER', 2, 'PROFILE', timeout=-1)

        self.assertEqual(exc.InvalidParameter, ex.exc_info[0])
        self.assertEqual("Invalid value '-1' specified for 'timeout'",
                         six.text_type(ex.exc_info[1]))
        mock_find.assert_called_once_with(self.ctx, 'PROFILE')

    @mock.patch.object(service.EngineService, 'check_cluster_quota')
    @mock.patch.object(service.EngineService, 'profile_find')
    def test_cluster_create_failed_checking(self, mock_find, mock_quota):
        mock_quota.return_value = None
        mock_find.return_value = mock.Mock()

        ex = self.assertRaises(rpc.ExpectedException,
                               self.eng.cluster_create,
                               self.ctx, 'CLUSTER', 2, 'PROFILE',
                               min_size=3)

        self.assertEqual(exc.BadRequest, ex.exc_info[0])
        self.assertEqual("The request is malformed: The target capacity (2) "
                         "is less than the specified min_size (3).",
                         six.text_type(ex.exc_info[1]))
        mock_find.assert_called_once_with(self.ctx, 'PROFILE')

    @mock.patch.object(am.Action, 'create')
    @mock.patch.object(cm.Cluster, 'load')
    @mock.patch.object(service.EngineService, 'profile_find')
    @mock.patch.object(service.EngineService, 'cluster_find')
    @mock.patch.object(dispatcher, 'start_action')
    def test_cluster_update(self, notify, mock_find, mock_profile,
                            mock_load, mock_action):
        x_obj = mock.Mock()
        mock_find.return_value = x_obj
        x_cluster = mock.Mock(id='12345678AB', status='ACTIVE',
                              profile_id='OLD_PROFILE',
                              metadata={'A': 'B'})
        x_cluster.to_dict.return_value = {'foo': 'bar'}
        mock_load.return_value = x_cluster
        old_profile = mock.Mock(type='FAKE_TYPE', id='ID_OLD')
        new_profile = mock.Mock(type='FAKE_TYPE', id='ID_NEW')
        mock_profile.side_effect = [old_profile, new_profile]
        mock_action.return_value = 'ACTION_ID'

        # do it
        result = self.eng.cluster_update(self.ctx, 'FAKE_ID', name='new_name',
                                         metadata={'B': 'A'}, timeout=120,
                                         profile_id='NEW_PROFILE')

        self.assertEqual({'action': 'ACTION_ID', 'foo': 'bar'}, result)
        mock_find.assert_called_once_with(self.ctx, 'FAKE_ID')
        mock_load.assert_called_once_with(self.ctx, dbcluster=x_obj)
        mock_profile.assert_has_calls([
            mock.call(self.ctx, 'OLD_PROFILE'),
            mock.call(self.ctx, 'NEW_PROFILE'),
        ])
        mock_action.assert_called_once_with(
            self.ctx, '12345678AB', 'CLUSTER_UPDATE',
            name='cluster_update_12345678',
            cause=am.CAUSE_RPC,
            status=am.Action.READY,
            inputs={
                'new_profile_id': 'ID_NEW',
                'metadata': {
                    'B': 'A',
                },
                'timeout': 120,
                'name': 'new_name',
            },
        )
        notify.assert_called_once_with()

    @mock.patch.object(service.EngineService, 'cluster_find')
    def test_cluster_update_cluster_not_found(self, mock_find):
        mock_find.side_effect = exc.ClusterNotFound(cluster='Bogus')

        ex = self.assertRaises(rpc.ExpectedException,
                               self.eng.cluster_update,
                               self.ctx, 'Bogus')
        self.assertEqual(exc.ClusterNotFound, ex.exc_info[0])

    @mock.patch.object(cm.Cluster, 'load')
    @mock.patch.object(service.EngineService, 'cluster_find')
    def test_cluster_update_cluster_bad_status(self, mock_find, mock_load):
        x_obj = mock.Mock()
        mock_find.return_value = x_obj
        mock_load.return_value = mock.Mock(status='ERROR', ERROR='ERROR')

        ex = self.assertRaises(rpc.ExpectedException,
                               self.eng.cluster_update,
                               self.ctx, 'CLUSTER', name='new_name')

        self.assertEqual(exc.FeatureNotSupported, ex.exc_info[0])
        self.assertEqual('Updating a cluster in error state is not supported.',
                         six.text_type(ex.exc_info[1]))
        mock_find.assert_called_once_with(self.ctx, 'CLUSTER')
        mock_load.assert_called_once_with(self.ctx, dbcluster=x_obj)

    @mock.patch.object(service.EngineService, 'profile_find')
    @mock.patch.object(cm.Cluster, 'load')
    @mock.patch.object(service.EngineService, 'cluster_find')
    def test_cluster_update_profile_not_found(self, mock_find, mock_load,
                                              mock_profile):
        x_obj = mock.Mock()
        mock_find.return_value = x_obj
        mock_load.return_value = mock.Mock(status='ACTIVE', ERROR='ERROR',
                                           profile_id='OLD_ID')

        mock_profile.side_effect = [
            mock.Mock(type='FAKE_TYPE', id='OLD_ID'),
            exc.ProfileNotFound(profile='Bogus')
        ]

        ex = self.assertRaises(rpc.ExpectedException,
                               self.eng.cluster_update,
                               self.ctx, 'CLUSTER', profile_id='Bogus')

        self.assertEqual(exc.BadRequest, ex.exc_info[0])
        self.assertEqual("The request is malformed: "
                         "The specified profile 'Bogus' is not found.",
                         six.text_type(ex.exc_info[1]))
        mock_find.assert_called_once_with(self.ctx, 'CLUSTER')
        mock_load.assert_called_once_with(self.ctx, dbcluster=x_obj)
        mock_profile.assert_has_calls([
            mock.call(self.ctx, 'OLD_ID'),
            mock.call(self.ctx, 'Bogus'),
        ])

    @mock.patch.object(service.EngineService, 'profile_find')
    @mock.patch.object(cm.Cluster, 'load')
    @mock.patch.object(service.EngineService, 'cluster_find')
    def test_cluster_update_diff_profile_type(self, mock_find, mock_load,
                                              mock_profile):
        x_obj = mock.Mock()
        mock_find.return_value = x_obj
        mock_load.return_value = mock.Mock(status='ACTIVE', ERROR='ERROR',
                                           profile_id='OLD_ID')

        mock_profile.side_effect = [
            mock.Mock(type='FAKE_TYPE', id='OLD_ID'),
            mock.Mock(type='DIFF_TYPE', id='NEW_ID'),
        ]

        ex = self.assertRaises(rpc.ExpectedException,
                               self.eng.cluster_update,
                               self.ctx, 'CLUSTER', profile_id='NEW_PROFILE')

        self.assertEqual(exc.ProfileTypeNotMatch, ex.exc_info[0])
        mock_find.assert_called_once_with(self.ctx, 'CLUSTER')
        mock_load.assert_called_once_with(self.ctx, dbcluster=x_obj)
        mock_profile.assert_has_calls([
            mock.call(self.ctx, 'OLD_ID'),
            mock.call(self.ctx, 'NEW_PROFILE'),
        ])

    @mock.patch.object(am.Action, 'create')
    @mock.patch.object(cm.Cluster, 'load')
    @mock.patch.object(service.EngineService, 'profile_find')
    @mock.patch.object(service.EngineService, 'cluster_find')
    @mock.patch.object(dispatcher, 'start_action')
    def test_cluster_update_same_profile(self, notify, mock_find, mock_profile,
                                         mock_load, mock_action):
        x_obj = mock.Mock()
        mock_find.return_value = x_obj
        x_cluster = mock.Mock(id='12345678AB', status='ACTIVE',
                              profile_id='OLD_PROFILE')
        x_cluster.to_dict.return_value = {'foo': 'bar'}
        mock_load.return_value = x_cluster
        old_profile = mock.Mock(type='FAKE_TYPE', id='ID_OLD')
        new_profile = mock.Mock(type='FAKE_TYPE', id='ID_OLD')
        mock_profile.side_effect = [old_profile, new_profile]
        mock_action.return_value = 'ACTION_ID'

        # do it
        result = self.eng.cluster_update(self.ctx, 'FAKE_ID', name='new_name',
                                         profile_id='NEW_PROFILE')

        self.assertEqual({'action': 'ACTION_ID', 'foo': 'bar'}, result)
        mock_find.assert_called_once_with(self.ctx, 'FAKE_ID')
        mock_load.assert_called_once_with(self.ctx, dbcluster=x_obj)
        mock_profile.assert_has_calls([
            mock.call(self.ctx, 'OLD_PROFILE'),
            mock.call(self.ctx, 'NEW_PROFILE'),
        ])
        mock_action.assert_called_once_with(
            self.ctx, '12345678AB', 'CLUSTER_UPDATE',
            name='cluster_update_12345678',
            cause=am.CAUSE_RPC,
            status=am.Action.READY,
            inputs={
                # Note profile_id is not shown in the inputs
                'name': 'new_name',
            },
        )
        notify.assert_called_once_with()

    @mock.patch.object(am.Action, 'create')
    @mock.patch.object(cm.Cluster, 'load')
    @mock.patch.object(service.EngineService, 'cluster_find')
    @mock.patch.object(dispatcher, 'start_action')
    def test_cluster_update_same_metadata(self, notify, mock_find, mock_load,
                                          mock_action):
        x_obj = mock.Mock()
        mock_find.return_value = x_obj
        x_cluster = mock.Mock(id='12345678AB', status='ACTIVE',
                              metadata={'K': 'V'})
        x_cluster.to_dict.return_value = {'foo': 'bar'}
        mock_load.return_value = x_cluster
        mock_action.return_value = 'ACTION_ID'

        # do it
        result = self.eng.cluster_update(self.ctx, 'FAKE_ID', name='new_name',
                                         metadata={'K': 'V'})

        self.assertEqual({'action': 'ACTION_ID', 'foo': 'bar'}, result)
        mock_find.assert_called_once_with(self.ctx, 'FAKE_ID')
        mock_load.assert_called_once_with(self.ctx, dbcluster=x_obj)
        mock_action.assert_called_once_with(
            self.ctx, '12345678AB', 'CLUSTER_UPDATE',
            name='cluster_update_12345678',
            status=am.Action.READY,
            cause=am.CAUSE_RPC,
            inputs={
                # Note metadata is not included in the inputs
                'name': 'new_name',
            },
        )
        notify.assert_called_once_with()

    @mock.patch.object(cm.Cluster, 'load')
    @mock.patch.object(service.EngineService, 'cluster_find')
    def test_cluster_update_timeout_not_integer(self, mock_find, mock_load):
        x_obj = mock.Mock()
        mock_find.return_value = x_obj
        x_cluster = mock.Mock(id='12345678AB', status='ACTIVE')
        mock_load.return_value = x_cluster

        ex = self.assertRaises(rpc.ExpectedException,
                               self.eng.cluster_update,
                               self.ctx, 'CLUSTER', timeout='Long')

        self.assertEqual(exc.InvalidParameter, ex.exc_info[0])
        mock_find.assert_called_once_with(self.ctx, 'CLUSTER')
        mock_load.assert_called_once_with(self.ctx, dbcluster=x_obj)

    @mock.patch.object(cm.Cluster, 'load')
    @mock.patch.object(service.EngineService, 'cluster_find')
    def test_cluster_update_cluster_no_property_updated(self, mock_find,
                                                        mock_load):
        x_obj = mock.Mock()
        mock_find.return_value = x_obj
        mock_load.return_value = mock.Mock(status='ACTIVE', ERROR='ERROR',
                                           profile_id='OLD_ID')

        ex = self.assertRaises(rpc.ExpectedException,
                               self.eng.cluster_update,
                               self.ctx, 'CLUSTER')
        self.assertEqual(exc.BadRequest, ex.exc_info[0])

    @mock.patch.object(am.Action, 'create')
    @mock.patch.object(ro.Receiver, 'get_all')
    @mock.patch.object(cpo.ClusterPolicy, 'get_all')
    @mock.patch.object(service.EngineService, 'cluster_find')
    @mock.patch.object(dispatcher, 'start_action')
    def test_cluster_delete(self, notify, mock_find, mock_policies,
                            mock_receivers, mock_action):
        x_obj = mock.Mock(id='12345678AB')
        mock_find.return_value = x_obj
        mock_policies.return_value = []
        mock_receivers.return_value = []
        mock_action.return_value = 'ACTION_ID'

        result = self.eng.cluster_delete(self.ctx, 'IDENTITY')

        self.assertEqual({'action': 'ACTION_ID'}, result)
        mock_find.assert_called_once_with(self.ctx, 'IDENTITY')
        mock_policies.assert_called_once_with(self.ctx, '12345678AB')
        mock_receivers.assert_called_once_with(
            self.ctx, filters={'cluster_id': '12345678AB'})
        mock_action.assert_called_once_with(
            self.ctx, '12345678AB', 'CLUSTER_DELETE',
            name='cluster_delete_12345678',
            cause=am.CAUSE_RPC,
            status=am.Action.READY)

        notify.assert_called_once_with()

    @mock.patch.object(service.EngineService, 'cluster_find')
    def test_cluster_delete_not_found(self, mock_find):
        mock_find.side_effect = exc.ClusterNotFound(cluster='Bogus')

        ex = self.assertRaises(rpc.ExpectedException,
                               self.eng.cluster_delete,
                               self.ctx, 'Bogus')

        self.assertEqual(exc.ClusterNotFound, ex.exc_info[0])
        self.assertEqual('The cluster (Bogus) could not be found.',
                         six.text_type(ex.exc_info[1]))

    @mock.patch.object(cpo.ClusterPolicy, 'get_all')
    @mock.patch.object(service.EngineService, 'cluster_find')
    def test_cluster_delete_policy_attached(self, mock_find, mock_policies):
        x_obj = mock.Mock(id='12345678AB')
        mock_find.return_value = x_obj
        mock_policies.return_value = [mock.Mock()]

        ex = self.assertRaises(rpc.ExpectedException,
                               self.eng.cluster_delete,
                               self.ctx, 'IDENTITY')

        self.assertEqual(exc.ClusterBusy, ex.exc_info[0])
        expected_msg = _('The cluster (12345678AB) cannot be deleted: '
                         'there is still policy(s) attached to it.')
        self.assertEqual(expected_msg, six.text_type(ex.exc_info[1]))
        mock_find.assert_called_once_with(self.ctx, 'IDENTITY')
        mock_policies.assert_called_once_with(self.ctx, '12345678AB')

    @mock.patch.object(ro.Receiver, 'get_all')
    @mock.patch.object(cpo.ClusterPolicy, 'get_all')
    @mock.patch.object(service.EngineService, 'cluster_find')
    def test_cluster_delete_with_receiver(self, mock_find, mock_policies,
                                          mock_receivers):
        x_obj = mock.Mock(id='12345678AB')
        mock_find.return_value = x_obj
        mock_policies.return_value = []
        mock_receivers.return_value = [mock.Mock()]

        ex = self.assertRaises(rpc.ExpectedException,
                               self.eng.cluster_delete,
                               self.ctx, 'IDENTITY')

        self.assertEqual(exc.ClusterBusy, ex.exc_info[0])
        expected_msg = _('The cluster (12345678AB) cannot be deleted: '
                         'there is still receiver(s) associated with it.')
        self.assertEqual(expected_msg, six.text_type(ex.exc_info[1]))
        mock_find.assert_called_once_with(self.ctx, 'IDENTITY')
        mock_policies.assert_called_once_with(self.ctx, '12345678AB')
        mock_receivers.assert_called_once_with(
            self.ctx, filters={'cluster_id': '12345678AB'})

    @mock.patch.object(su, 'check_size_params')
    @mock.patch.object(am.Action, 'create')
    @mock.patch.object(service.EngineService, 'node_find')
    @mock.patch.object(service.EngineService, 'profile_find')
    @mock.patch.object(service.EngineService, 'cluster_find')
    @mock.patch.object(dispatcher, 'start_action')
    def test_cluster_add_nodes(self, notify, mock_find, mock_profile,
                               mock_node, mock_action, mock_check):
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

        result = self.eng.cluster_add_nodes(self.ctx, 'C1',
                                            ['NODE_A', 'NODE_B'])

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
            cause=am.CAUSE_RPC,
            status=am.Action.READY,
            inputs={'nodes': ['NODE1', 'NODE2']},
        )
        notify.assert_called_once_with()

    @mock.patch.object(service.EngineService, 'cluster_find')
    def test_cluster_add_nodes_cluster_not_found(self, mock_find):
        mock_find.side_effect = exc.ClusterNotFound(cluster='Bogus')

        ex = self.assertRaises(rpc.ExpectedException,
                               self.eng.cluster_add_nodes,
                               self.ctx, 'Bogus', ['n1', 'n2'])

        self.assertEqual(exc.ClusterNotFound, ex.exc_info[0])
        self.assertEqual('The cluster (Bogus) could not be found.',
                         six.text_type(ex.exc_info[1]))
        mock_find.assert_called_once_with(self.ctx, 'Bogus')

    @mock.patch.object(service.EngineService, 'profile_find')
    @mock.patch.object(service.EngineService, 'cluster_find')
    def test_cluster_add_nodes_empty_list(self, mock_find, mock_profile):

        mock_find.return_value = mock.Mock(id='1234', profile_id='FAKE_ID')
        mock_profile.return_value = mock.Mock(type='FAKE_TYPE')

        ex = self.assertRaises(rpc.ExpectedException,
                               self.eng.cluster_add_nodes,
                               self.ctx, 'CLUSTER', [])

        self.assertEqual(exc.BadRequest, ex.exc_info[0])
        self.assertEqual('The request is malformed: No nodes to add: [].',
                         six.text_type(ex.exc_info[1]))
        mock_find.assert_called_once_with(self.ctx, 'CLUSTER')
        mock_profile.assert_called_once_with(self.ctx, 'FAKE_ID')

    @mock.patch.object(service.EngineService, 'node_find')
    @mock.patch.object(service.EngineService, 'profile_find')
    @mock.patch.object(service.EngineService, 'cluster_find')
    def test_cluster_add_nodes_nodes_not_found(self, mock_find, mock_profile,
                                               mock_node):
        mock_find.return_value = mock.Mock(id='1234', profile_id='FAKE_ID')
        mock_profile.return_value = mock.Mock(type='FAKE_TYPE')
        mock_node.side_effect = exc.NodeNotFound(node='NODE1')

        ex = self.assertRaises(rpc.ExpectedException,
                               self.eng.cluster_add_nodes,
                               self.ctx, 'CLUSTER', ['NODE1'])

        self.assertEqual(exc.BadRequest, ex.exc_info[0])
        self.assertEqual("The request is malformed: Nodes not found: "
                         "['NODE1'].", six.text_type(ex.exc_info[1]))
        mock_find.assert_called_once_with(self.ctx, 'CLUSTER')
        mock_profile.assert_called_once_with(self.ctx, 'FAKE_ID')
        mock_node.assert_called_once_with(self.ctx, 'NODE1')

    @mock.patch.object(service.EngineService, 'node_find')
    @mock.patch.object(service.EngineService, 'profile_find')
    @mock.patch.object(service.EngineService, 'cluster_find')
    def test_cluster_add_nodes_bad_status(self, mock_find, mock_profile,
                                          mock_node):
        mock_find.return_value = mock.Mock(id='1234', profile_id='FAKE_ID')
        mock_profile.return_value = mock.Mock(type='FAKE_TYPE')
        mock_node.return_value = mock.Mock(id='NODE2', status='ERROR')

        ex = self.assertRaises(rpc.ExpectedException,
                               self.eng.cluster_add_nodes,
                               self.ctx, 'CLUSTER', ['NODE2'])

        self.assertEqual(exc.BadRequest, ex.exc_info[0])
        self.assertEqual("The request is malformed: Nodes are not ACTIVE: "
                         "['NODE2'].",
                         six.text_type(ex.exc_info[1]))

        mock_find.assert_called_once_with(self.ctx, 'CLUSTER')
        mock_profile.assert_called_once_with(self.ctx, 'FAKE_ID')
        mock_node.assert_called_once_with(self.ctx, 'NODE2')

    @mock.patch.object(service.EngineService, 'node_find')
    @mock.patch.object(service.EngineService, 'profile_find')
    @mock.patch.object(service.EngineService, 'cluster_find')
    def test_cluster_add_nodes_node_already_owned(self, mock_find,
                                                  mock_profile, mock_node):

        mock_find.return_value = mock.Mock(id='1234', profile_id='FAKE_ID')
        mock_profile.return_value = mock.Mock(type='FAKE_TYPE')
        mock_node.return_value = mock.Mock(id='NODE3', status='ACTIVE',
                                           cluster_id='OTHER')

        ex = self.assertRaises(rpc.ExpectedException,
                               self.eng.cluster_add_nodes,
                               self.ctx, 'CLUSTER', ['NODE3'])

        self.assertEqual(exc.NodeNotOrphan, ex.exc_info[0])
        self.assertEqual("Nodes ['NODE3'] already owned by some cluster.",
                         six.text_type(ex.exc_info[1]))

        mock_find.assert_called_once_with(self.ctx, 'CLUSTER')
        mock_profile.assert_called_once_with(self.ctx, 'FAKE_ID')
        mock_node.assert_called_once_with(self.ctx, 'NODE3')

    @mock.patch.object(service.EngineService, 'node_find')
    @mock.patch.object(service.EngineService, 'profile_find')
    @mock.patch.object(service.EngineService, 'cluster_find')
    def test_cluster_add_nodes_node_profile_type_not_match(
            self, mock_find, mock_profile, mock_node):

        mock_find.return_value = mock.Mock(id='1234', profile_id='FAKE_ID')
        mock_profile.side_effect = [
            mock.Mock(type='FAKE_TYPE_1'),
            mock.Mock(type='FAKE_TYPE_2'),
        ]
        mock_node.return_value = mock.Mock(id='NODE4', status='ACTIVE',
                                           cluster_id='', profile_id='DIFF')

        ex = self.assertRaises(rpc.ExpectedException,
                               self.eng.cluster_add_nodes,
                               self.ctx, 'CLUSTER', ['NODE4'])

        self.assertEqual(exc.ProfileTypeNotMatch, ex.exc_info[0])
        self.assertEqual("Profile type of nodes ['NODE4'] does not match "
                         "that of the cluster.",
                         six.text_type(ex.exc_info[1]))
        mock_find.assert_called_once_with(self.ctx, 'CLUSTER')
        mock_profile.assert_has_calls([
            mock.call(self.ctx, 'FAKE_ID'),
            mock.call(self.ctx, 'DIFF'),
        ])
        mock_node.assert_called_once_with(self.ctx, 'NODE4')

    @mock.patch.object(su, 'check_size_params')
    @mock.patch.object(service.EngineService, 'node_find')
    @mock.patch.object(service.EngineService, 'profile_find')
    @mock.patch.object(service.EngineService, 'cluster_find')
    def test_cluster_add_nodes_failed_checking(self, mock_find, mock_profile,
                                               mock_node, mock_check):
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

        ex = self.assertRaises(rpc.ExpectedException,
                               self.eng.cluster_add_nodes,
                               self.ctx, 'C1', ['NODE_A', 'NODE_B'])

        self.assertEqual(exc.BadRequest, ex.exc_info[0])
        self.assertEqual("The request is malformed: Failed size checking.",
                         six.text_type(ex.exc_info[1]))

        mock_find.assert_called_once_with(self.ctx, 'C1')
        mock_profile.assert_has_calls([
            mock.call(self.ctx, 'FAKE_PROFILE'),
            mock.call(self.ctx, 'FAKE_PROFILE_1'),
            mock.call(self.ctx, 'FAKE_PROFILE_2'),
        ])
        mock_node.assert_has_calls([
            mock.call(self.ctx, 'NODE_A'),
            mock.call(self.ctx, 'NODE_B'),
        ])
        mock_check.assert_called_once_with(x_cluster, 4, strict=True)

    @mock.patch.object(su, 'check_size_params')
    @mock.patch.object(am.Action, 'create')
    @mock.patch.object(service.EngineService, 'node_find')
    @mock.patch.object(service.EngineService, 'cluster_find')
    @mock.patch.object(dispatcher, 'start_action')
    def test_cluster_del_nodes(self, notify, mock_find, mock_node,
                               mock_action, mock_check):
        x_cluster = mock.Mock(id='1234', desired_capacity=2)
        mock_find.return_value = x_cluster
        mock_node.return_value = mock.Mock(id='NODE2', cluster_id='1234')
        mock_check.return_value = None
        mock_action.return_value = 'ACTION_ID'

        result = self.eng.cluster_del_nodes(self.ctx, 'CLUSTER', ['NODE1'])

        self.assertEqual({'action': 'ACTION_ID'}, result)
        mock_find.assert_called_once_with(self.ctx, 'CLUSTER')
        mock_node.assert_called_once_with(self.ctx, 'NODE1')
        mock_check.asset_called_once_with(x_cluster, 1, strict=True)
        mock_action.assert_called_once_with(
            self.ctx, '1234', consts.CLUSTER_DEL_NODES,
            name='cluster_del_nodes_1234',
            status=am.Action.READY,
            cause=am.CAUSE_RPC,
            inputs={
                'count': 1,
                'candidates': ['NODE2'],
            },
        )
        notify.assert_called_once_with()

    @mock.patch.object(service.EngineService, 'cluster_find')
    def test_cluster_del_nodes_cluster_not_found(self, mock_find):
        mock_find.side_effect = exc.ClusterNotFound(cluster='Bogus')

        ex = self.assertRaises(rpc.ExpectedException,
                               self.eng.cluster_del_nodes,
                               self.ctx, 'Bogus', ['n1', 'n2'])

        self.assertEqual(exc.ClusterNotFound, ex.exc_info[0])
        self.assertEqual('The cluster (Bogus) could not be found.',
                         six.text_type(ex.exc_info[1]))
        mock_find.assert_called_once_with(self.ctx, 'Bogus')

    @mock.patch.object(service.EngineService, 'cluster_find')
    def test_cluster_del_nodes_empty_list(self, mock_find):
        mock_find.return_value = mock.Mock(id='1234')

        ex = self.assertRaises(rpc.ExpectedException,
                               self.eng.cluster_del_nodes,
                               self.ctx, 'CLUSTER', [])

        self.assertEqual(exc.BadRequest, ex.exc_info[0])
        self.assertEqual('The request is malformed: No nodes specified.',
                         six.text_type(ex.exc_info[1]))
        mock_find.assert_called_once_with(self.ctx, 'CLUSTER')

    @mock.patch.object(service.EngineService, 'node_find')
    @mock.patch.object(service.EngineService, 'cluster_find')
    def test_cluster_del_nodes_node_not_found(self, mock_find, mock_node):
        mock_find.return_value = mock.Mock()
        mock_node.side_effect = exc.NodeNotFound(node='NODE1')

        ex = self.assertRaises(rpc.ExpectedException,
                               self.eng.cluster_del_nodes,
                               self.ctx, 'CLUSTER', ['NODE1'])

        self.assertEqual(exc.BadRequest, ex.exc_info[0])
        self.assertEqual("The request is malformed: Nodes not found: "
                         "['NODE1'].", six.text_type(ex.exc_info[1]))
        mock_find.assert_called_once_with(self.ctx, 'CLUSTER')
        mock_node.assert_called_once_with(self.ctx, 'NODE1')

    @mock.patch.object(service.EngineService, 'node_find')
    @mock.patch.object(service.EngineService, 'cluster_find')
    def test_cluster_del_nodes_node_in_other_cluster(self, mock_find,
                                                     mock_node):
        mock_find.return_value = mock.Mock(id='1234')
        mock_node.return_value = mock.Mock(id='NODE2', cluster_id='5678')

        ex = self.assertRaises(rpc.ExpectedException,
                               self.eng.cluster_del_nodes,
                               self.ctx, 'CLUSTER', ['NODE2'])

        self.assertEqual(exc.BadRequest, ex.exc_info[0])
        self.assertEqual("The request is malformed: Nodes not members of "
                         "specified cluster: ['NODE2'].",
                         six.text_type(ex.exc_info[1]))
        mock_find.assert_called_once_with(self.ctx, 'CLUSTER')
        mock_node.assert_called_once_with(self.ctx, 'NODE2')

    @mock.patch.object(service.EngineService, 'node_find')
    @mock.patch.object(service.EngineService, 'cluster_find')
    def test_cluster_del_nodes_orphan_nodes(self, mock_find, mock_node):
        mock_find.return_value = mock.Mock(id='1234')
        mock_node.return_value = mock.Mock(id='NODE3', cluster_id='')

        ex = self.assertRaises(rpc.ExpectedException,
                               self.eng.cluster_del_nodes,
                               self.ctx, 'CLUSTER', ['NODE3'])

        self.assertEqual(exc.BadRequest, ex.exc_info[0])
        self.assertEqual("The request is malformed: Nodes not members of "
                         "specified cluster: ['NODE3'].",
                         six.text_type(ex.exc_info[1]))

        mock_find.assert_called_once_with(self.ctx, 'CLUSTER')
        mock_node.assert_called_once_with(self.ctx, 'NODE3')

    @mock.patch.object(su, 'check_size_params')
    @mock.patch.object(service.EngineService, 'node_find')
    @mock.patch.object(service.EngineService, 'cluster_find')
    def test_cluster_del_nodes_failed_checking(self, mock_find, mock_node,
                                               mock_check):
        x_cluster = mock.Mock(id='1234', desired_capacity=2)
        mock_find.return_value = x_cluster
        mock_node.return_value = mock.Mock(id='NODE2', cluster_id='1234')
        mock_check.return_value = 'Failed size checking.'

        ex = self.assertRaises(rpc.ExpectedException,
                               self.eng.cluster_del_nodes,
                               self.ctx, 'CLUSTER', ['NODE1'])

        self.assertEqual(exc.BadRequest, ex.exc_info[0])
        self.assertEqual("The request is malformed: Failed size checking.",
                         six.text_type(ex.exc_info[1]))

        mock_find.assert_called_once_with(self.ctx, 'CLUSTER')
        mock_node.assert_called_once_with(self.ctx, 'NODE1')
        mock_check.assert_called_once_with(x_cluster, 1, strict=True)

    @mock.patch.object(su, 'calculate_desired')
    @mock.patch.object(su, 'check_size_params')
    @mock.patch.object(dispatcher, 'start_action')
    @mock.patch.object(am.Action, 'create')
    @mock.patch.object(service.EngineService, 'cluster_find')
    def test_cluster_resize_exact_capacity(self, mock_find, mock_action,
                                           notify, mock_check, mock_calc):
        x_cluster = mock.Mock(id='12345678ABCDEFGH', desired_capacity=3)
        mock_find.return_value = x_cluster
        mock_calc.return_value = 5
        mock_check.return_value = None
        mock_action.return_value = 'ACTION_ID'

        res = self.eng.cluster_resize(self.ctx, 'CLUSTER',
                                      adj_type=consts.EXACT_CAPACITY,
                                      number=5)

        self.assertEqual({'action': 'ACTION_ID'}, res)
        mock_find.assert_called_once_with(self.ctx, 'CLUSTER')
        mock_calc.assert_called_once_with(3, consts.EXACT_CAPACITY, 5, None)
        mock_check.assert_called_once_with(x_cluster, 5, None, None, True)
        mock_action.assert_called_once_with(
            self.ctx, '12345678ABCDEFGH', consts.CLUSTER_RESIZE,
            name='cluster_resize_12345678',
            cause=am.CAUSE_RPC,
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

    @mock.patch.object(su, 'calculate_desired')
    @mock.patch.object(su, 'check_size_params')
    @mock.patch.object(dispatcher, 'start_action')
    @mock.patch.object(am.Action, 'create')
    @mock.patch.object(service.EngineService, 'cluster_find')
    def test_cluster_resize_change_in_capacity(self, mock_find, mock_action,
                                               notify, mock_check, mock_calc):
        x_cluster = mock.Mock(id='12345678ABCDEFGH', desired_capacity=4)
        mock_find.return_value = x_cluster
        mock_calc.return_value = 9
        mock_check.return_value = None
        mock_action.return_value = 'ACTION_ID'

        res = self.eng.cluster_resize(self.ctx, 'CLUSTER',
                                      adj_type=consts.CHANGE_IN_CAPACITY,
                                      number=5)

        self.assertEqual({'action': 'ACTION_ID'}, res)
        mock_find.assert_called_once_with(self.ctx, 'CLUSTER')
        mock_calc.assert_called_once_with(4, consts.CHANGE_IN_CAPACITY, 5,
                                          None)
        mock_check.assert_called_once_with(x_cluster, 9, None, None, True)
        mock_action.assert_called_once_with(
            self.ctx, '12345678ABCDEFGH', consts.CLUSTER_RESIZE,
            name='cluster_resize_12345678',
            cause=am.CAUSE_RPC,
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

    @mock.patch.object(su, 'calculate_desired')
    @mock.patch.object(su, 'check_size_params')
    @mock.patch.object(dispatcher, 'start_action')
    @mock.patch.object(am.Action, 'create')
    @mock.patch.object(service.EngineService, 'cluster_find')
    def test_cluster_resize_change_in_percentage(self, mock_find, mock_action,
                                                 notify, mock_check,
                                                 mock_calc):
        x_cluster = mock.Mock(id='12345678ABCDEFGH', desired_capacity=10)
        mock_find.return_value = x_cluster
        mock_calc.return_value = 8
        mock_check.return_value = None
        mock_action.return_value = 'ACTION_ID'

        res = self.eng.cluster_resize(self.ctx, 'CLUSTER',
                                      adj_type=consts.CHANGE_IN_PERCENTAGE,
                                      number=15.81)

        self.assertEqual({'action': 'ACTION_ID'}, res)
        mock_find.assert_called_once_with(self.ctx, 'CLUSTER')
        mock_calc.assert_called_once_with(10, consts.CHANGE_IN_PERCENTAGE,
                                          15.81, None)
        mock_check.assert_called_once_with(x_cluster, 8, None, None, True)
        mock_action.assert_called_once_with(
            self.ctx, '12345678ABCDEFGH', consts.CLUSTER_RESIZE,
            name='cluster_resize_12345678',
            cause=am.CAUSE_RPC,
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

    def test_cluster_resize_bad_adj_type(self):
        ex = self.assertRaises(rpc.ExpectedException,
                               self.eng.cluster_resize,
                               self.ctx, 'FAKE_CLUSTER',
                               adj_type='BOOMBOOM')
        self.assertEqual(exc.InvalidParameter, ex.exc_info[0])
        self.assertEqual("Invalid value 'BOOMBOOM' specified for "
                         "'adjustment_type'", six.text_type(ex.exc_info[1]))

    def test_cluster_resize_missing_number(self):
        ex = self.assertRaises(rpc.ExpectedException,
                               self.eng.cluster_resize,
                               self.ctx, 'FAKE_CLUSTER',
                               adj_type=consts.EXACT_CAPACITY)
        self.assertEqual(exc.BadRequest, ex.exc_info[0])
        self.assertEqual("The request is malformed: Missing number value for "
                         "size adjustment.", six.text_type(ex.exc_info[1]))

    def test_cluster_resize_number_without_type(self):
        ex = self.assertRaises(rpc.ExpectedException,
                               self.eng.cluster_resize,
                               self.ctx, 'FAKE_CLUSTER', number=10)
        self.assertEqual(exc.BadRequest, ex.exc_info[0])
        self.assertEqual("The request is malformed: Missing adjustment_type "
                         "value for size adjustment.",
                         six.text_type(ex.exc_info[1]))

    def test_cluster_resize_bad_number_for_exact_capacity(self):
        ex = self.assertRaises(rpc.ExpectedException,
                               self.eng.cluster_resize,
                               self.ctx, 'FAKE_CLUSTER',
                               adj_type=consts.EXACT_CAPACITY,
                               number='BIGGER')
        self.assertEqual(exc.InvalidParameter, ex.exc_info[0])
        self.assertEqual("Invalid value 'BIGGER' specified for 'number'",
                         six.text_type(ex.exc_info[1]))

        ex = self.assertRaises(rpc.ExpectedException,
                               self.eng.cluster_resize,
                               self.ctx, 'FAKE_CLUSTER',
                               adj_type=consts.EXACT_CAPACITY,
                               number=-10)
        self.assertEqual(exc.InvalidParameter, ex.exc_info[0])
        self.assertEqual("Invalid value '-10' specified for 'number'",
                         six.text_type(ex.exc_info[1]))

    def test_cluster_resize_bad_number_for_change_capacity(self):
        ex = self.assertRaises(rpc.ExpectedException,
                               self.eng.cluster_resize,
                               self.ctx, 'FAKE_CLUSTER',
                               adj_type=consts.CHANGE_IN_CAPACITY,
                               number='BIGGER')
        self.assertEqual(exc.InvalidParameter, ex.exc_info[0])
        self.assertEqual("Invalid value 'BIGGER' specified for 'number'",
                         six.text_type(ex.exc_info[1]))

    def test_cluster_resize_bad_number_for_change_percentage(self):
        ex = self.assertRaises(rpc.ExpectedException,
                               self.eng.cluster_resize,
                               self.ctx, 'FAKE_CLUSTER',
                               adj_type=consts.CHANGE_IN_PERCENTAGE,
                               number='BIGGER')

        self.assertEqual(exc.InvalidParameter, ex.exc_info[0])
        self.assertEqual("Invalid value 'BIGGER' specified for 'number'",
                         six.text_type(ex.exc_info[1]))

    def test_cluster_resize_bad_step_for_change_percentage(self):
        ex = self.assertRaises(rpc.ExpectedException,
                               self.eng.cluster_resize,
                               self.ctx, 'FAKE_CLUSTER',
                               adj_type=consts.CHANGE_IN_PERCENTAGE,
                               number=10.2, min_step='SMALL')

        self.assertEqual(exc.InvalidParameter, ex.exc_info[0])
        self.assertEqual("Invalid value 'SMALL' specified for 'min_step'",
                         six.text_type(ex.exc_info[1]))

    def test_cluster_resize_bad_min_size(self):
        # we intentionally omit adj_type and number here because we allow
        # the use case where only min_size/max_size is specified
        ex = self.assertRaises(rpc.ExpectedException,
                               self.eng.cluster_resize,
                               self.ctx, 'FAKE_CLUSTER', min_size='SMALL')

        self.assertEqual(exc.InvalidParameter, ex.exc_info[0])
        self.assertEqual("Invalid value 'SMALL' specified for 'min_size'",
                         six.text_type(ex.exc_info[1]))

    def test_cluster_resize_bad_max_size(self):
        # we intentionally omit adj_type and number here because we allow
        # the use case where only min_size/max_size is specified
        ex = self.assertRaises(rpc.ExpectedException,
                               self.eng.cluster_resize,
                               self.ctx, 'FAKE_CLUSTER', max_size='INF')

        self.assertEqual(exc.InvalidParameter, ex.exc_info[0])
        self.assertEqual("Invalid value 'INF' specified for 'max_size'",
                         six.text_type(ex.exc_info[1]))

    def test_cluster_resize_bad_strict(self):
        ex = self.assertRaises(rpc.ExpectedException,
                               self.eng.cluster_resize,
                               self.ctx, 'FAKE_CLUSTER', strict='YES')

        self.assertEqual(exc.InvalidParameter, ex.exc_info[0])
        self.assertEqual("Invalid value 'YES' specified for 'strict'",
                         six.text_type(ex.exc_info[1]))

    @mock.patch.object(service.EngineService, 'cluster_find')
    def test_cluster_resize_cluster_not_found(self, mock_find):
        mock_find.side_effect = exc.ClusterNotFound(cluster='FAKE_CLUSTER')

        ex = self.assertRaises(rpc.ExpectedException,
                               self.eng.cluster_resize,
                               self.ctx, 'FAKE_CLUSTER',
                               adj_type=consts.EXACT_CAPACITY, number=10)

        mock_find.assert_called_once_with(self.ctx, 'FAKE_CLUSTER')
        self.assertEqual(exc.ClusterNotFound, ex.exc_info[0])
        self.assertEqual("The cluster (FAKE_CLUSTER) could not be found.",
                         six.text_type(ex.exc_info[1]))
        mock_find.assert_called_once_with(self.ctx, 'FAKE_CLUSTER')

    @mock.patch.object(su, 'check_size_params')
    @mock.patch.object(service.EngineService, 'cluster_find')
    def test_cluster_resize_failing_size_check(self, mock_find, mock_check):
        mock_find.return_value = mock.Mock()
        mock_check.return_value = 'size check.'

        ex = self.assertRaises(rpc.ExpectedException,
                               self.eng.cluster_resize,
                               self.ctx, 'FAKE_CLUSTER',
                               adj_type=consts.EXACT_CAPACITY, number=10)

        mock_find.assert_called_once_with(self.ctx, 'FAKE_CLUSTER')
        self.assertEqual(exc.BadRequest, ex.exc_info[0])
        self.assertEqual("The request is malformed: size check.",
                         six.text_type(ex.exc_info[1]))

    @mock.patch.object(dispatcher, 'start_action')
    @mock.patch.object(am.Action, 'create')
    @mock.patch.object(su, 'check_size_params')
    @mock.patch.object(service.EngineService, 'cluster_find')
    def test_cluster_scale_out(self, mock_find, mock_check, mock_action,
                               notify):
        x_cluster = mock.Mock(id='12345678ABCDEFGH', desired_capacity=4)
        mock_find.return_value = x_cluster
        mock_check.return_value = None
        mock_action.return_value = 'ACTION_ID'

        result = self.eng.cluster_scale_out(self.ctx, 'CLUSTER', count=1)

        self.assertEqual({'action': 'ACTION_ID'}, result)
        mock_find.assert_called_once_with(self.ctx, 'CLUSTER')
        mock_check.assert_called_once_with(x_cluster, 5)
        mock_action.assert_called_once_with(
            self.ctx, '12345678ABCDEFGH', consts.CLUSTER_SCALE_OUT,
            name='cluster_scale_out_12345678',
            cause=am.CAUSE_RPC,
            status=am.Action.READY,
            inputs={'count': 1},
        )
        notify.assert_called_once_with()

    @mock.patch.object(service.EngineService, 'cluster_find')
    def test_cluster_scale_out_cluster_not_found(self, mock_find):
        mock_find.side_effect = exc.ClusterNotFound(cluster='Bogus')

        ex = self.assertRaises(rpc.ExpectedException,
                               self.eng.cluster_scale_out,
                               self.ctx, 'Bogus')

        self.assertEqual(exc.ClusterNotFound, ex.exc_info[0])
        self.assertEqual('The cluster (Bogus) could not be found.',
                         six.text_type(ex.exc_info[1]))
        mock_find.assert_called_once_with(self.ctx, 'Bogus')

    @mock.patch.object(dispatcher, 'start_action')
    @mock.patch.object(am.Action, 'create')
    @mock.patch.object(service.EngineService, 'cluster_find')
    def test_cluster_scale_out_count_is_none(self, mock_find, mock_action,
                                             notify):
        mock_find.return_value = mock.Mock(id='12345678ABCDEFGH',
                                           desired_capacity=4)
        mock_action.return_value = 'ACTION_ID'

        result = self.eng.cluster_scale_out(self.ctx, 'CLUSTER')

        self.assertEqual({'action': 'ACTION_ID'}, result)
        mock_find.assert_called_once_with(self.ctx, 'CLUSTER')
        mock_action.assert_called_once_with(
            self.ctx, '12345678ABCDEFGH', consts.CLUSTER_SCALE_OUT,
            name='cluster_scale_out_12345678',
            cause=am.CAUSE_RPC,
            status=am.Action.READY,
            inputs={},
        )
        notify.assert_called_once_with()

    @mock.patch.object(service.EngineService, 'cluster_find')
    def test_cluster_scale_out_count_not_int_or_zero(self, mock_find):
        mock_find.return_value = mock.Mock(desired_capacity=4)

        ex = self.assertRaises(rpc.ExpectedException,
                               self.eng.cluster_scale_out,
                               self.ctx, 'CLUSTER', count='one')

        self.assertEqual(exc.InvalidParameter, ex.exc_info[0])
        self.assertEqual("Invalid value 'one' specified for 'count'",
                         six.text_type(ex.exc_info[1]))

        ex = self.assertRaises(rpc.ExpectedException,
                               self.eng.cluster_scale_out,
                               self.ctx, 'CLUSTER', count=0)

        self.assertEqual(exc.InvalidParameter, ex.exc_info[0])
        self.assertEqual("Invalid value '0' specified for 'count'",
                         six.text_type(ex.exc_info[1]))

    @mock.patch.object(su, 'check_size_params')
    @mock.patch.object(service.EngineService, 'cluster_find')
    def test_cluster_scale_out_failed_size_check(self, mock_find, mock_check):
        x_cluster = mock.Mock(desired_capacity=4)
        mock_find.return_value = x_cluster
        mock_check.return_value = 'size limit'

        ex = self.assertRaises(rpc.ExpectedException,
                               self.eng.cluster_scale_out,
                               self.ctx, 'FAKE_CLUSTER', 2)

        self.assertEqual(exc.BadRequest, ex.exc_info[0])
        self.assertEqual("The request is malformed: size limit",
                         six.text_type(ex.exc_info[1]))
        mock_find.assert_called_once_with(self.ctx, 'FAKE_CLUSTER')
        mock_check.assert_called_once_with(x_cluster, 6)

    @mock.patch.object(dispatcher, 'start_action')
    @mock.patch.object(am.Action, 'create')
    @mock.patch.object(su, 'check_size_params')
    @mock.patch.object(service.EngineService, 'cluster_find')
    def test_cluster_scale_in(self, mock_find, mock_check, mock_action,
                              notify):
        x_cluster = mock.Mock(id='12345678ABCD', desired_capacity=4)
        mock_find.return_value = x_cluster
        mock_check.return_value = None
        mock_action.return_value = 'ACTION_ID'

        result = self.eng.cluster_scale_in(self.ctx, 'CLUSTER', count=1)

        self.assertEqual({'action': 'ACTION_ID'}, result)
        mock_find.assert_called_once_with(self.ctx, 'CLUSTER')
        mock_check.assert_called_once_with(x_cluster, 3)
        mock_action.assert_called_once_with(
            self.ctx, '12345678ABCD', consts.CLUSTER_SCALE_IN,
            name='cluster_scale_in_12345678',
            cause=am.CAUSE_RPC,
            status=am.Action.READY,
            inputs={'count': 1},
        )
        notify.assert_called_once_with()

    @mock.patch.object(service.EngineService, 'cluster_find')
    def test_cluster_scale_in_cluster_not_found(self, mock_find):
        mock_find.side_effect = exc.ClusterNotFound(cluster='Bogus')

        ex = self.assertRaises(rpc.ExpectedException,
                               self.eng.cluster_scale_in,
                               self.ctx, 'Bogus')

        self.assertEqual(exc.ClusterNotFound, ex.exc_info[0])
        self.assertEqual('The cluster (Bogus) could not be found.',
                         six.text_type(ex.exc_info[1]))
        mock_find.assert_called_once_with(self.ctx, 'Bogus')

    @mock.patch.object(dispatcher, 'start_action')
    @mock.patch.object(am.Action, 'create')
    @mock.patch.object(service.EngineService, 'cluster_find')
    def test_cluster_scale_in_count_is_none(self, mock_find, mock_action,
                                            notify):
        mock_find.return_value = mock.Mock(id='12345678ABCD',
                                           desired_capacity=4)
        mock_action.return_value = 'ACTION_ID'

        result = self.eng.cluster_scale_in(self.ctx, 'CLUSTER')

        self.assertEqual({'action': 'ACTION_ID'}, result)
        mock_find.assert_called_once_with(self.ctx, 'CLUSTER')
        mock_action.assert_called_once_with(
            self.ctx, '12345678ABCD', consts.CLUSTER_SCALE_IN,
            name='cluster_scale_in_12345678',
            cause=am.CAUSE_RPC,
            status=am.Action.READY,
            inputs={},
        )
        notify.assert_called_once_with()

    @mock.patch.object(service.EngineService, 'cluster_find')
    def test_cluster_scale_in_count_not_int_or_zero(self, mock_find):
        mock_find.return_value = mock.Mock(desired_capacity=4)

        ex = self.assertRaises(rpc.ExpectedException,
                               self.eng.cluster_scale_in,
                               self.ctx, 'CLUSTER', count='one')

        self.assertEqual(exc.InvalidParameter, ex.exc_info[0])
        self.assertEqual("Invalid value 'one' specified for 'count'",
                         six.text_type(ex.exc_info[1]))

        ex = self.assertRaises(rpc.ExpectedException,
                               self.eng.cluster_scale_in,
                               self.ctx, 'CLUSTER', count=0)

        self.assertEqual(exc.InvalidParameter, ex.exc_info[0])
        self.assertEqual("Invalid value '0' specified for 'count'",
                         six.text_type(ex.exc_info[1]))

    @mock.patch.object(su, 'check_size_params')
    @mock.patch.object(service.EngineService, 'cluster_find')
    def test_cluster_scale_in_failed_size_check(self, mock_find, mock_check):
        x_cluster = mock.Mock(desired_capacity=4)
        mock_find.return_value = x_cluster
        mock_check.return_value = 'size limit'

        ex = self.assertRaises(rpc.ExpectedException,
                               self.eng.cluster_scale_in,
                               self.ctx, 'FAKE_CLUSTER', 2)

        self.assertEqual(exc.BadRequest, ex.exc_info[0])
        self.assertEqual("The request is malformed: size limit",
                         six.text_type(ex.exc_info[1]))
        mock_find.assert_called_once_with(self.ctx, 'FAKE_CLUSTER')
        mock_check.assert_called_once_with(x_cluster, 2)

    @mock.patch.object(nm.Node, 'load_all')
    @mock.patch.object(service.EngineService, 'cluster_find')
    def test_cluster_collect(self, mock_find, mock_load):
        x_cluster = mock.Mock(id='FAKE_CLUSTER')
        mock_find.return_value = x_cluster
        x_node_1 = mock.Mock(id='NODE1', physical_id='PHYID1')
        x_node_1.to_dict.return_value = {'name': 'node1'}
        x_node_1.get_details.return_value = {'ip': '1.2.3.4'}
        x_node_2 = mock.Mock(id='NODE2', physical_id='PHYID2')
        x_node_2.to_dict.return_value = {'name': 'node2'}
        x_node_2.get_details.return_value = {'ip': '5.6.7.8'}
        mock_load.return_value = [x_node_1, x_node_2]

        res = self.eng.cluster_collect(self.ctx, 'CLUSTER_ID', 'details.ip')

        self.assertIn('cluster_attributes', res)
        self.assertIn({'id': 'NODE1', 'value': '1.2.3.4'},
                      res['cluster_attributes'])
        self.assertIn({'id': 'NODE2', 'value': '5.6.7.8'},
                      res['cluster_attributes'])
        mock_find.assert_called_once_with(self.ctx, 'CLUSTER_ID')
        mock_load.assert_called_once_with(self.ctx, cluster_id='FAKE_CLUSTER',
                                          project_safe=True)
        x_node_1.to_dict.assert_called_once_with()
        x_node_1.get_details.assert_called_once_with(self.ctx)
        x_node_2.to_dict.assert_called_once_with()
        x_node_2.get_details.assert_called_once_with(self.ctx)

    @mock.patch.object(service.EngineService, 'cluster_find')
    @mock.patch.object(common_utils, 'get_path_parser')
    def test_cluster_collect_bad_path(self, mock_parser, mock_find):
        mock_parser.side_effect = exc.BadRequest(msg='Boom')

        err = self.assertRaises(rpc.ExpectedException,
                                self.eng.cluster_collect,
                                self.ctx, 'CLUSTER-ID', 'foo.bar')

        self.assertEqual(exc.BadRequest, err.exc_info[0])
        mock_parser.assert_called_once_with('foo.bar')
        self.assertEqual(0, mock_find.call_count)

    @mock.patch.object(nm.Node, 'load_all')
    @mock.patch.object(service.EngineService, 'cluster_find')
    def test_cluster_collect_cluster_not_found(self, mock_find, mock_load):
        cid = 'FAKE_CLUSTER'
        mock_find.side_effect = exc.ClusterNotFound(cluster=cid)

        err = self.assertRaises(rpc.ExpectedException,
                                self.eng.cluster_collect,
                                self.ctx, cid, 'foo.bar')
        self.assertEqual(exc.ClusterNotFound, err.exc_info[0])
        mock_find.assert_called_once_with(self.ctx, cid)
        self.assertEqual(0, mock_load.call_count)

    @mock.patch.object(nm.Node, 'load_all')
    @mock.patch.object(service.EngineService, 'cluster_find')
    def test_cluster_collect_no_nodes(self, mock_find, mock_load):
        x_cluster = mock.Mock(id='FAKE_CLUSTER')
        mock_find.return_value = x_cluster
        mock_load.return_value = []

        res = self.eng.cluster_collect(self.ctx, 'CLUSTER_ID', 'bogus')

        self.assertEqual({'cluster_attributes': []}, res)
        mock_find.assert_called_once_with(self.ctx, 'CLUSTER_ID')
        mock_load.assert_called_once_with(self.ctx, cluster_id='FAKE_CLUSTER',
                                          project_safe=True)

    @mock.patch.object(nm.Node, 'load_all')
    @mock.patch.object(service.EngineService, 'cluster_find')
    def test_cluster_collect_no_details(self, mock_find, mock_load):
        x_cluster = mock.Mock(id='FAKE_CLUSTER')
        mock_find.return_value = x_cluster
        x_node_1 = mock.Mock(id='NODE1', physical_id=None)
        x_node_1.to_dict.return_value = {'name': 'node1'}
        x_node_2 = mock.Mock(id='NODE2', physical_id=None)
        x_node_2.to_dict.return_value = {'name': 'node2'}
        mock_load.return_value = [x_node_1, x_node_2]

        res = self.eng.cluster_collect(self.ctx, 'CLUSTER_ID', 'name')

        self.assertIn('cluster_attributes', res)
        self.assertIn({'id': 'NODE1', 'value': 'node1'},
                      res['cluster_attributes'])
        self.assertIn({'id': 'NODE2', 'value': 'node2'},
                      res['cluster_attributes'])
        mock_find.assert_called_once_with(self.ctx, 'CLUSTER_ID')
        mock_load.assert_called_once_with(self.ctx, cluster_id='FAKE_CLUSTER',
                                          project_safe=True)
        x_node_1.to_dict.assert_called_once_with()
        self.assertEqual(0, x_node_1.get_details.call_count)
        x_node_2.to_dict.assert_called_once_with()
        self.assertEqual(0, x_node_2.get_details.call_count)

    @mock.patch.object(nm.Node, 'load_all')
    @mock.patch.object(service.EngineService, 'cluster_find')
    def test_cluster_collect_no_match(self, mock_find, mock_load):
        x_cluster = mock.Mock(id='FAKE_CLUSTER')
        mock_find.return_value = x_cluster
        x_node_1 = mock.Mock(physical_id=None)
        x_node_1.to_dict.return_value = {'name': 'node1'}
        x_node_2 = mock.Mock(physical_id=None)
        x_node_2.to_dict.return_value = {'name': 'node2'}
        mock_load.return_value = [x_node_1, x_node_2]

        res = self.eng.cluster_collect(self.ctx, 'CLUSTER_ID', 'bogus')

        self.assertEqual({'cluster_attributes': []}, res)
        mock_find.assert_called_once_with(self.ctx, 'CLUSTER_ID')
        mock_load.assert_called_once_with(self.ctx, cluster_id='FAKE_CLUSTER',
                                          project_safe=True)
        x_node_1.to_dict.assert_called_once_with()
        self.assertEqual(0, x_node_1.get_details.call_count)
        x_node_2.to_dict.assert_called_once_with()
        self.assertEqual(0, x_node_2.get_details.call_count)

    @mock.patch.object(am.Action, 'create')
    @mock.patch.object(service.EngineService, 'cluster_find')
    @mock.patch.object(dispatcher, 'start_action')
    def test_cluster_check(self, notify, mock_find, mock_action):
        x_cluster = mock.Mock(id='CID')
        mock_find.return_value = x_cluster
        mock_action.return_value = 'ACTION_ID'

        params = {'foo': 'bar'}
        result = self.eng.cluster_check(self.ctx, 'CLUSTER', params)

        self.assertEqual({'action': 'ACTION_ID'}, result)
        mock_find.assert_called_once_with(self.ctx, 'CLUSTER')
        mock_action.assert_called_once_with(
            self.ctx, 'CID', consts.CLUSTER_CHECK,
            name='cluster_check_CID',
            cause=am.CAUSE_RPC,
            status=am.Action.READY,
            inputs={'foo': 'bar'},
        )
        notify.assert_called_once_with()

    @mock.patch.object(service.EngineService, 'cluster_find')
    def test_cluster_check_cluster_not_found(self, mock_find):
        mock_find.side_effect = exc.ClusterNotFound(cluster='Bogus')

        ex = self.assertRaises(rpc.ExpectedException,
                               self.eng.cluster_check,
                               self.ctx, 'Bogus')

        self.assertEqual(exc.ClusterNotFound, ex.exc_info[0])
        self.assertEqual('The cluster (Bogus) could not be found.',
                         six.text_type(ex.exc_info[1]))
        mock_find.assert_called_once_with(self.ctx, 'Bogus')

    @mock.patch.object(am.Action, 'create')
    @mock.patch.object(service.EngineService, 'cluster_find')
    @mock.patch.object(dispatcher, 'start_action')
    def test_cluster_recover(self, notify, mock_find, mock_action):
        x_cluster = mock.Mock(id='CID')
        mock_find.return_value = x_cluster
        mock_action.return_value = 'ACTION_ID'

        params = {'foo': 'bar'}
        result = self.eng.cluster_recover(self.ctx, 'CLUSTER', params)

        self.assertEqual({'action': 'ACTION_ID'}, result)
        mock_find.assert_called_once_with(self.ctx, 'CLUSTER')
        mock_action.assert_called_once_with(
            self.ctx, 'CID', consts.CLUSTER_RECOVER,
            name='cluster_recover_CID',
            cause=am.CAUSE_RPC,
            status=am.Action.READY,
            inputs={'foo': 'bar'},
        )
        notify.assert_called_once_with()

    @mock.patch.object(service.EngineService, 'cluster_find')
    def test_cluster_recover_cluster_not_found(self, mock_find):
        mock_find.side_effect = exc.ClusterNotFound(cluster='Bogus')

        ex = self.assertRaises(rpc.ExpectedException,
                               self.eng.cluster_recover,
                               self.ctx, 'Bogus')
        self.assertEqual(exc.ClusterNotFound, ex.exc_info[0])
        self.assertEqual('The cluster (Bogus) could not be found.',
                         six.text_type(ex.exc_info[1]))
        mock_find.assert_called_once_with(self.ctx, 'Bogus')
