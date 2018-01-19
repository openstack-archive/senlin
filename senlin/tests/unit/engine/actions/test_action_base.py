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
import eventlet

import mock
from oslo_config import cfg
from oslo_utils import timeutils
from oslo_utils import uuidutils
import six

from senlin.common import consts
from senlin.common import exception
from senlin.common import utils as common_utils
from senlin.engine.actions import base as ab
from senlin.engine import cluster as cluster_mod
from senlin.engine import dispatcher
from senlin.engine import environment
from senlin.engine import event as EVENT
from senlin.engine import node as node_mod
from senlin.objects import action as ao
from senlin.objects import cluster_policy as cpo
from senlin.objects import dependency as dobj
from senlin.policies import base as policy_mod
from senlin.tests.unit.common import base
from senlin.tests.unit.common import utils
from senlin.tests.unit import fakes

CLUSTER_ID = 'e1cfd82b-dc95-46ad-86e8-37864d7be1cd'
OBJID = '571fffb8-f41c-4cbc-945c-cb2937d76f19'
OWNER_ID = 'c7114713-ee68-409d-ba5d-0560a72a386c'
ACTION_ID = '4c2cead2-fd74-418a-9d12-bd2d9bd7a812'
USER_ID = '3c4d64baadcd437d8dd49054899e73dd'
PROJECT_ID = 'cf7a6ae28dde4f46aa8fe55d318a608f'


class DummyAction(ab.Action):

    def __init__(self, target, action, context, **kwargs):
        super(DummyAction, self).__init__(target, action, context, **kwargs)


class ActionBaseTest(base.SenlinTestCase):

    def setUp(self):
        super(ActionBaseTest, self).setUp()

        self.ctx = utils.dummy_context(project=PROJECT_ID, user_id=USER_ID)
        self.action_values = {
            'name': 'FAKE_NAME',
            'cause': 'FAKE_CAUSE',
            'owner': OWNER_ID,
            'interval': 60,
            'start_time': 0,
            'end_time': 0,
            'timeout': 120,
            'status': 'FAKE_STATUS',
            'status_reason': 'FAKE_STATUS_REASON',
            'inputs': {'param': 'value'},
            'outputs': {'key': 'output_value'},
            'created_at': timeutils.utcnow(True),
            'updated_at': None,
            'data': {'data_key': 'data_value'},
        }

    def _verify_new_action(self, obj, target, action):
        self.assertIsNone(obj.id)
        self.assertEqual('', obj.name)
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

    @mock.patch.object(cluster_mod.Cluster, 'load')
    def test_action_new_cluster(self, mock_load):
        fake_cluster = mock.Mock(timeout=cfg.CONF.default_action_timeout)
        mock_load.return_value = fake_cluster
        obj = ab.Action(OBJID, 'CLUSTER_CREATE', self.ctx)
        self._verify_new_action(obj, OBJID, 'CLUSTER_CREATE')

    @mock.patch.object(node_mod.Node, 'load')
    def test_action_new_node(self, mock_load):
        obj = ab.Action(OBJID, 'NODE_CREATE', self.ctx)
        self._verify_new_action(obj, OBJID, 'NODE_CREATE')

    def test_action_init_with_values(self):
        values = copy.deepcopy(self.action_values)
        values['id'] = 'FAKE_ID'
        values['created_at'] = 'FAKE_CREATED_TIME'
        values['updated_at'] = 'FAKE_UPDATED_TIME'

        obj = ab.Action(OBJID, 'OBJECT_ACTION', self.ctx, **values)

        self.assertEqual('FAKE_ID', obj.id)
        self.assertEqual('FAKE_NAME', obj.name)
        self.assertEqual(OBJID, obj.target)
        self.assertEqual('FAKE_CAUSE', obj.cause)
        self.assertEqual(OWNER_ID, obj.owner)
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
        obj = ab.Action(OBJID, 'OBJECT_ACTION', self.ctx, **values)

        self.assertEqual(common_utils.isotime(values['created_at']),
                         common_utils.isotime(obj.created_at))
        self.assertIsNone(obj.updated_at)

        # store for creation
        res = obj.store(self.ctx)
        self.assertIsNotNone(res)
        self.assertEqual(obj.id, res)
        self.assertIsNotNone(obj.created_at)
        self.assertIsNone(obj.updated_at)

    def test_action_store_for_update(self):
        values = copy.deepcopy(self.action_values)

        obj = ab.Action(OBJID, 'OBJECT_ACTION', self.ctx, **values)
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
        obj = ab.Action(OBJID, 'OBJECT_ACTION', self.ctx, **values)
        obj.store(self.ctx)

        record = ao.Action.get(self.ctx, obj.id)

        action_obj = ab.Action._from_object(record)
        self.assertIsInstance(action_obj, ab.Action)
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
        self.assertEqual(common_utils.isotime(obj.created_at),
                         common_utils.isotime(action_obj.created_at))
        self.assertEqual(obj.updated_at, action_obj.updated_at)
        self.assertEqual(obj.data, action_obj.data)
        self.assertEqual(obj.user, action_obj.user)
        self.assertEqual(obj.project, action_obj.project)
        self.assertEqual(obj.domain, action_obj.domain)

    def test_from_db_record_with_empty_fields(self):
        values = copy.deepcopy(self.action_values)
        del values['inputs']
        del values['outputs']
        obj = ab.Action(OBJID, 'OBJECT_ACTION', self.ctx, **values)
        obj.store(self.ctx)
        record = ao.Action.get(self.ctx, obj.id)
        action_obj = ab.Action._from_object(record)
        self.assertEqual({}, action_obj.inputs)
        self.assertEqual({}, action_obj.outputs)

    def test_load(self):
        values = copy.deepcopy(self.action_values)
        obj = ab.Action(OBJID, 'OBJECT_ACTION', self.ctx, **values)
        obj.store(self.ctx)

        result = ab.Action.load(self.ctx, obj.id, None)
        # no need to do a thorough test here
        self.assertEqual(obj.id, result.id)
        self.assertEqual(obj.action, result.action)

        db_action = ao.Action.get(self.ctx, obj.id)
        result = ab.Action.load(self.ctx, None, db_action)
        # no need to do a thorough test here
        self.assertEqual(obj.id, result.id)
        self.assertEqual(obj.action, result.action)

    def test_load_not_found(self):
        # not found due to bad identity
        ex = self.assertRaises(exception.ResourceNotFound,
                               ab.Action.load,
                               self.ctx, 'non-existent', None)
        self.assertEqual("The action 'non-existent' could not be "
                         "found.", six.text_type(ex))

        # not found due to no object
        self.patchobject(ao.Action, 'get', return_value=None)
        ex = self.assertRaises(exception.ResourceNotFound,
                               ab.Action.load,
                               self.ctx, 'whatever', None)
        self.assertEqual("The action 'whatever' could not be found.",
                         six.text_type(ex))

    @mock.patch.object(ab.Action, 'store')
    def test_action_create(self, mock_store):
        mock_store.return_value = 'FAKE_ID'

        result = ab.Action.create(self.ctx, OBJID, 'CLUSTER_DANCE',
                                  name='test')

        self.assertEqual('FAKE_ID', result)
        mock_store.assert_called_once_with(self.ctx)

    def test_action_delete(self):
        result = ab.Action.delete(self.ctx, 'non-existent')
        self.assertIsNone(result)

        values = copy.deepcopy(self.action_values)
        action1 = ab.Action(OBJID, 'OBJECT_ACTION', self.ctx, **values)
        action1.store(self.ctx)

        result = ab.Action.delete(self.ctx, action1.id)
        self.assertIsNone(result)

    @mock.patch.object(ao.Action, 'delete')
    def test_action_delete_db_call(self, mock_call):
        # test db api call
        ab.Action.delete(self.ctx, 'FAKE_ID')
        mock_call.assert_called_once_with(self.ctx, 'FAKE_ID')

    @mock.patch.object(ao.Action, 'signal')
    def test_action_signal_bad_command(self, mock_call):
        values = copy.deepcopy(self.action_values)
        action1 = ab.Action(OBJID, 'OBJECT_ACTION', self.ctx, **values)
        action1.store(self.ctx)

        result = action1.signal('BOGUS')
        self.assertIsNone(result)
        self.assertEqual(0, mock_call.call_count)

    @mock.patch.object(ao.Action, 'signal')
    def test_action_signal_cancel(self, mock_call):
        values = copy.deepcopy(self.action_values)
        action = ab.Action(OBJID, 'OBJECT_ACTION', self.ctx, **values)
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

    @mock.patch.object(ao.Action, 'signal')
    def test_action_signal_suspend(self, mock_call):
        action = ab.Action(OBJID, 'OBJECT_ACTION', self.ctx, id=ACTION_ID)

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

    @mock.patch.object(ao.Action, 'signal')
    def test_action_signal_resume(self, mock_call):
        action = ab.Action(OBJID, 'OBJECT_ACTION', self.ctx, id=ACTION_ID)

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

    def test_execute_default(self):
        action = ab.Action.__new__(DummyAction, OBJID, 'BOOM', self.ctx)
        self.assertRaises(NotImplementedError,
                          action.execute)

    @mock.patch.object(EVENT, 'info')
    @mock.patch.object(EVENT, 'error')
    @mock.patch.object(EVENT, 'warning')
    @mock.patch.object(ao.Action, 'mark_succeeded')
    @mock.patch.object(ao.Action, 'mark_failed')
    @mock.patch.object(ao.Action, 'mark_cancelled')
    @mock.patch.object(ao.Action, 'mark_ready')
    @mock.patch.object(ao.Action, 'abandon')
    @mock.patch.object(dispatcher, 'start_action')
    @mock.patch.object(eventlet, 'sleep')
    def test_set_status(self, mock_sleep, mock_start, mock_abandon,
                        mark_ready, mark_cancel, mark_fail,
                        mark_succeed, mock_event, mock_error,
                        mock_info):
        action = ab.Action(OBJID, 'OBJECT_ACTION', self.ctx, id='FAKE_ID')
        action.entity = mock.Mock()

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
        action.set_status(action.RES_LIFECYCLE_COMPLETE, 'LIFECYCLE COMPLETE')
        self.assertEqual(action.SUCCEEDED, action.status)
        self.assertEqual('LIFECYCLE COMPLETE', action.status_reason)
        mark_ready.assert_called_once_with(action.context, 'FAKE_ID', mock.ANY)

        mark_fail.reset_mock()
        action.set_status(action.RES_RETRY, 'BUSY')
        self.assertEqual(action.READY, action.status)
        self.assertEqual('BUSY', action.status_reason)
        mock_start.assert_called_once_with(action.id)
        mock_sleep.assert_called_once_with(10)
        mock_abandon.assert_called_once_with(
            action.context, 'FAKE_ID', {'data': {'retries': 1}})

        mark_fail.reset_mock()
        action.data = {'retries': 3}
        action.set_status(action.RES_RETRY, 'BUSY')
        self.assertEqual(action.RES_ERROR, action.status)
        mark_fail.assert_called_once_with(action.context, 'FAKE_ID', mock.ANY,
                                          'BUSY')

    @mock.patch.object(EVENT, 'info')
    @mock.patch.object(EVENT, 'error')
    @mock.patch.object(EVENT, 'warning')
    @mock.patch.object(ao.Action, 'mark_succeeded')
    @mock.patch.object(ao.Action, 'mark_failed')
    @mock.patch.object(ao.Action, 'abandon')
    def test_set_status_dump_event(self, mock_abandon, mark_fail,
                                   mark_succeed, mock_warning, mock_error,
                                   mock_info):
        action = ab.Action(OBJID, 'OBJECT_ACTION', self.ctx, id='FAKE_ID')
        action.entity = mock.Mock()

        action.set_status(action.RES_OK, 'FAKE_SUCCEEDED')
        mock_info.assert_called_once_with(action, consts.PHASE_END,
                                          'FAKE_SUCCEEDED')

        action.set_status(action.RES_ERROR, 'FAKE_ERROR')
        mock_error.assert_called_once_with(action, consts.PHASE_ERROR,
                                           'FAKE_ERROR')

        action.set_status(action.RES_RETRY, 'FAKE_RETRY')
        mock_warning.assert_called_once_with(action, consts.PHASE_ERROR,
                                             'FAKE_RETRY')

    @mock.patch.object(EVENT, 'info')
    @mock.patch.object(EVENT, 'error')
    @mock.patch.object(EVENT, 'warning')
    @mock.patch.object(ao.Action, 'mark_succeeded')
    @mock.patch.object(ao.Action, 'mark_failed')
    @mock.patch.object(ao.Action, 'abandon')
    def test_set_status_reason_is_none(self, mock_abandon, mark_fail,
                                       mark_succeed, mock_warning, mock_error,
                                       mock_info):
        action = ab.Action(OBJID, 'OBJECT_ACTION', self.ctx, id='FAKE_ID')
        action.entity = mock.Mock()

        action.set_status(action.RES_OK)
        mock_info.assert_called_once_with(action, consts.PHASE_END,
                                          'SUCCEEDED')

        action.set_status(action.RES_ERROR)
        mock_error.assert_called_once_with(action, consts.PHASE_ERROR,
                                           'ERROR')

        action.set_status(action.RES_RETRY)
        mock_warning.assert_called_once_with(action, consts.PHASE_ERROR,
                                             'RETRY')

    @mock.patch.object(ao.Action, 'check_status')
    def test_get_status(self, mock_get):
        mock_get.return_value = 'FAKE_STATUS'

        action = ab.Action(OBJID, 'OBJECT_ACTION', self.ctx)
        action.id = 'FAKE_ID'

        res = action.get_status()

        self.assertEqual('FAKE_STATUS', res)
        self.assertEqual('FAKE_STATUS', action.status)
        mock_get.assert_called_once_with(action.context, 'FAKE_ID', mock.ANY)

    @mock.patch.object(ab, 'wallclock')
    def test_is_timeout(self, mock_time):
        action = ab.Action.__new__(DummyAction, 'OBJ', 'BOOM', self.ctx)
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

    @mock.patch.object(EVENT, 'debug')
    def test_check_signal_timeout(self, mock_debug):
        action = ab.Action(OBJID, 'OBJECT_ACTION', self.ctx, id='FAKE_ID',
                           timeout=10)
        action.entity = mock.Mock()
        self.patchobject(action, 'is_timeout', return_value=True)

        res = action._check_signal()
        self.assertEqual(action.RES_TIMEOUT, res)

    @mock.patch.object(ao.Action, 'signal_query')
    def test_check_signal_signals_caught(self, mock_query):
        action = ab.Action(OBJID, 'OBJECT_ACTION', self.ctx)
        action.id = 'FAKE_ID'
        action.timeout = 100
        self.patchobject(action, 'is_timeout', return_value=False)
        sig_cmd = mock.Mock()
        mock_query.return_value = sig_cmd

        res = action._check_signal()
        self.assertEqual(sig_cmd, res)
        mock_query.assert_called_once_with(action.context, 'FAKE_ID')

    @mock.patch.object(ao.Action, 'signal_query')
    def test_is_cancelled(self, mock_query):
        action = ab.Action(OBJID, 'OBJECT_ACTION', self.ctx)
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

    @mock.patch.object(ao.Action, 'signal_query')
    def test_is_suspended(self, mock_query):
        action = ab.Action(OBJID, 'OBJECT_ACTION', self.ctx)
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

    @mock.patch.object(ao.Action, 'signal_query')
    def test_is_resumed(self, mock_query):
        action = ab.Action(OBJID, 'OBJECT_ACTION', self.ctx)
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

    @mock.patch.object(cpo.ClusterPolicy, 'get_all')
    def test_policy_check_target_invalid(self, mock_load):
        action = ab.Action(OBJID, 'OBJECT_ACTION', self.ctx)

        res = action.policy_check('FAKE_CLUSTER', 'WHEN')

        self.assertIsNone(res)
        self.assertEqual(0, mock_load.call_count)

    @mock.patch.object(cpo.ClusterPolicy, 'get_all')
    def test_policy_check_no_bindings(self, mock_load):
        action = ab.Action(OBJID, 'OBJECT_ACTION', self.ctx)
        mock_load.return_value = []

        res = action.policy_check('FAKE_CLUSTER', 'BEFORE')

        self.assertIsNone(res)
        self.assertEqual(policy_mod.CHECK_OK, action.data['status'])
        mock_load.assert_called_once_with(action.context, 'FAKE_CLUSTER',
                                          sort='priority',
                                          filters={'enabled': True})

    @mock.patch.object(dobj.Dependency, 'get_depended')
    @mock.patch.object(dobj.Dependency, 'get_dependents')
    def test_action_to_dict(self, mock_dep_by, mock_dep_on):
        mock_dep_on.return_value = ['ACTION_1']
        mock_dep_by.return_value = ['ACTION_2']
        action = ab.Action(OBJID, 'OBJECT_ACTION', self.ctx,
                           **self.action_values)
        action.id = 'FAKE_ID'
        ts = common_utils.isotime(self.action_values['created_at'])
        expected = {
            'id': 'FAKE_ID',
            'name': 'FAKE_NAME',
            'action': 'OBJECT_ACTION',
            'target': OBJID,
            'cause': 'FAKE_CAUSE',
            'owner': OWNER_ID,
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
            'created_at': ts,
            'updated_at': None,
            'data': {'data_key': 'data_value'},
            'user': USER_ID,
            'project': PROJECT_ID,
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
            'user': self.ctx.user_id,
            'project': self.ctx.project_id,
        }
        policy = fakes.TestPolicy('DummyPolicy', 'test-policy', **values)
        policy.store(self.ctx)
        return policy

    def _create_cp_binding(self, cluster_id, policy_id):
        return cpo.ClusterPolicy(cluster_id=cluster_id, policy_id=policy_id,
                                 enabled=True, id=uuidutils.generate_uuid(),
                                 last_op=None)

    @mock.patch.object(policy_mod.Policy, 'post_op')
    @mock.patch.object(policy_mod.Policy, 'pre_op')
    @mock.patch.object(cpo.ClusterPolicy, 'get_all')
    @mock.patch.object(policy_mod.Policy, 'load')
    def test_policy_check_missing_target(self, mock_load, mock_load_all,
                                         mock_pre_op, mock_post_op):
        cluster_id = CLUSTER_ID
        # Note: policy is mocked
        spec = {
            'type': 'TestPolicy',
            'version': '1.0',
            'properties': {'KEY2': 5},
        }
        policy = fakes.TestPolicy('test-policy', spec)
        policy.id = uuidutils.generate_uuid()
        policy.TARGET = [('BEFORE', 'OBJECT_ACTION')]
        # Note: policy binding is created but not stored
        pb = self._create_cp_binding(cluster_id, policy.id)
        self.assertIsNone(pb.last_op)
        mock_load_all.return_value = [pb]
        mock_load.return_value = policy
        mock_pre_op.return_value = None
        mock_post_op.return_value = None
        action = ab.Action(cluster_id, 'OBJECT_ACTION_1', self.ctx)

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

    def test__check_result_true(self):
        cluster_id = CLUSTER_ID
        action = ab.Action(cluster_id, 'OBJECT_ACTION', self.ctx)
        action.data['status'] = policy_mod.CHECK_OK
        action.data['reason'] = "Completed policy checking."

        res = action._check_result('FAKE_POLICY_NAME')

        self.assertTrue(res)

    def test__check_result_false(self):
        cluster_id = CLUSTER_ID
        action = ab.Action(cluster_id, 'OBJECT_ACTION', self.ctx)
        action.data['status'] = policy_mod.CHECK_ERROR
        reason = ("Policy '%s' cooldown is still in progress." %
                  'FAKE_POLICY_2')
        action.data['reason'] = reason

        res = action._check_result('FAKE_POLICY_NAME')
        reason = ("Failed policy '%(name)s': %(reason)s"
                  ) % {'name': 'FAKE_POLICY_NAME', 'reason': reason}
        self.assertFalse(res)

    @mock.patch.object(cpo.ClusterPolicy, 'get_all')
    @mock.patch.object(policy_mod.Policy, 'load')
    def test_policy_check_pre_op(self, mock_load, mock_load_all):
        cluster_id = CLUSTER_ID
        # Note: policy is mocked
        spec = {
            'type': 'TestPolicy',
            'version': '1.0',
            'properties': {'KEY2': 5},
        }
        policy = fakes.TestPolicy('test-policy', spec)
        policy.id = uuidutils.generate_uuid()
        policy.TARGET = [('BEFORE', 'OBJECT_ACTION')]
        # Note: policy binding is created but not stored
        pb = self._create_cp_binding(cluster_id, policy.id)
        self.assertIsNone(pb.last_op)
        mock_load_all.return_value = [pb]
        mock_load.return_value = policy
        entity = mock.Mock()
        action = ab.Action(cluster_id, 'OBJECT_ACTION', self.ctx)
        action.entity = entity

        res = action.policy_check(cluster_id, 'BEFORE')

        self.assertIsNone(res)
        self.assertEqual(policy_mod.CHECK_OK, action.data['status'])
        mock_load_all.assert_called_once_with(
            action.context, cluster_id, sort='priority',
            filters={'enabled': True})
        mock_load.assert_called_once_with(action.context, policy.id)
        # last_op was not updated
        self.assertIsNone(pb.last_op)

    @mock.patch.object(cpo.ClusterPolicy, 'get_all')
    @mock.patch.object(policy_mod.Policy, 'load')
    def test_policy_check_post_op(self, mock_load, mock_load_all):
        cluster_id = CLUSTER_ID
        # Note: policy is mocked
        policy = mock.Mock(id=uuidutils.generate_uuid(), cooldown=0,
                           TARGET=[('AFTER', 'OBJECT_ACTION')])
        # Note: policy binding is created but not stored
        pb = self._create_cp_binding(cluster_id, policy.id)
        self.assertIsNone(pb.last_op)
        mock_load_all.return_value = [pb]
        mock_load.return_value = policy
        entity = mock.Mock()
        action = ab.Action(cluster_id, 'OBJECT_ACTION', self.ctx)
        action.entity = entity

        res = action.policy_check(CLUSTER_ID, 'AFTER')

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

    @mock.patch.object(cpo.ClusterPolicy, 'cooldown_inprogress')
    @mock.patch.object(cpo.ClusterPolicy, 'get_all')
    @mock.patch.object(policy_mod.Policy, 'load')
    def test_policy_check_cooldown_inprogress(self, mock_load, mock_load_all,
                                              mock_inprogress):
        cluster_id = CLUSTER_ID
        # Note: policy is mocked
        policy_id = uuidutils.generate_uuid()
        policy = mock.Mock(id=policy_id, TARGET=[('AFTER', 'OBJECT_ACTION')])
        # Note: policy binding is created but not stored
        pb = self._create_cp_binding(cluster_id, policy.id)
        mock_inprogress.return_value = True
        mock_load_all.return_value = [pb]
        mock_load.return_value = policy
        action = ab.Action(cluster_id, 'OBJECT_ACTION', self.ctx)

        # Do it
        res = action.policy_check(CLUSTER_ID, 'AFTER')

        self.assertIsNone(res)
        self.assertEqual(policy_mod.CHECK_ERROR, action.data['status'])
        self.assertEqual(
            'Policy %s cooldown is still in progress.' % policy_id,
            six.text_type(action.data['reason']))
        mock_load_all.assert_called_once_with(
            action.context, cluster_id, sort='priority',
            filters={'enabled': True})
        mock_load.assert_called_once_with(action.context, policy.id)
        # last_op was updated for POST check
        self.assertIsNotNone(pb.last_op)
        # neither pre_op nor post_op was not called, due to cooldown
        self.assertEqual(0, policy.pre_op.call_count)
        self.assertEqual(0, policy.post_op.call_count)

    @mock.patch.object(cpo.ClusterPolicy, 'get_all')
    @mock.patch.object(policy_mod.Policy, 'load')
    @mock.patch.object(ab.Action, '_check_result')
    def test_policy_check_abort_in_middle(self, mock_check, mock_load,
                                          mock_load_all):
        cluster_id = CLUSTER_ID
        # Note: both policies are mocked
        policy1 = mock.Mock(id=uuidutils.generate_uuid(), cooldown=0,
                            TARGET=[('AFTER', 'OBJECT_ACTION')])
        policy1.name = 'P1'
        policy2 = mock.Mock(id=uuidutils.generate_uuid(), cooldown=0,
                            TARGET=[('AFTER', 'OBJECT_ACTION')])
        policy2.name = 'P2'
        action = ab.Action(cluster_id, 'OBJECT_ACTION', self.ctx)

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
    @mock.patch.object(ab.Action, 'load')
    @mock.patch.object(ao.Action, 'mark_succeeded')
    def test_action_proc_successful(self, mock_mark, mock_load,
                                    mock_event_info):
        action = ab.Action(OBJID, 'OBJECT_ACTION', self.ctx)
        mock_obj = mock.Mock()
        action.entity = mock_obj
        self.patchobject(action, 'execute',
                         return_value=(action.RES_OK, 'BIG SUCCESS'))
        mock_status = self.patchobject(action, 'set_status')
        mock_load.return_value = action

        res = ab.ActionProc(self.ctx, 'ACTION_ID')

        self.assertTrue(res)
        mock_load.assert_called_once_with(self.ctx, action_id='ACTION_ID',
                                          project_safe=False)
        mock_event_info.assert_called_once_with(action, 'start', 'ACTION_I')
        mock_status.assert_called_once_with(action.RES_OK, 'BIG SUCCESS')

    @mock.patch.object(EVENT, 'info')
    @mock.patch.object(ab.Action, 'load')
    @mock.patch.object(ao.Action, 'mark_failed')
    def test_action_proc_failed_error(self, mock_mark, mock_load, mock_info):
        action = ab.Action(OBJID, 'CLUSTER_ACTION', self.ctx, id=ACTION_ID)
        action.entity = mock.Mock(id=CLUSTER_ID, name='fake-cluster')

        self.patchobject(action, 'execute', side_effect=Exception('Boom!'))
        mock_status = self.patchobject(action, 'set_status')
        mock_load.return_value = action

        res = ab.ActionProc(self.ctx, 'ACTION')

        self.assertFalse(res)
        mock_load.assert_called_once_with(self.ctx, action_id='ACTION',
                                          project_safe=False)
        mock_info.assert_called_once_with(action, 'start', 'ACTION')
        mock_status.assert_called_once_with(action.RES_ERROR, 'Boom!')
