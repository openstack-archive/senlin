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
from senlin.common.i18n import _
from senlin.db import api as db_api
from senlin.engine.actions import base as action_mod
from senlin.engine import cluster as cluster_mod
from senlin.engine import dispatcher
from senlin.engine import environment
from senlin.engine import service
from senlin.tests.unit.common import base
from senlin.tests.unit.common import utils
from senlin.tests.unit import fakes


class ClusterTest(base.SenlinTestCase):

    def setUp(self):
        super(ClusterTest, self).setUp()
        self.ctx = utils.dummy_context(project='cluster_test_project')
        self.eng = service.EngineService('host-a', 'topic-a')
        self.eng.init_tgm()

        self.eng.dispatcher = mock.Mock()

        env = environment.global_env()
        env.register_profile('TestProfile', fakes.TestProfile)
        env.register_policy('TestPolicy', fakes.TestPolicy)

        spec = {
            'type': 'TestProfile',
            'version': '1.0',
            'properties': {'INT': 10, 'STR': 'string'},
        }
        self.profile = self.eng.profile_create(self.ctx, 'p-test', spec,
                                               permission='1111')
        spec = {
            'type': 'TestPolicy',
            'version': '1.0',
            'properties': {'KEY2': 3}
        }
        self.policy = self.eng.policy_create(self.ctx, 'policy_1', spec,
                                             cooldown=60, level=50)

    def _verify_action(self, obj, action, name, target, cause, inputs=None):
        if inputs is None:
            inputs = {}
        self.assertEqual(action, obj['action'])
        self.assertEqual(name, obj['name'])
        self.assertEqual(target, obj['target'])
        self.assertEqual(cause, obj['cause'])
        self.assertEqual(inputs, obj['inputs'])

    @mock.patch.object(dispatcher, 'start_action')
    def test_cluster_create_default(self, notify):
        result = self.eng.cluster_create(self.ctx, 'c-1', 0,
                                         self.profile['id'])
        self.assertIsNotNone(result)
        self.assertEqual('c-1', result['name'])
        self.assertEqual(0, result['desired_capacity'])
        self.assertEqual(self.profile['id'], result['profile_id'])
        self.assertEqual(self.ctx.user, result['user'])
        self.assertEqual('cluster_test_project', result['project'])
        self.assertIsNone(result['parent'])
        self.assertIsNone(result['timeout'])
        self.assertIsNone(result['metadata'])

        action_id = result['action']
        action = db_api.action_get(self.ctx, result['action'])
        self.assertIsNotNone(action)
        self._verify_action(action, 'CLUSTER_CREATE',
                            'cluster_create_%s' % result['id'][:8],
                            result['id'],
                            cause=action_mod.CAUSE_RPC)
        notify.assert_called_once_with(action_id=action_id)

    @mock.patch.object(dispatcher, 'start_action')
    def test_cluster_create_with_timeout(self, notify):
        result = self.eng.cluster_create(self.ctx, 'c-1', 0,
                                         self.profile['id'],
                                         timeout=120)

        self.assertIsNotNone(result)
        self.assertEqual('c-1', result['name'])
        self.assertEqual(120, result['timeout'])

        ex = self.assertRaises(rpc.ExpectedException,
                               self.eng.cluster_create,
                               self.ctx, 'c-1', 0,
                               self.profile['id'],
                               timeout='N/A')

        self.assertEqual(exception.InvalidParameter, ex.exc_info[0])

    @mock.patch.object(dispatcher, 'start_action')
    def test_cluster_create_with_desired_capacity(self, notify):
        result = self.eng.cluster_create(self.ctx, 'c-1', 2,
                                         self.profile['id'])

        self.assertIsNotNone(result)
        self.assertEqual('c-1', result['name'])
        self.assertEqual(2, result['desired_capacity'])

        ex = self.assertRaises(rpc.ExpectedException,
                               self.eng.cluster_create,
                               self.ctx, 'c-1', 'Big',
                               self.profile['id'])

        self.assertEqual(exception.InvalidParameter, ex.exc_info[0])

    @mock.patch.object(dispatcher, 'start_action')
    def test_cluster_create_with_parent(self, notify):
        result = self.eng.cluster_create(self.ctx, 'c-1', 2,
                                         self.profile['id'],
                                         parent='fake id')

        self.assertIsNotNone(result)
        self.assertEqual('c-1', result['name'])
        self.assertEqual('fake id', result['parent'])

    @mock.patch.object(dispatcher, 'start_action')
    def test_cluster_create_with_metadata(self, notify):
        result = self.eng.cluster_create(self.ctx, 'c-1', 2,
                                         self.profile['id'],
                                         metadata={'k': 'v'})

        self.assertIsNotNone(result)
        self.assertEqual('c-1', result['name'])
        self.assertEqual({'k': 'v'}, result['metadata'])

    def test_cluster_create_profile_not_found(self):
        ex = self.assertRaises(rpc.ExpectedException,
                               self.eng.cluster_create,
                               self.ctx, 'c-1', 0, 'Bogus')
        self.assertEqual(exception.ProfileNotFound, ex.exc_info[0])

    @mock.patch.object(dispatcher, 'start_action')
    def test_cluster_create_with_profile_name_or_short_id(self, notify):
        result = self.eng.cluster_create(self.ctx, 'c-1', 0,
                                         self.profile['id'][:8])
        self.assertIsNotNone(result)
        self.assertEqual(self.profile['id'], result['profile_id'])

        result = self.eng.cluster_create(self.ctx, 'c-2', 0,
                                         self.profile['name'])
        self.assertIsNotNone(result)
        self.assertEqual(self.profile['id'], result['profile_id'])

    def test_validate_cluster_size_params_invalid_value(self):
        inputs = [
            (['big', 0, 1], 'big', 'desired_capacity'),
            ([-1, 0, 1], -1, 'desired_capacity'),
            ([1, 'small', 2], 'small', 'min_size'),
            ([1, -1, 2], -1, 'min_size'),
            ([1, 0, 'big'], 'big', 'max_size')
        ]

        for args, value, name in inputs:
            ex = self.assertRaises(exception.InvalidParameter,
                                   self.eng._validate_cluster_size_params,
                                   *args)
            self.assertEqual("Invalid value '%(value)s' specified for "
                             "'%(name)s'" % {'value': value, 'name': name},
                             six.text_type(ex))

    def test_validate_cluster_size_params_valid_value(self):
        inputs = [
            (['0', 0, 1], (0, 0, 1)),
            ([0, 0, 1], (0, 0, 1)),
            ([1, 1, 2], (1, 1, 2)),
            ([2, 2, 2], (2, 2, 2)),
            ([2, '2', 2], (2, 2, 2)),
            ([1, 0, '1'], (1, 0, 1)),
            ([1, 0, -1], (1, 0, -1)),
            ([100, 1, -1], (100, 1, -1)),
            ([100, 1, -2], (100, 1, -2)),
            ([None, None, None], (None, None, None)),
            ([None, 0, 1], (None, 0, 1)),
            ([None, 0, -1], (None, 0, -1)),
            ([1, None, 1], (1, None, 1)),
            ([1, None, -1], (1, None, -1)),
            ([1, 1, None], (1, 1, None)),
            ([None, None, 1], (None, None, 1)),
            ([None, None, -1], (None, None, -1)),
            ([None, 1, None], (None, 1, None)),
            ([1, None, None], (1, None, None)),
        ]

        for args, expected in inputs:
            result = self.eng._validate_cluster_size_params(*args)
            self.assertEqual(expected, result)

    def test_validate_cluster_size_params_invalid_combination(self):
        ex1 = ("Cluster min_size, if specified, must be lesser than or equal "
               "to its desired_capacity.")
        ex2 = ("Cluster max_size, if specified, must be greater than or equal "
               "to its desired_capacity. Setting max_size to -1 means no "
               "upper limit on cluster size.")
        ex3 = ("Cluster max_size, if specified, must be greater than or equal "
               "to its min_size. Setting max_size to -1 means no upper limit "
               "on cluster size.")

        inputs = [
            ([0, 1, None], ex1),
            ([0, 1, 1], ex1),
            ([2, 3, 2], ex1),
            ([0, 1, -1], ex1),
            ([2, 1, 1], ex2),
            ([3, 1, 2], ex2),
            ([1, None, 0], ex2),
            ([None, 1, 0], ex3),
        ]

        for args, expected in inputs:
            ex = self.assertRaises(exception.SenlinBadRequest,
                                   self.eng._validate_cluster_size_params,
                                   *args)

            self.assertEqual("The request is malformed: %s" % expected,
                             six.text_type(ex))

    @mock.patch.object(dispatcher, 'start_action')
    def test_cluster_get(self, notify):
        c = self.eng.cluster_create(self.ctx, 'c-1', 0,
                                    self.profile['id'])

        for identity in [c['id'], c['id'][:6], 'c-1']:
            result = self.eng.cluster_get(self.ctx, identity)
            self.assertIsInstance(result, dict)
            self.assertEqual(c['id'], result['id'])

        ex = self.assertRaises(rpc.ExpectedException,
                               self.eng.cluster_get, self.ctx, 'Bogus')
        self.assertEqual(exception.ClusterNotFound, ex.exc_info[0])

    @mock.patch.object(dispatcher, 'start_action')
    def test_cluster_list(self, notify):
        c1 = self.eng.cluster_create(self.ctx, 'c-1', 0, self.profile['id'])
        c2 = self.eng.cluster_create(self.ctx, 'c-2', 0, self.profile['id'])
        result = self.eng.cluster_list(self.ctx)
        self.assertIsInstance(result, list)
        names = [c['name'] for c in result]
        ids = [c['id'] for c in result]
        self.assertEqual(c1['name'], names[0])
        self.assertEqual(c2['name'], names[1])
        self.assertEqual(c1['id'], ids[0])
        self.assertEqual(c2['id'], ids[1])

    @mock.patch.object(dispatcher, 'start_action')
    def test_cluster_list_with_limit_marker(self, notify):
        c1 = self.eng.cluster_create(self.ctx, 'c-1', 0, self.profile['id'])
        c2 = self.eng.cluster_create(self.ctx, 'c-2', 0, self.profile['id'])
        result = self.eng.cluster_list(self.ctx, limit=0)

        self.assertEqual(0, len(result))
        result = self.eng.cluster_list(self.ctx, limit=1)
        self.assertEqual(1, len(result))
        result = self.eng.cluster_list(self.ctx, limit=2)
        self.assertEqual(2, len(result))
        result = self.eng.cluster_list(self.ctx, limit=3)
        self.assertEqual(2, len(result))

        result = self.eng.cluster_list(self.ctx, marker=c1['id'])
        self.assertEqual(1, len(result))
        result = self.eng.cluster_list(self.ctx, marker=c2['id'])
        self.assertEqual(0, len(result))

        self.eng.cluster_create(self.ctx, 'c-3', 0, self.profile['id'])

        result = self.eng.cluster_list(self.ctx, limit=1, marker=c1['id'])
        self.assertEqual(1, len(result))
        result = self.eng.cluster_list(self.ctx, limit=2, marker=c1['id'])
        self.assertEqual(2, len(result))

    @mock.patch.object(dispatcher, 'start_action')
    def test_cluster_list_with_sort_keys(self, notify):
        c1 = self.eng.cluster_create(self.ctx, 'CC', 0, self.profile['id'])
        c2 = self.eng.cluster_create(self.ctx, 'BB', 0, self.profile['id'])

        # default by created_time
        result = self.eng.cluster_list(self.ctx)
        self.assertEqual(c1['id'], result[0]['id'])
        self.assertEqual(c2['id'], result[1]['id'])

        # use name for sorting
        result = self.eng.cluster_list(self.ctx, sort_keys=['name'])
        self.assertEqual(c2['id'], result[0]['id'])
        self.assertEqual(c1['id'], result[1]['id'])

        # unknown keys will be ignored
        result = self.eng.cluster_list(self.ctx, sort_keys=['duang'])
        self.assertIsNotNone(result)

    @mock.patch.object(dispatcher, 'start_action')
    def test_cluster_list_with_sort_dir(self, notify):
        c1 = self.eng.cluster_create(self.ctx, 'BB', 0, self.profile['id'])
        c2 = self.eng.cluster_create(self.ctx, 'AA', 0, self.profile['id'])
        c3 = self.eng.cluster_create(self.ctx, 'CC', 0, self.profile['id'])

        # default by created_time, ascending
        result = self.eng.cluster_list(self.ctx)
        self.assertEqual(c1['id'], result[0]['id'])
        self.assertEqual(c2['id'], result[1]['id'])

        # sort by created_time, descending
        result = self.eng.cluster_list(self.ctx, sort_dir='desc')
        self.assertEqual(c3['id'], result[0]['id'])
        self.assertEqual(c2['id'], result[1]['id'])

        # use name for sorting, descending
        result = self.eng.cluster_list(self.ctx, sort_keys=['name'],
                                       sort_dir='desc')
        self.assertEqual(c3['id'], result[0]['id'])
        self.assertEqual(c1['id'], result[1]['id'])

        # use permission for sorting
        ex = self.assertRaises(ValueError,
                               self.eng.cluster_list, self.ctx,
                               sort_dir='Bogus')
        self.assertEqual("Unknown sort direction, must be one of: "
                         "asc-nullsfirst, asc-nullslast, desc-nullsfirst, "
                         "desc-nullslast", six.text_type(ex))

    @mock.patch.object(dispatcher, 'start_action')
    def test_cluster_list_show_deleted(self, notify):
        c = self.eng.cluster_create(self.ctx, 'c-1', 0, self.profile['id'])
        result = self.eng.cluster_list(self.ctx)
        self.assertEqual(1, len(result))
        self.assertEqual(c['id'], result[0]['id'])

        db_api.cluster_delete(self.ctx, c['id'])

        result = self.eng.cluster_list(self.ctx)
        self.assertEqual(0, len(result))

        result = self.eng.cluster_list(self.ctx, show_deleted=True)
        self.assertEqual(1, len(result))
        self.assertEqual(c['id'], result[0]['id'])

    @mock.patch.object(dispatcher, 'start_action')
    def test_cluster_list_show_nested(self, notify):
        c = self.eng.cluster_create(self.ctx, 'c-1', 0, self.profile['id'],
                                    parent='other-cluster')
        result = self.eng.cluster_list(self.ctx)
        self.assertEqual(0, len(result))

        result = self.eng.cluster_list(self.ctx, show_nested=True)
        self.assertEqual(1, len(result))
        self.assertEqual(c['id'], result[0]['id'])

    @mock.patch.object(dispatcher, 'start_action')
    def test_cluster_list_project_safe(self, notify):
        new_ctx = utils.dummy_context(project='a_diff_project')
        spec = {
            'type': 'TestProfile',
            'version': '1.0',
            'properties': {'INT': 10, 'STR': 'string'},
        }
        p1 = self.eng.profile_create(self.ctx, 'p-test-1', spec,
                                     permission='1111')
        p2 = self.eng.profile_create(new_ctx, 'p-test-2', spec,
                                     permission='1111')
        c1 = self.eng.cluster_create(self.ctx, 'c1', 0, p1['id'])
        c2 = self.eng.cluster_create(new_ctx, 'c2', 0, p2['id'])

        # default is project_safe
        result = self.eng.cluster_list(self.ctx)
        self.assertIsInstance(result, list)
        self.assertEqual(1, len(result))
        self.assertEqual(c1['id'], result[0]['id'])

        result = self.eng.cluster_list(new_ctx)
        self.assertIsInstance(result, list)
        self.assertEqual(1, len(result))
        self.assertEqual(c2['id'], result[0]['id'])

        # try project_safe set to False
        result = self.eng.cluster_list(self.ctx, project_safe=False)
        self.assertIsInstance(result, list)
        self.assertEqual(2, len(result))
        self.assertEqual(c1['id'], result[0]['id'])
        self.assertEqual(c2['id'], result[1]['id'])

    @mock.patch.object(dispatcher, 'start_action')
    def test_cluster_list_with_filters(self, notify):
        self.eng.cluster_create(self.ctx, 'BB', 0, self.profile['id'])
        self.eng.cluster_create(self.ctx, 'AA', 0, self.profile['id'])
        self.eng.cluster_create(self.ctx, 'CC', 0, self.profile['id'])

        result = self.eng.cluster_list(self.ctx, filters={'name': 'BB'})
        self.assertEqual(1, len(result))
        self.assertEqual('BB', result[0]['name'])

        result = self.eng.cluster_list(self.ctx, filters={'name': 'DD'})
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
                               show_nested='no')
        self.assertEqual(exception.InvalidParameter, ex.exc_info[0])

        ex = self.assertRaises(rpc.ExpectedException,
                               self.eng.cluster_list, self.ctx,
                               project_safe='no')
        self.assertEqual(exception.InvalidParameter, ex.exc_info[0])

    def test_cluster_list_empty(self):
        result = self.eng.cluster_list(self.ctx)
        self.assertIsInstance(result, list)
        self.assertEqual(0, len(result))

    @mock.patch.object(dispatcher, 'start_action')
    def test_cluster_find(self, notify):
        c = self.eng.cluster_create(self.ctx, 'c-1', 0, self.profile['id'])
        cid = c['id']

        result = self.eng.cluster_find(self.ctx, cid)
        self.assertIsNotNone(result)

        # short id
        result = self.eng.cluster_find(self.ctx, cid[:5])
        self.assertIsNotNone(result)

        # name
        result = self.eng.cluster_find(self.ctx, 'c-1')
        self.assertIsNotNone(result)

        # others
        self.assertRaises(exception.ClusterNotFound,
                          self.eng.cluster_find, self.ctx, 'Bogus')

    @mock.patch.object(dispatcher, 'start_action')
    def test_cluster_find_show_deleted(self, notify):
        c = self.eng.cluster_create(self.ctx, 'c-1', 0, self.profile['id'])
        cid = c['id']
        db_api.cluster_delete(self.ctx, cid)

        for identity in [cid, cid[:6], 'c-1']:
            self.assertRaises(exception.ClusterNotFound,
                              self.eng.cluster_find, self.ctx, identity)

        # short id and name based finding does not support show_deleted
        for identity in [cid[:6], 'c-1']:
            self.assertRaises(exception.ClusterNotFound,
                              self.eng.cluster_find, self.ctx, identity)

        # ID based finding is okay with show_deleted
        result = self.eng.cluster_find(self.ctx, cid, show_deleted=True)
        self.assertIsNotNone(result)

    @mock.patch.object(dispatcher, 'start_action')
    def test_cluster_update_simple_success(self, notify):
        c1 = self.eng.cluster_create(self.ctx, 'c-1', 0, self.profile['id'])
        cid = c1['id']

        # 1. update name
        self.eng.cluster_update(self.ctx, cid, name='c-2')
        c = self.eng.cluster_get(self.ctx, cid)
        self.assertEqual(cid, c['id'])
        self.assertEqual('c-2', c['name'])

        # 2. update parent
        p = self.eng.cluster_create(self.ctx, 'parent', 0, self.profile['id'])
        self.eng.cluster_update(self.ctx, cid, parent=p['id'])
        c = self.eng.cluster_get(self.ctx, cid)
        self.assertEqual(cid, c['id'])
        self.assertEqual(p['id'], c['parent'])

        # 3.1 update metadata
        self.eng.cluster_update(self.ctx, cid, metadata={'k': 'v'})
        c = self.eng.cluster_get(self.ctx, cid)
        self.assertEqual(cid, c['id'])
        self.assertEqual({'k': 'v'}, c['metadata'])

        # 3.2 update existing metadata
        self.eng.cluster_update(self.ctx, cid, metadata={'k': 'v1'})
        c = self.eng.cluster_get(self.ctx, cid)
        self.assertEqual(cid, c['id'])
        self.assertEqual({'k': 'v1'}, c['metadata'])

        # 4. update timeout
        self.eng.cluster_update(self.ctx, cid, timeout=119)
        c = self.eng.cluster_get(self.ctx, cid)
        self.assertEqual(cid, c['id'])
        self.assertEqual(119, c['timeout'])

    def test_cluster_update_cluster_not_found(self):
        ex = self.assertRaises(rpc.ExpectedException,
                               self.eng.cluster_update, self.ctx, 'Bogus')

        self.assertEqual(exception.ClusterNotFound, ex.exc_info[0])

    @mock.patch.object(dispatcher, 'start_action')
    def test_cluster_update_cluster_bad_status(self, notify):
        c = self.eng.cluster_create(self.ctx, 'c-1', 0, self.profile['id'])
        cluster = cluster_mod.Cluster.load(self.ctx, c['id'])
        cluster.set_status(self.ctx, cluster.DELETED, reason='test')

        ex = self.assertRaises(rpc.ExpectedException,
                               self.eng.cluster_update, self.ctx, c['id'],
                               name='new name')

        self.assertEqual(exception.ClusterNotFound, ex.exc_info[0])

    @mock.patch.object(dispatcher, 'start_action')
    def test_cluster_update_parent_not_found(self, notify):
        c = self.eng.cluster_create(self.ctx, 'c-1', 0, self.profile['id'])

        ex = self.assertRaises(rpc.ExpectedException,
                               self.eng.cluster_update, self.ctx, c['id'],
                               parent='Bogus')

        self.assertEqual(exception.ClusterNotFound, ex.exc_info[0])

    @mock.patch.object(dispatcher, 'start_action')
    def test_cluster_update_timeout_not_integer(self, notify):
        c = self.eng.cluster_create(self.ctx, 'c-1', 0, self.profile['id'])

        ex = self.assertRaises(rpc.ExpectedException,
                               self.eng.cluster_update, self.ctx, c['id'],
                               timeout='Long')

        self.assertEqual(exception.InvalidParameter, ex.exc_info[0])

    @mock.patch.object(dispatcher, 'start_action')
    def test_cluster_update_cluster_status_error(self, notify):
        c = self.eng.cluster_create(self.ctx, 'c-1', 0, self.profile['id'])
        cluster = cluster_mod.Cluster.load(self.ctx, c['id'])
        cluster.set_status(self.ctx, cluster.ERROR, reason='test')

        ex = self.assertRaises(rpc.ExpectedException,
                               self.eng.cluster_update, self.ctx, c['id'],
                               profile_id='good_profile')

        self.assertEqual(exception.FeatureNotSupported, ex.exc_info[0])

    @mock.patch.object(dispatcher, 'start_action')
    def test_cluster_update_update_to_same_profile(self, notify):
        c = self.eng.cluster_create(self.ctx, 'c-1', 0, self.profile['id'])
        result = self.eng.cluster_update(self.ctx, c['id'],
                                         profile_id=self.profile['id'])
        cluster = self.eng.cluster_get(self.ctx, c['id'])
        self.assertEqual(c['id'], cluster['id'])
        self.assertEqual(c['profile_id'], cluster['profile_id'])

        # No new action is generated during 'cluster_update' progress
        self.assertTrue('action' not in result)

    @mock.patch.object(dispatcher, 'start_action')
    def test_cluster_update_update_to_diff_profile_type(self, notify):
        # Register a different profile
        env = environment.global_env()
        env.register_profile('DiffProfileType', fakes.TestProfile)
        new_spec = {
            'type': 'DiffProfileType',
            'version': '1.0',
            'properties': {'INT': 10, 'STR': 'string'},
        }
        new_profile = self.eng.profile_create(
            self.ctx, 'p-test', new_spec, permission='1111')

        c = self.eng.cluster_create(self.ctx, 'c-1', 0, self.profile['id'])
        ex = self.assertRaises(rpc.ExpectedException,
                               self.eng.cluster_update,
                               self.ctx, c['id'], profile_id=new_profile['id'])

        self.assertEqual(exception.ProfileTypeNotMatch, ex.exc_info[0])

    @mock.patch.object(dispatcher, 'start_action')
    def test_cluster_update_profile_not_found(self, notify):
        c = self.eng.cluster_create(self.ctx, 'c-1', 0, self.profile['id'])
        ex = self.assertRaises(rpc.ExpectedException,
                               self.eng.cluster_update,
                               self.ctx, c['id'], profile_id='Bogus')

        self.assertEqual(exception.ProfileNotFound, ex.exc_info[0])

    @mock.patch.object(dispatcher, 'start_action')
    def test_cluster_update_profile_normal(self, notify):
        new_spec = {
            'type': 'TestProfile',
            'version': '1.0',
            'properties': {'INT': 20, 'STR': 'string new'},
        }
        new_profile = self.eng.profile_create(self.ctx, 'p-new', new_spec)

        c = self.eng.cluster_create(self.ctx, 'c-1', 0, self.profile['id'])
        self.eng.cluster_update(self.ctx, c['id'],
                                profile_id=new_profile['id'])

        # TODO(anyone): uncomment the following lines when cluster-update
        # is implemented
        # action_id = result['action']
        # action = self.eng.action_get(self.ctx, action_id)
        # self._verify_action(action, 'CLUSTER_UPDATE',
        #                     'cluster_update_%s' % c['id'][:8],
        #                     result['id'],
        #                     cause=action_mod.CAUSE_RPC)

        # notify.assert_called_once_with(self.ctx, action_id=action_id)

    @mock.patch.object(dispatcher, 'start_action')
    def test_cluster_delete(self, notify):
        c = self.eng.cluster_create(self.ctx, 'c-1', 0, self.profile['id'])
        cid = c['id']

        result = self.eng.cluster_delete(self.ctx, cid)
        self.assertIsNotNone(result)

        # verify action is fired
        action_id = result['action']
        action = self.eng.action_get(self.ctx, action_id)
        self._verify_action(action, 'CLUSTER_DELETE',
                            'cluster_delete_%s' % c['id'][:8],
                            c['id'],
                            cause=action_mod.CAUSE_RPC)

        expected_call = mock.call(action_id=mock.ANY)

        # two calls: one for create, the other for delete
        notify.assert_has_calls([expected_call] * 2)

    @mock.patch.object(dispatcher, 'start_action')
    def test_cluster_delete_policy_attached(self, notify):
        c = self.eng.cluster_create(self.ctx, 'c-1', 0, self.profile['id'])
        cid = c['id']
        db_api.cluster_policy_attach(self.ctx, cid, self.policy['id'], {})

        ex = self.assertRaises(rpc.ExpectedException,
                               self.eng.cluster_delete, self.ctx, cid)
        self.assertEqual(exception.SenlinBadRequest, ex.exc_info[0])
        self.assertEqual(_('The request is malformed: Cluster %(id)s is not '
                           'allowed to be deleted without detaching all '
                           'policies.') % {'id': cid},
                         six.text_type(ex.exc_info[1]))

    def test_cluster_delete_not_found(self):
        ex = self.assertRaises(rpc.ExpectedException,
                               self.eng.cluster_delete, self.ctx, 'Bogus')

        self.assertEqual(exception.ClusterNotFound, ex.exc_info[0])
        self.assertEqual('The cluster (Bogus) could not be found.',
                         six.text_type(ex.exc_info[1]))

    def _prepare_nodes(self, ctx, count=3, profile_id=None, **kwargs):
        '''Prepare nodes for add or delete.'''
        nodes = []
        for i in range(count):
            values = {
                'name': 'test_node_name',
                'physical_id': 'fake-phy-id-%s' % (i + 1),
                'cluster_id': None,
                'profile_id': profile_id or self.profile['id'],
                'project': ctx.project,
                'index': i + 1,
                'role': None,
                'created_time': None,
                'updated_time': None,
                'deleted_time': None,
                'status': 'ACTIVE',
                'status_reason': 'create complete',
                'metadata': {'foo': '123'},
                'data': {'key1': 'value1'},
            }
            values.update(kwargs)
            db_node = db_api.node_create(ctx, values)
            nodes.append(six.text_type(db_node.id))
        return nodes

    @mock.patch.object(dispatcher, 'start_action')
    def test_cluster_add_nodes(self, notify):
        c = self.eng.cluster_create(self.ctx, 'c-1', 0, self.profile['id'])
        cid = c['id']
        nodes = self._prepare_nodes(self.ctx)

        result = self.eng.cluster_add_nodes(self.ctx, cid, nodes)

        # verify action is fired
        action_id = result['action']
        action = self.eng.action_get(self.ctx, action_id)
        self._verify_action(action, 'CLUSTER_ADD_NODES',
                            'cluster_add_nodes_%s' % cid[:8],
                            cid, cause=action_mod.CAUSE_RPC,
                            inputs={'nodes': nodes})

        expected_call = mock.call(action_id=mock.ANY)

        # two calls: one for create, the other for adding nodes
        notify.assert_has_calls([expected_call] * 2)

    def test_cluster_add_nodes_cluster_not_found(self):
        ex = self.assertRaises(rpc.ExpectedException,
                               self.eng.cluster_add_nodes,
                               self.ctx, 'Bogus', ['n1', 'n2'])

        self.assertEqual(exception.ClusterNotFound, ex.exc_info[0])
        self.assertEqual('The cluster (Bogus) could not be found.',
                         six.text_type(ex.exc_info[1]))

    @mock.patch.object(dispatcher, 'start_action')
    def test_cluster_add_nodes_empty_list(self, notify):
        c = self.eng.cluster_create(self.ctx, 'c-1', 0, self.profile['id'])
        cid = c['id']

        ex = self.assertRaises(rpc.ExpectedException,
                               self.eng.cluster_add_nodes,
                               self.ctx, cid, [])

        self.assertEqual(exception.SenlinBadRequest, ex.exc_info[0])
        self.assertEqual('The request is malformed: No nodes to add: []',
                         six.text_type(ex.exc_info[1]))

    @mock.patch.object(dispatcher, 'start_action')
    def test_cluster_add_nodes_node_not_found(self, notify):
        c = self.eng.cluster_create(self.ctx, 'c-1', 0, self.profile['id'])
        cid = c['id']

        ex = self.assertRaises(rpc.ExpectedException,
                               self.eng.cluster_add_nodes,
                               self.ctx, cid, ['Bogus'])

        self.assertEqual(exception.SenlinBadRequest, ex.exc_info[0])
        self.assertEqual("The request is malformed: Nodes not found: "
                         "['Bogus']", six.text_type(ex.exc_info[1]))

    @mock.patch.object(dispatcher, 'start_action')
    def test_cluster_add_nodes_node_not_active(self, notify):
        c = self.eng.cluster_create(self.ctx, 'c-1', 0, self.profile['id'])
        cid = c['id']
        nodes = self._prepare_nodes(self.ctx, count=1, status='ERROR')
        ex = self.assertRaises(rpc.ExpectedException,
                               self.eng.cluster_add_nodes,
                               self.ctx, cid, nodes)

        self.assertEqual(exception.SenlinBadRequest, ex.exc_info[0])
        msg = _("Nodes are not ACTIVE: %s") % nodes
        self.assertEqual(_("The request is malformed: %(msg)s") % {'msg': msg},
                         six.text_type(ex.exc_info[1]))

    @mock.patch.object(dispatcher, 'start_action')
    def test_cluster_add_nodes_node_already_owned(self, notify):
        c1 = self.eng.cluster_create(self.ctx, 'c-1', 0, self.profile['id'])
        cid1 = c1['id']
        c2 = self.eng.cluster_create(self.ctx, 'c-2', 0, self.profile['id'])
        cid2 = c2['id']
        nodes1 = self._prepare_nodes(self.ctx, count=1, cluster_id=cid1)
        nodes2 = self._prepare_nodes(self.ctx, count=1, cluster_id=cid2)

        ex = self.assertRaises(rpc.ExpectedException,
                               self.eng.cluster_add_nodes,
                               self.ctx, cid1, nodes1)

        # adding from the same cluster is not allowed
        self.assertEqual(exception.NodeNotOrphan, ex.exc_info[0])
        msg = _("Nodes %s already owned by some cluster") % nodes1
        self.assertEqual(msg, six.text_type(ex.exc_info[1]))

        ex = self.assertRaises(rpc.ExpectedException,
                               self.eng.cluster_add_nodes,
                               self.ctx, cid1, nodes2)

        # adding from a different cluster is not allowed either
        self.assertEqual(exception.NodeNotOrphan, ex.exc_info[0])
        msg = _("Nodes %s already owned by some cluster") % nodes2
        self.assertEqual(msg, six.text_type(ex.exc_info[1]))

    @mock.patch.object(dispatcher, 'start_action')
    def test_cluster_add_nodes_node_profile_type_not_match(self, notify):
        c = self.eng.cluster_create(self.ctx, 'c-1', 0, self.profile['id'])
        # Register a different profile
        env = environment.global_env()
        env.register_profile('DiffProfileType', fakes.TestProfile)
        new_spec = {
            'type': 'DiffProfileType',
            'version': '1.0',
            'properties': {'INT': 10, 'STR': 'string'},
        }
        new_profile = self.eng.profile_create(
            self.ctx, 'p-test', new_spec, permission='1111')
        nodes = self._prepare_nodes(self.ctx, count=1,
                                    profile_id=new_profile['id'])

        ex = self.assertRaises(rpc.ExpectedException,
                               self.eng.cluster_add_nodes,
                               self.ctx, c['id'], nodes)

        self.assertEqual(exception.ProfileTypeNotMatch, ex.exc_info[0])
        msg = _("Profile type of nodes %s does not match with "
                "cluster") % nodes
        self.assertEqual(msg, six.text_type(ex.exc_info[1]))

    @mock.patch.object(dispatcher, 'start_action')
    def test_cluster_del_nodes(self, notify):
        c = self.eng.cluster_create(self.ctx, 'c-1', 0, self.profile['id'])
        cid = c['id']
        nodes = self._prepare_nodes(self.ctx, count=1, cluster_id=cid)

        result = self.eng.cluster_del_nodes(self.ctx, cid, nodes)

        # verify action is fired
        action_id = result['action']
        action = self.eng.action_get(self.ctx, action_id)
        self._verify_action(action, 'CLUSTER_DEL_NODES',
                            'cluster_del_nodes_%s' % cid[:8],
                            cid, cause=action_mod.CAUSE_RPC,
                            inputs={'candidates': nodes,
                                    'count': len(nodes)})

        expected_call = mock.call(action_id=mock.ANY)

        # two calls: one for create, the other for adding nodes
        notify.assert_has_calls([expected_call] * 2)

    def test_cluster_del_nodes_cluster_not_found(self):
        ex = self.assertRaises(rpc.ExpectedException,
                               self.eng.cluster_del_nodes,
                               self.ctx, 'Bogus', ['n1', 'n2'])

        self.assertEqual(exception.ClusterNotFound, ex.exc_info[0])
        self.assertEqual('The cluster (Bogus) could not be found.',
                         six.text_type(ex.exc_info[1]))

    @mock.patch.object(dispatcher, 'start_action')
    def test_cluster_del_nodes_empty_list(self, notify):
        c = self.eng.cluster_create(self.ctx, 'c-1', 0, self.profile['id'])
        cid = c['id']

        ex = self.assertRaises(rpc.ExpectedException,
                               self.eng.cluster_del_nodes,
                               self.ctx, cid, [])

        self.assertEqual(exception.SenlinBadRequest, ex.exc_info[0])
        self.assertEqual('The request is malformed: No nodes specified.',
                         six.text_type(ex.exc_info[1]))

    @mock.patch.object(dispatcher, 'start_action')
    def test_cluster_del_nodes_node_not_found(self, notify):
        c = self.eng.cluster_create(self.ctx, 'c-1', 0, self.profile['id'])
        cid = c['id']

        ex = self.assertRaises(rpc.ExpectedException,
                               self.eng.cluster_del_nodes,
                               self.ctx, cid, ['Bogus'])

        self.assertEqual(exception.SenlinBadRequest, ex.exc_info[0])
        self.assertEqual("The request is malformed: Nodes not found: "
                         "['Bogus']", six.text_type(ex.exc_info[1]))

    @mock.patch.object(dispatcher, 'start_action')
    def test_cluster_del_nodes_node_in_other_cluster(self, notify):
        c = self.eng.cluster_create(self.ctx, 'c-1', 0, self.profile['id'])
        c2 = self.eng.cluster_create(self.ctx, 'c-2', 0, self.profile['id'])
        cid = c['id']
        nodes = self._prepare_nodes(self.ctx, count=1, cluster_id=c2['id'])

        ex = self.assertRaises(rpc.ExpectedException,
                               self.eng.cluster_del_nodes,
                               self.ctx, cid, nodes)

        self.assertEqual(exception.SenlinBadRequest, ex.exc_info[0])
        self.assertEqual("The request is malformed: Nodes not members of "
                         "specified cluster: %s" % nodes,
                         six.text_type(ex.exc_info[1]))

    @mock.patch.object(dispatcher, 'start_action')
    def test_cluster_del_nodes_orphan_nodes(self, notify):
        c = self.eng.cluster_create(self.ctx, 'c-1', 0, self.profile['id'])
        cid = c['id']

        nodes = self._prepare_nodes(self.ctx, count=1)

        ex = self.assertRaises(rpc.ExpectedException,
                               self.eng.cluster_del_nodes,
                               self.ctx, cid, nodes)

        self.assertEqual(exception.SenlinBadRequest, ex.exc_info[0])
        self.assertEqual("The request is malformed: Nodes not members of "
                         "specified cluster: %s" % nodes,
                         six.text_type(ex.exc_info[1]))

    @mock.patch.object(dispatcher, 'start_action')
    def test_cluster_scale_out(self, notify):
        c = self.eng.cluster_create(self.ctx, 'c-1', 0, self.profile['id'])
        cid = c['id']

        result = self.eng.cluster_scale_out(self.ctx, cid, count=1)

        # verify action is fired
        action_id = result['action']
        action = self.eng.action_get(self.ctx, action_id)
        self._verify_action(action, 'CLUSTER_SCALE_OUT',
                            'cluster_scale_out_%s' % cid[:8],
                            cid, cause=action_mod.CAUSE_RPC,
                            inputs={'count': 1})

        expected_call = mock.call(action_id=mock.ANY)

        # two calls: one for create, the other for scaling operation
        notify.assert_has_calls([expected_call] * 2)

    @mock.patch.object(dispatcher, 'start_action')
    def test_cluster_scale_out_cluster_not_found(self, notify):
        ex = self.assertRaises(rpc.ExpectedException,
                               self.eng.cluster_scale_out,
                               self.ctx, 'Bogus')

        self.assertEqual(exception.ClusterNotFound, ex.exc_info[0])
        self.assertEqual('The cluster (Bogus) could not be found.',
                         six.text_type(ex.exc_info[1]))

    @mock.patch.object(dispatcher, 'start_action')
    def test_cluster_scale_out_count_is_none(self, notify):
        c = self.eng.cluster_create(self.ctx, 'c-1', 0, self.profile['id'])
        cid = c['id']

        result = self.eng.cluster_scale_out(self.ctx, cid)

        # verify action is fired
        action_id = result['action']
        action = self.eng.action_get(self.ctx, action_id)
        self._verify_action(action, 'CLUSTER_SCALE_OUT',
                            'cluster_scale_out_%s' % cid[:8],
                            cid, cause=action_mod.CAUSE_RPC,
                            inputs={})

        expected_call = mock.call(action_id=mock.ANY)

        # two calls: one for create, the other for scaling operation
        notify.assert_has_calls([expected_call] * 2)

    @mock.patch.object(dispatcher, 'start_action')
    def test_cluster_scale_out_count_not_int_or_zero(self, notify):
        c = self.eng.cluster_create(self.ctx, 'c-1', 0, self.profile['id'])
        cid = c['id']

        ex = self.assertRaises(rpc.ExpectedException,
                               self.eng.cluster_scale_out,
                               self.ctx, cid, count='one')

        self.assertEqual(exception.InvalidParameter, ex.exc_info[0])
        self.assertEqual("Invalid value 'one' specified for 'count'",
                         six.text_type(ex.exc_info[1]))

        ex = self.assertRaises(rpc.ExpectedException,
                               self.eng.cluster_scale_out,
                               self.ctx, cid, count=0)

        self.assertEqual(exception.InvalidParameter, ex.exc_info[0])
        self.assertEqual("Invalid value '0' specified for 'count'",
                         six.text_type(ex.exc_info[1]))

    @mock.patch.object(dispatcher, 'start_action')
    def test_cluster_scale_in(self, notify):
        c = self.eng.cluster_create(self.ctx, 'c-1', 2, self.profile['id'])
        cid = c['id']

        result = self.eng.cluster_scale_in(self.ctx, cid, count=1)

        # verify action is fired
        action_id = result['action']
        action = self.eng.action_get(self.ctx, action_id)
        self._verify_action(action, 'CLUSTER_SCALE_IN',
                            'cluster_scale_in_%s' % cid[:8],
                            cid, cause=action_mod.CAUSE_RPC,
                            inputs={'count': 1})

        expected_call = mock.call(action_id=mock.ANY)

        # two calls: one for create, the other for scaling operation
        notify.assert_has_calls([expected_call] * 2)

    @mock.patch.object(dispatcher, 'start_action')
    def test_cluster_scale_in_cluster_not_found(self, notify):
        ex = self.assertRaises(rpc.ExpectedException,
                               self.eng.cluster_scale_in,
                               self.ctx, 'Bogus')

        self.assertEqual(exception.ClusterNotFound, ex.exc_info[0])
        self.assertEqual('The cluster (Bogus) could not be found.',
                         six.text_type(ex.exc_info[1]))

    @mock.patch.object(dispatcher, 'start_action')
    def test_cluster_scale_in_count_is_none(self, notify):
        c = self.eng.cluster_create(self.ctx, 'c-1', 2, self.profile['id'])
        cid = c['id']

        result = self.eng.cluster_scale_in(self.ctx, cid)

        # verify action is fired
        action_id = result['action']
        action = self.eng.action_get(self.ctx, action_id)
        self._verify_action(action, 'CLUSTER_SCALE_IN',
                            'cluster_scale_in_%s' % cid[:8],
                            cid, cause=action_mod.CAUSE_RPC,
                            inputs={})

        expected_call = mock.call(action_id=mock.ANY)

        # two calls: one for create, the other for scaling operation
        notify.assert_has_calls([expected_call] * 2)

    @mock.patch.object(dispatcher, 'start_action')
    def test_cluster_scale_in_count_not_int_or_zero(self, notify):
        c = self.eng.cluster_create(self.ctx, 'c-1', 2, self.profile['id'])
        cid = c['id']

        ex = self.assertRaises(rpc.ExpectedException,
                               self.eng.cluster_scale_in,
                               self.ctx, cid, count='one')

        self.assertEqual(exception.InvalidParameter, ex.exc_info[0])
        self.assertEqual("Invalid value 'one' specified for 'count'",
                         six.text_type(ex.exc_info[1]))

        ex = self.assertRaises(rpc.ExpectedException,
                               self.eng.cluster_scale_in,
                               self.ctx, cid, count=0)

        self.assertEqual(exception.InvalidParameter, ex.exc_info[0])
        self.assertEqual("Invalid value '0' specified for 'count'",
                         six.text_type(ex.exc_info[1]))
