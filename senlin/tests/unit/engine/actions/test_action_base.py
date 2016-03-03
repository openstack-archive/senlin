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

import copy

import mock
from oslo_config import cfg
import six

from senlin.common import exception
from senlin.db.sqlalchemy import api as db_api
from senlin.engine.actions import base as action_base
from senlin.engine import cluster as cluster_mod
from senlin.engine import cluster_policy as cp_mod
from senlin.engine import environment
from senlin.engine import event as EVENT
from senlin.engine import node as node_mod
from senlin.policies import base as policy_mod
from senlin.tests.unit.common import base
from senlin.tests.unit.common import utils
from senlin.tests.unit import fakes


class DummyAction(action_base.Action):

    def __init__(self, target, action, context, **kwargs):
        super(DummyAction, self).__init__(target, action, context, **kwargs)


class ActionBaseTest(base.SenlinTestCase):

    def setUp(self):
        super(ActionBaseTest, self).setUp()

        self.ctx = utils.dummy_context()
        self.action_values = {
            'name': 'FAKE_NAME',
            'cause': 'FAKE_CAUSE',
            'owner': 'FAKE_OWNER',
            'interval': 60,
            'start_time': 0,
            'end_time': 0,
            'timeout': 120,
            'status': 'FAKE_STATUS',
            'status_reason': 'FAKE_STATUS_REASON',
            'inputs': {'param': 'value'},
            'outputs': {'key': 'output_value'},
            'created_at': None,
            'updated_at': None,
            'data': {'data_key': 'data_value'},
        }

    def _verify_new_action(self, obj, target, action):
        self.assertIsNone(obj.id)
        self.assertEqual('', obj.name)
        self.assertEqual('', obj.description)
        self.assertEqual(target, obj.target)
        self.assertEqual(action, obj.action)
        self.assertEqual('', obj.cause)
        self.assertIsNone(obj.owner)
        self.assertEqual(-1, obj.interval)
        self.assertIsNone(obj.start_time)
        self.assertIsNone(obj.end_time)
        self.assertEqual(cfg.CONF.default_action_timeout, obj.timeout)
        self.assertEqual('INIT', obj.status)
        self.assertEqual('', obj.status_reason)
        self.assertEqual({}, obj.inputs)
        self.assertEqual({}, obj.outputs)
        self.assertIsNone(obj.created_at)
        self.assertIsNone(obj.updated_at)
        self.assertEqual({}, obj.data)

    @mock.patch.object(node_mod.Node, 'load')
    @mock.patch.object(cluster_mod.Cluster, 'load')
    def test_action_new(self, mock_n_load, mock_c_load):
        for action in ['CLUSTER_CREATE', 'NODE_CREATE', 'WHAT_EVER']:
            obj = action_base.Action('OBJID', action, self.ctx)
            self._verify_new_action(obj, 'OBJID', action)

    def test_action_init_with_values(self):
        values = copy.deepcopy(self.action_values)
        values['id'] = 'FAKE_ID'
        values['description'] = 'FAKE_DESC'
        values['created_at'] = 'FAKE_CREATED_TIME'
        values['updated_at'] = 'FAKE_UPDATED_TIME'

        obj = action_base.Action('OBJID', 'OBJECT_ACTION', self.ctx,
                                 **values)

        self.assertEqual('FAKE_ID', obj.id)
        self.assertEqual('FAKE_NAME', obj.name)
        self.assertEqual('FAKE_DESC', obj.description)
        self.assertEqual('OBJID', obj.target)
        self.assertEqual('FAKE_CAUSE', obj.cause)
        self.assertEqual('FAKE_OWNER', obj.owner)
        self.assertEqual(60, obj.interval)
        self.assertEqual(0, obj.start_time)
        self.assertEqual(0, obj.end_time)
        self.assertEqual(120, obj.timeout)
        self.assertEqual('FAKE_STATUS', obj.status)
        self.assertEqual('FAKE_STATUS_REASON', obj.status_reason)
        self.assertEqual({'param': 'value'}, obj.inputs)
        self.assertEqual({'key': 'output_value'}, obj.outputs)
        self.assertEqual('FAKE_CREATED_TIME', obj.created_at)
        self.assertEqual('FAKE_UPDATED_TIME', obj.updated_at)
        self.assertEqual({'data_key': 'data_value'}, obj.data)

    def test_action_store_for_create(self):
        values = copy.deepcopy(self.action_values)
        obj = action_base.Action('OBJID', 'OBJECT_ACTION', self.ctx,
                                 **values)

        self.assertIsNone(obj.created_at)
        self.assertIsNone(obj.updated_at)

        # store for creation
        res = obj.store(self.ctx)
        self.assertIsNotNone(res)
        self.assertEqual(obj.id, res)
        self.assertIsNotNone(obj.created_at)
        self.assertIsNone(obj.updated_at)

    def test_action_store_for_update(self):
        values = copy.deepcopy(self.action_values)

        obj = action_base.Action('OBJID', 'OBJECT_ACTION', self.ctx,
                                 **values)
        obj_id = obj.store(self.ctx)
        self.assertIsNotNone(obj_id)
        self.assertIsNotNone(obj.created_at)
        self.assertIsNone(obj.updated_at)

        # store for creation
        res = obj.store(self.ctx)
        self.assertIsNotNone(res)
        self.assertEqual(obj_id, res)
        self.assertEqual(obj.id, res)
        self.assertIsNotNone(obj.created_at)
        self.assertIsNotNone(obj.updated_at)

    def test_from_db_record(self):
        values = copy.deepcopy(self.action_values)
        obj = action_base.Action('OBJID', 'OBJECT_ACTION', self.ctx,
                                 **values)
        obj.store(self.ctx)

        record = db_api.action_get(self.ctx, obj.id)

        action_obj = action_base.Action._from_db_record(record)
        self.assertIsInstance(action_obj, action_base.Action)
        self.assertEqual(obj.id, action_obj.id)
        self.assertEqual(obj.action, action_obj.action)
        self.assertEqual(obj.name, action_obj.name)
        self.assertEqual(obj.target, action_obj.target)
        self.assertEqual(obj.cause, action_obj.cause)
        self.assertEqual(obj.owner, action_obj.owner)
        self.assertEqual(obj.interval, action_obj.interval)
        self.assertEqual(obj.start_time, action_obj.start_time)
        self.assertEqual(obj.end_time, action_obj.end_time)
        self.assertEqual(obj.timeout, action_obj.timeout)
        self.assertEqual(obj.status, action_obj.status)
        self.assertEqual(obj.status_reason, action_obj.status_reason)
        self.assertEqual(obj.inputs, action_obj.inputs)
        self.assertEqual(obj.outputs, action_obj.outputs)
        self.assertEqual(obj.created_at, action_obj.created_at)
        self.assertEqual(obj.updated_at, action_obj.updated_at)
        self.assertEqual(obj.data, action_obj.data)
        self.assertEqual(obj.user, action_obj.user)
        self.assertEqual(obj.project, action_obj.project)
        self.assertEqual(obj.domain, action_obj.domain)

    def test_from_db_record_with_empty_fields(self):
        values = copy.deepcopy(self.action_values)
        del values['inputs']
        del values['outputs']
        obj = action_base.Action('OBJID', 'OBJECT_ACTION', self.ctx,
                                 **values)
        obj.store(self.ctx)
        record = db_api.action_get(self.ctx, obj.id)
        action_obj = action_base.Action._from_db_record(record)
        self.assertEqual({}, action_obj.inputs)
        self.assertEqual({}, action_obj.outputs)

    def test_load(self):
        values = copy.deepcopy(self.action_values)
        obj = action_base.Action('OBJID', 'OBJECT_ACTION', self.ctx, **values)
        obj.store(self.ctx)

        result = action_base.Action.load(self.ctx, obj.id, None)
        # no need to do a thorough test here
        self.assertEqual(obj.id, result.id)
        self.assertEqual(obj.action, result.action)

        db_action = db_api.action_get(self.ctx, obj.id)
        result = action_base.Action.load(self.ctx, None, db_action)
        # no need to do a thorough test here
        self.assertEqual(obj.id, result.id)
        self.assertEqual(obj.action, result.action)

    def test_load_not_found(self):
        # not found due to bad identity
        ex = self.assertRaises(exception.ActionNotFound,
                               action_base.Action.load,
                               self.ctx, 'non-existent', None)
        self.assertEqual('The action (non-existent) could not be found.',
                         six.text_type(ex))

        # not found due to no object
        self.patchobject(db_api, 'action_get', return_value=None)
        ex = self.assertRaises(exception.ActionNotFound,
                               action_base.Action.load,
                               self.ctx, 'whatever', None)
        self.assertEqual('The action (whatever) could not be found.',
                         six.text_type(ex))

    def test_load_all(self):
        result = action_base.Action.load_all(self.ctx)
        self.assertEqual([], [c for c in result])

        values = copy.deepcopy(self.action_values)
        action1 = action_base.Action('OBJID', 'OBJECT_ACTION', self.ctx,
                                     **values)
        action1.store(self.ctx)
        action2 = action_base.Action('OBJID', 'OBJECT_ACTION', self.ctx,
                                     **values)
        action2.store(self.ctx)

        # NOTE: we don't test all other parameters because the db api tests
        #       already covered that
        results = list(action_base.Action.load_all(self.ctx))
        actions = [a.id for a in results]
        self.assertEqual(2, len(actions))
        self.assertIn(action1.id, actions)
        self.assertIn(action2.id, actions)

    @mock.patch.object(db_api, 'action_get_all')
    def test_load_all_with_params(self, mock_call):
        mock_call.return_value = []

        results = action_base.Action.load_all(
            self.ctx, filters='FAKE_FILTER', limit='FAKE_LIMIT',
            marker='FAKE_MARKER', sort='FAKE_SORT')

        # the following line is important, or else the generator won't get
        # called.
        self.assertEqual([], list(results))
        mock_call.assert_called_once_with(
            self.ctx, filters='FAKE_FILTER', limit='FAKE_LIMIT',
            marker='FAKE_MARKER', sort='FAKE_SORT',
            project_safe=True)

    @mock.patch.object(action_base.Action, 'store')
    def test_action_create(self, mock_store):
        mock_store.return_value = 'FAKE_ID'

        result = action_base.Action.create(self.ctx, 'OBJ_ID', 'CLUSTER_DANCE',
                                           name='test')

        self.assertEqual('FAKE_ID', result)
        mock_store.assert_called_once_with(self.ctx)

    def test_action_delete(self):
        result = action_base.Action.delete(self.ctx, 'non-existent')
        self.assertIsNone(result)

        values = copy.deepcopy(self.action_values)
        action1 = action_base.Action('OBJID', 'OBJECT_ACTION', self.ctx,
                                     **values)
        action1.store(self.ctx)

        result = action_base.Action.delete(self.ctx, action1.id)
        self.assertIsNone(result)

    @mock.patch.object(db_api, 'action_delete')
    def test_action_delete_db_call(self, mock_call):
        # test db api call
        action_base.Action.delete(self.ctx, 'FAKE_ID')
        mock_call.assert_called_once_with(self.ctx, 'FAKE_ID', False)

    @mock.patch.object(db_api, 'action_signal')
    def test_action_signal_bad_command(self, mock_call):
        values = copy.deepcopy(self.action_values)
        action1 = action_base.Action('OBJID', 'OBJECT_ACTION', self.ctx,
                                     **values)
        action1.store(self.ctx)

        result = action1.signal('BOGUS')
        self.assertIsNone(result)
        self.assertEqual(0, mock_call.call_count)

    @mock.patch.object(db_api, 'action_signal')
    @mock.patch.object(EVENT, 'error')
    def test_action_signal_cancel(self, mock_error, mock_call):
        values = copy.deepcopy(self.action_values)
        action = action_base.Action('OBJID', 'OBJECT_ACTION', self.ctx,
                                    **values)
        action.store(self.ctx)

        expected = [action.INIT, action.WAITING, action.READY, action.RUNNING]
        for status in expected:
            action.status = status
            result = action.signal(action.SIG_CANCEL)
            self.assertIsNone(result)
            self.assertEqual(1, mock_call.call_count)
            mock_call.reset_mock()

        invalid = [action.SUSPENDED, action.SUCCEEDED, action.CANCELLED,
                   action.FAILED]
        for status in invalid:
            action.status = status
            result = action.signal(action.SIG_CANCEL)
            self.assertIsNone(result)
            self.assertEqual(0, mock_call.call_count)
            mock_call.reset_mock()
            self.assertEqual(1, mock_error.call_count)
            mock_error.reset_mock()

    @mock.patch.object(db_api, 'action_signal')
    @mock.patch.object(EVENT, 'error')
    def test_action_signal_suspend(self, mock_error, mock_call):
        action = action_base.Action('OBJID', 'OBJECT_ACTION', self.ctx)

        expected = [action.RUNNING]
        for status in expected:
            action.status = status
            result = action.signal(action.SIG_SUSPEND)
            self.assertIsNone(result)
            self.assertEqual(1, mock_call.call_count)
            mock_call.reset_mock()

        invalid = [action.INIT, action.WAITING, action.READY, action.SUSPENDED,
                   action.SUCCEEDED, action.CANCELLED, action.FAILED]
        for status in invalid:
            action.status = status
            result = action.signal(action.SIG_SUSPEND)
            self.assertIsNone(result)
            self.assertEqual(0, mock_call.call_count)
            mock_call.reset_mock()
            self.assertEqual(1, mock_error.call_count)
            mock_error.reset_mock()

    @mock.patch.object(db_api, 'action_signal')
    @mock.patch.object(EVENT, 'error')
    def test_action_signal_resume(self, mock_error, mock_call):
        action = action_base.Action('OBJID', 'OBJECT_ACTION', self.ctx)

        expected = [action.SUSPENDED]
        for status in expected:
            action.status = status
            result = action.signal(action.SIG_RESUME)
            self.assertIsNone(result)
            self.assertEqual(1, mock_call.call_count)
            mock_call.reset_mock()

        invalid = [action.INIT, action.WAITING, action.READY, action.RUNNING,
                   action.SUCCEEDED, action.CANCELLED, action.FAILED]
        for status in invalid:
            action.status = status
            result = action.signal(action.SIG_RESUME)
            self.assertIsNone(result)
            self.assertEqual(0, mock_call.call_count)
            mock_call.reset_mock()
            self.assertEqual(1, mock_error.call_count)
            mock_error.reset_mock()

    def test_execute_default(self):
        action = action_base.Action.__new__(DummyAction, 'OBJID', 'BOOM',
                                            self.ctx)
        res = action.execute()
        self.assertEqual(NotImplemented, res)

    @mock.patch.object(db_api, 'action_mark_succeeded')
    @mock.patch.object(db_api, 'action_mark_failed')
    @mock.patch.object(db_api, 'action_mark_cancelled')
    @mock.patch.object(db_api, 'action_abandon')
    def test_set_status(self, mock_abandon, mark_cancel, mark_fail,
                        mark_succeed):
        action = action_base.Action('OBJID', 'OBJECT_ACTION', self.ctx)
        action.id = 'FAKE_ID'

        action.set_status(action.RES_OK, 'FAKE_REASON')
        self.assertEqual(action.SUCCEEDED, action.status)
        self.assertEqual('FAKE_REASON', action.status_reason)
        mark_succeed.assert_called_once_with(action.context, 'FAKE_ID',
                                             mock.ANY)

        action.set_status(action.RES_ERROR, 'FAKE_ERROR')
        self.assertEqual(action.FAILED, action.status)
        self.assertEqual('FAKE_ERROR', action.status_reason)
        mark_fail.assert_called_once_with(action.context, 'FAKE_ID', mock.ANY,
                                          'FAKE_ERROR')

        mark_fail.reset_mock()
        action.set_status(action.RES_TIMEOUT, 'TIMEOUT_ERROR')
        self.assertEqual(action.FAILED, action.status)
        self.assertEqual('TIMEOUT_ERROR', action.status_reason)
        mark_fail.assert_called_once_with(action.context, 'FAKE_ID', mock.ANY,
                                          'TIMEOUT_ERROR')

        mark_fail.reset_mock()
        action.set_status(action.RES_CANCEL, 'CANCELLED')
        self.assertEqual(action.CANCELLED, action.status)
        self.assertEqual('CANCELLED', action.status_reason)
        mark_cancel.assert_called_once_with(action.context, 'FAKE_ID',
                                            mock.ANY)

        mark_fail.reset_mock()
        action.set_status(action.RES_RETRY, 'BUSY')
        self.assertEqual(action.READY, action.status)
        self.assertEqual('BUSY', action.status_reason)
        mock_abandon.assert_called_once_with(action.context, 'FAKE_ID')

    @mock.patch.object(db_api, 'action_check_status')
    def test_get_status(self, mock_get):
        mock_get.return_value = 'FAKE_STATUS'

        action = action_base.Action('OBJID', 'OBJECT_ACTION', self.ctx)
        action.id = 'FAKE_ID'

        res = action.get_status()

        self.assertEqual('FAKE_STATUS', res)
        self.assertEqual('FAKE_STATUS', action.status)
        mock_get.assert_called_once_with(action.context, 'FAKE_ID', mock.ANY)

    @mock.patch.object(action_base, 'wallclock')
    def test_is_timeout(self, mock_time):
        action = action_base.Action.__new__(DummyAction, 'OBJ', 'BOOM',
                                            self.ctx)
        action.start_time = 1
        action.timeout = 10

        mock_time.return_value = 9
        self.assertFalse(action.is_timeout())

        mock_time.return_value = 10
        self.assertFalse(action.is_timeout())

        mock_time.return_value = 11
        self.assertFalse(action.is_timeout())

        mock_time.return_value = 12
        self.assertTrue(action.is_timeout())

    def test_check_signal_timeout(self):
        action = action_base.Action('OBJID', 'OBJECT_ACTION', self.ctx)
        action.id = 'FAKE_ID'
        action.timeout = 10
        self.patchobject(action, 'is_timeout', return_value=True)

        res = action._check_signal()
        self.assertEqual(action.RES_TIMEOUT, res)

    @mock.patch.object(db_api, 'action_signal_query')
    def test_check_signal_signals_caught(self, mock_query):
        action = action_base.Action('OBJID', 'OBJECT_ACTION', self.ctx)
        action.id = 'FAKE_ID'
        action.timeout = 100
        self.patchobject(action, 'is_timeout', return_value=False)
        sig_cmd = mock.Mock()
        mock_query.return_value = sig_cmd

        res = action._check_signal()
        self.assertEqual(sig_cmd, res)
        mock_query.assert_called_once_with(action.context, 'FAKE_ID')

    @mock.patch.object(db_api, 'action_signal_query')
    def test_is_cancelled(self, mock_query):
        action = action_base.Action('OBJID', 'OBJECT_ACTION', self.ctx)
        action.id = 'FAKE_ID'
        action.timeout = 100
        self.patchobject(action, 'is_timeout', return_value=False)

        mock_query.return_value = action.SIG_CANCEL
        res = action.is_cancelled()
        self.assertTrue(res)
        mock_query.assert_called_once_with(action.context, 'FAKE_ID')
        mock_query.reset_mock()

        mock_query.return_value = None
        res = action.is_cancelled()
        self.assertFalse(res)
        mock_query.assert_called_once_with(action.context, 'FAKE_ID')

    @mock.patch.object(db_api, 'action_signal_query')
    def test_is_suspended(self, mock_query):
        action = action_base.Action('OBJID', 'OBJECT_ACTION', self.ctx)
        action.id = 'FAKE_ID'
        action.timeout = 100
        self.patchobject(action, 'is_timeout', return_value=False)

        mock_query.return_value = action.SIG_SUSPEND
        res = action.is_suspended()
        self.assertTrue(res)
        mock_query.assert_called_once_with(action.context, 'FAKE_ID')
        mock_query.reset_mock()

        mock_query.return_value = 'OTHERS'
        res = action.is_suspended()
        self.assertFalse(res)
        mock_query.assert_called_once_with(action.context, 'FAKE_ID')

    @mock.patch.object(db_api, 'action_signal_query')
    def test_is_resumed(self, mock_query):
        action = action_base.Action('OBJID', 'OBJECT_ACTION', self.ctx)
        action.id = 'FAKE_ID'
        action.timeout = 100
        self.patchobject(action, 'is_timeout', return_value=False)

        mock_query.return_value = action.SIG_RESUME
        res = action.is_resumed()
        self.assertTrue(res)
        mock_query.assert_called_once_with(action.context, 'FAKE_ID')
        mock_query.reset_mock()

        mock_query.return_value = 'OTHERS'
        res = action.is_resumed()
        self.assertFalse(res)
        mock_query.assert_called_once_with(action.context, 'FAKE_ID')

    @mock.patch.object(cp_mod.ClusterPolicy, 'load_all')
    def test_policy_check_target_invalid(self, mock_load):
        action = action_base.Action('OBJID', 'OBJECT_ACTION', self.ctx)
        res = action.policy_check('FAKE_CLUSTER', 'WHEN')
        self.assertIsNone(res)
        self.assertEqual(0, mock_load.call_count)

    @mock.patch.object(cp_mod.ClusterPolicy, 'load_all')
    def test_policy_check_no_bindings(self, mock_load):
        action = action_base.Action('OBJID', 'OBJECT_ACTION', self.ctx)
        mock_load.return_value = []
        res = action.policy_check('FAKE_CLUSTER', 'BEFORE')
        self.assertIsNone(res)
        self.assertEqual(policy_mod.CHECK_OK, action.data['status'])
        mock_load.assert_called_once_with(action.context, 'FAKE_CLUSTER',
                                          sort='priority',
                                          filters={'enabled': True})

    @mock.patch.object(db_api, 'dependency_get_depended')
    @mock.patch.object(db_api, 'dependency_get_dependents')
    def test_action_to_dict(self, mock_dep_by, mock_dep_on):
        mock_dep_on.return_value = ['ACTION_1']
        mock_dep_by.return_value = ['ACTION_2']
        action = action_base.Action('OBJID', 'OBJECT_ACTION', self.ctx,
                                    **self.action_values)
        action.id = 'FAKE_ID'
        expected = {
            'id': 'FAKE_ID',
            'name': 'FAKE_NAME',
            'action': 'OBJECT_ACTION',
            'target': 'OBJID',
            'cause': 'FAKE_CAUSE',
            'owner': 'FAKE_OWNER',
            'interval': 60,
            'start_time': 0,
            'end_time': 0,
            'timeout': 120,
            'status': 'FAKE_STATUS',
            'status_reason': 'FAKE_STATUS_REASON',
            'inputs': {'param': 'value'},
            'outputs': {'key': 'output_value'},
            'depends_on': ['ACTION_1'],
            'depended_by': ['ACTION_2'],
            'created_at': None,
            'updated_at': None,
            'data': {'data_key': 'data_value'},
        }

        res = action.to_dict()
        self.assertEqual(expected, res)
        mock_dep_on.assert_called_once_with(action.context, 'FAKE_ID')
        mock_dep_by.assert_called_once_with(action.context, 'FAKE_ID')


class ActionPolicyCheckTest(base.SenlinTestCase):

    def setUp(self):
        super(ActionPolicyCheckTest, self).setUp()

        self.ctx = utils.dummy_context()
        environment.global_env().register_policy('DummyPolicy',
                                                 fakes.TestPolicy)

    def _create_policy(self):
        values = {
            'user': self.ctx.user,
            'project': self.ctx.project,
        }
        policy = fakes.TestPolicy('DummyPolicy', 'test-policy', **values)
        policy.store(self.ctx)
        return policy

    def _create_cp_binding(self, cluster_id, policy_id):
        values = {'enabled': True}

        pb = cp_mod.ClusterPolicy(cluster_id, policy_id, **values)
        pb.id = 'FAKE_BINDING_ID'
        return pb

    @mock.patch.object(policy_mod.Policy, 'post_op')
    @mock.patch.object(policy_mod.Policy, 'pre_op')
    @mock.patch.object(cp_mod.ClusterPolicy, 'load_all')
    @mock.patch.object(policy_mod.Policy, 'load')
    def test_policy_check_missing_target(self, mock_load, mock_load_all,
                                         mock_pre_op, mock_post_op):
        cluster_id = 'FAKE_CLUSTER_ID'
        # Note: policy is mocked
        spec = {
            'type': 'TestPolicy',
            'version': '1.0',
            'properties': {'KEY2': 5},
        }
        policy = fakes.TestPolicy('test-policy', spec)
        policy.id = 'FAKE_POLICY_ID'
        policy.TARGET = [('BEFORE', 'OBJECT_ACTION')]
        # Note: policy binding is created but not stored
        pb = self._create_cp_binding(cluster_id, policy.id)
        self.assertIsNone(pb.last_op)
        mock_load_all.return_value = [pb]
        mock_load.return_value = policy
        mock_pre_op.return_value = None
        mock_post_op.return_value = None
        action = action_base.Action(cluster_id, 'OBJECT_ACTION_1', self.ctx)

        res = action.policy_check(cluster_id, 'AFTER')

        self.assertIsNone(res)
        self.assertEqual(policy_mod.CHECK_OK, action.data['status'])
        mock_load_all.assert_called_once_with(
            action.context, cluster_id, sort='priority',
            filters={'enabled': True})
        mock_load.assert_called_once_with(action.context, policy.id)
        # last_op was updated anyway
        self.assertIsNotNone(pb.last_op)
        # neither pre_op nor post_op was called, because target not match
        self.assertEqual(0, mock_pre_op.call_count)
        self.assertEqual(0, mock_post_op.call_count)

    @mock.patch.object(cp_mod.ClusterPolicy, 'load_all')
    @mock.patch.object(policy_mod.Policy, 'load')
    def test_policy_check_pre_op(self, mock_load, mock_load_all):
        cluster_id = 'FAKE_CLUSTER_ID'
        # Note: policy is mocked
        spec = {
            'type': 'TestPolicy',
            'version': '1.0',
            'properties': {'KEY2': 5},
        }
        policy = fakes.TestPolicy('test-policy', spec)
        policy.id = 'FAKE_POLICY_ID'
        policy.TARGET = [('BEFORE', 'OBJECT_ACTION')]
        # Note: policy binding is created but not stored
        pb = self._create_cp_binding(cluster_id, policy.id)
        self.assertIsNone(pb.last_op)
        mock_load_all.return_value = [pb]
        mock_load.return_value = policy
        action = action_base.Action(cluster_id, 'OBJECT_ACTION', self.ctx)

        res = action.policy_check(cluster_id, 'BEFORE')

        self.assertIsNone(res)
        self.assertEqual(policy_mod.CHECK_OK, action.data['status'])
        mock_load_all.assert_called_once_with(
            action.context, cluster_id, sort='priority',
            filters={'enabled': True})
        mock_load.assert_called_once_with(action.context, policy.id)
        # last_op was not updated
        self.assertIsNone(pb.last_op)

    @mock.patch.object(cp_mod.ClusterPolicy, 'load_all')
    @mock.patch.object(policy_mod.Policy, 'load')
    def test_policy_check_post_op(self, mock_load, mock_load_all):
        cluster_id = 'FAKE_CLUSTER_ID'
        # Note: policy is mocked
        policy = mock.Mock()
        policy.id = 'FAKE_POLICY_ID'
        policy.TARGET = [('AFTER', 'OBJECT_ACTION')]
        policy.cooldown = 0
        # Note: policy binding is created but not stored
        pb = self._create_cp_binding(cluster_id, policy.id)
        self.assertIsNone(pb.last_op)
        mock_load_all.return_value = [pb]
        mock_load.return_value = policy
        action = action_base.Action(cluster_id, 'OBJECT_ACTION', self.ctx)

        res = action.policy_check('FAKE_CLUSTER_ID', 'AFTER')

        self.assertIsNone(res)
        self.assertEqual(policy_mod.CHECK_OK, action.data['status'])
        mock_load_all.assert_called_once_with(
            action.context, cluster_id, sort='priority',
            filters={'enabled': True})
        mock_load.assert_called_once_with(action.context, policy.id)
        # last_op was updated for POST check
        self.assertIsNotNone(pb.last_op)
        # pre_op is called, but post_op was not called
        self.assertEqual(0, policy.pre_op.call_count)
        policy.post_op.assert_called_once_with(cluster_id, action)

    @mock.patch.object(cp_mod.ClusterPolicy, 'load_all')
    @mock.patch.object(policy_mod.Policy, 'load')
    def test_policy_check_cooldown_inprogress(self, mock_load, mock_load_all):
        cluster_id = 'FAKE_CLUSTER_ID'
        # Note: policy is mocked
        policy = mock.Mock()
        policy.id = 'FAKE_POLICY_ID'
        policy.TARGET = [('AFTER', 'OBJECT_ACTION')]
        # Note: policy binding is created but not stored
        pb = self._create_cp_binding(cluster_id, policy.id)
        self.patchobject(pb, 'cooldown_inprogress', return_value=True)
        self.assertIsNone(pb.last_op)
        mock_load_all.return_value = [pb]
        mock_load.return_value = policy
        action = action_base.Action(cluster_id, 'OBJECT_ACTION', self.ctx)

        res = action.policy_check('FAKE_CLUSTER_ID', 'AFTER')

        self.assertIsNone(res)
        self.assertEqual(policy_mod.CHECK_ERROR, action.data['status'])
        self.assertEqual('Policy FAKE_POLICY_ID cooldown is still in '
                         'progress.', six.text_type(action.data['reason']))
        mock_load_all.assert_called_once_with(
            action.context, cluster_id, sort='priority',
            filters={'enabled': True})
        mock_load.assert_called_once_with(action.context, policy.id)
        # last_op was updated for POST check
        self.assertIsNotNone(pb.last_op)
        # neither pre_op nor post_op was not called, due to cooldown
        self.assertEqual(0, policy.pre_op.call_count)
        self.assertEqual(0, policy.post_op.call_count)

    @mock.patch.object(cp_mod.ClusterPolicy, 'load_all')
    @mock.patch.object(policy_mod.Policy, 'load')
    @mock.patch.object(action_base.Action, '_check_result')
    def test_policy_check_abort_in_middle(self, mock_check, mock_load,
                                          mock_load_all):
        cluster_id = 'FAKE_CLUSTER_ID'
        # Note: both policies are mocked
        policy1 = mock.Mock()
        policy1.id = 'FAKE_POLICY_ID_1'
        policy1.name = 'P1'
        policy1.cooldown = 0
        policy1.TARGET = [('AFTER', 'OBJECT_ACTION')]
        policy2 = mock.Mock()
        policy2.id = 'FAKE_POLICY_ID_2'
        policy2.name = 'P2'
        policy2.cooldown = 0
        policy2.TARGET = [('AFTER', 'OBJECT_ACTION')]

        action = action_base.Action(cluster_id, 'OBJECT_ACTION', self.ctx)

        # Note: policy binding is created but not stored
        pb1 = self._create_cp_binding(cluster_id, policy1.id)
        pb2 = self._create_cp_binding(cluster_id, policy2.id)
        mock_load_all.return_value = [pb1, pb2]
        # mock return value for two calls
        mock_load.side_effect = [policy1, policy2]
        mock_check.side_effect = [False, True]

        res = action.policy_check(cluster_id, 'AFTER')

        self.assertIsNone(res)

        # post_op from policy1 was called, but post_op from policy2 was not
        policy1.post_op.assert_called_once_with(cluster_id, action)
        self.assertEqual(0, policy2.post_op.call_count)

        mock_load_all.assert_called_once_with(
            action.context, cluster_id, sort='priority',
            filters={'enabled': True})
        calls = [mock.call(action.context, policy1.id)]
        mock_load.assert_has_calls(calls)


class ActionProcTest(base.SenlinTestCase):

    def setUp(self):
        super(ActionProcTest, self).setUp()

        self.ctx = utils.dummy_context()

    @mock.patch.object(EVENT, 'info')
    @mock.patch.object(action_base.Action, 'load')
    @mock.patch.object(db_api, 'action_mark_succeeded')
    def test_action_proc_successful(self, mock_mark, mock_load,
                                    mock_event_info):
        action = action_base.Action('OBJID', 'OBJECT_ACTION', self.ctx)
        action.owner = 'WORKER'
        action.start_time = 123456
        self.patchobject(action, 'execute',
                         return_value=(action.RES_OK, 'BIG SUCCESS'))
        mock_load.return_value = action

        res = action_base.ActionProc(self.ctx, 'ACTION')
        self.assertTrue(res)

        mock_load.assert_called_once_with(self.ctx, action_id='ACTION')
        self.assertEqual(action.SUCCEEDED, action.status)
        self.assertEqual('WORKER', action.owner)
        self.assertEqual(123456, action.start_time)
        self.assertEqual('BIG SUCCESS', action.status_reason)

    @mock.patch.object(EVENT, 'info')
    @mock.patch.object(action_base.Action, 'load')
    @mock.patch.object(db_api, 'action_mark_failed')
    def test_action_proc_failed_error(self, mock_mark, mock_load,
                                      mock_event_info):
        action = action_base.Action('OBJID', 'OBJECT_ACTION', self.ctx)
        action.owner = 'WORKER'
        action.start_time = 123456
        self.patchobject(action, 'execute', side_effect=Exception('Boom!'))
        mock_load.return_value = action

        res = action_base.ActionProc(self.ctx, 'ACTION')
        self.assertFalse(res)

        mock_load.assert_called_once_with(self.ctx, action_id='ACTION')
        self.assertEqual(action.FAILED, action.status)
        self.assertEqual('Boom!', action.status_reason)
