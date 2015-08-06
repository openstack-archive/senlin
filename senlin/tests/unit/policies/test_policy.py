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
from senlin.common import schema
from senlin.db.sqlalchemy import api as db_api
from senlin.engine import environment
from senlin.policies import base as policy_base
from senlin.policies import deletion_policy
from senlin.tests.unit.common import base
from senlin.tests.unit.common import utils


class DummyPolicy(policy_base.Policy):
    spec_schema = {}


class TestPolicy(base.SenlinTestCase):

    def setUp(self):
        super(TestPolicy, self).setUp()
        self.context = utils.dummy_context()
        self.spec_schema = {
            'key1': schema.String('first key', default='value1'),
            'key2': schema.Integer('second key', required=True),
        }
        self.spec = {'key1': 'value1', 'key2': 2}
        self.spec_data = schema.Spec(self.spec_schema, self.spec)
        self.spec_data_deletion_policy = schema.Spec(
            deletion_policy.DeletionPolicy.spec_schema, {})

    def _create_policy(self, policy_name, policy_id=None):
        values = {
            'user': 'test-user',
            'project': 'test-project',
            'domain': 'test-domain',
            'name': policy_name,
            'type': 'DeletionPolicy',
            'level': 0,
            'cooldown': None,
            'spec': self.spec,
            'data': {},
        }
        if policy_id:
            values['id'] = policy_id

        return db_api.policy_create(self.context, values)

    @mock.patch.object(schema, 'Spec')
    def test_policy_new(self, mock_schema_spec):
        policy = policy_base.Policy('DeletionPolicy', 'test-policy')
        self.assertIsNone(policy.id)
        self.assertEqual('test-policy', policy.name)

    def test_policy_new_type_not_found(self):
        self.assertRaises(exception.PolicyTypeNotFound,
                          policy_base.Policy,
                          'fake-policy-type', 'test-policy')

    @mock.patch.object(schema, 'Spec')
    def test_policy_init(self, mock_schema_spec):
        kwargs = {
            'user': 'test-user',
            'project': 'test-project',
            'domain': 'test-domain',
            'type': 'DeletionPolicy',
            'level': 0,
            'cooldown': 10,
            'spec': self.spec,
            'data': {},
        }
        mock_schema_spec.return_value = self.spec_data_deletion_policy
        policy = policy_base.Policy('DeletionPolicy', 'test-policy', **kwargs)

        self.assertIsNone(policy.id)
        self.assertEqual(kwargs['user'], policy.user)
        self.assertEqual(kwargs['project'], policy.project)
        self.assertEqual(kwargs['domain'], policy.domain)
        self.assertEqual('test-policy', policy.name)
        self.assertEqual(kwargs['type'], policy.type)
        self.assertEqual(kwargs['level'], policy.level)
        self.assertEqual(kwargs['cooldown'], policy.cooldown)
        self.assertEqual(kwargs['spec'], policy.spec)
        self.assertEqual(kwargs['data'], policy.data)
        self.assertEqual(self.spec_data_deletion_policy, policy.spec_data)

        self.assertIsNone(policy.created_time)
        self.assertIsNone(policy.updated_time)
        self.assertIsNone(policy.deleted_time)

    @mock.patch.object(schema, 'Spec')
    def test_policy_init_default_value(self, mock_schema_spec):
        mock_schema_spec.return_value = self.spec_data_deletion_policy
        policy = policy_base.Policy('DeletionPolicy', 'test-policy')

        self.assertIsNone(policy.id)
        self.assertEqual(None, policy.user)
        self.assertEqual(None, policy.project)
        self.assertEqual(None, policy.domain)
        self.assertEqual('test-policy', policy.name)
        self.assertEqual('DeletionPolicy', policy.type)
        self.assertEqual(0, policy.level)
        self.assertEqual(None, policy.cooldown)
        self.assertEqual({}, policy.spec)
        self.assertEqual({}, policy.data)
        self.assertEqual(self.spec_data_deletion_policy, policy.spec_data)

        self.assertIsNone(policy.created_time)
        self.assertIsNone(policy.updated_time)
        self.assertIsNone(policy.deleted_time)

    @mock.patch.object(schema, 'Spec')
    def test_policy_load(self, mock_schema_spec):
        mock_schema_spec.return_value = self.spec_data_deletion_policy

        ex = self.assertRaises(exception.PolicyNotFound,
                               policy_base.Policy.load,
                               self.context, 'fake-policy', None)
        self.assertEqual('The policy (fake-policy) could not be found.',
                         six.text_type(ex))

        policy = self._create_policy('policy-1')
        result = policy_base.Policy.load(self.context, policy.id)

        self.assertEqual(policy.id, result.id)
        self.assertEqual(policy.name, result.name)
        self.assertEqual(policy.type, result.type)
        self.assertEqual(policy.user, result.user)
        self.assertEqual(policy.project, result.project)
        self.assertEqual(policy.domain, result.domain)
        self.assertEqual(policy.level, result.level)
        self.assertEqual(policy.cooldown, result.cooldown)
        self.assertEqual(policy.spec, result.spec)
        self.assertEqual(policy.data, result.data)
        self.assertEqual(self.spec_data_deletion_policy, result.spec_data)

        self.assertEqual(policy.created_time, result.created_time)
        self.assertEqual(policy.updated_time, result.updated_time)
        self.assertEqual(policy.deleted_time, result.deleted_time)

    @mock.patch.object(schema, 'Spec')
    def test_policy_load_all(self, mock_schema_spec):
        result = policy_base.Policy.load_all(self.context)
        self.assertEqual([], [p for p in result])

        policy1 = self._create_policy('policy-1', 'ID1')
        policy2 = self._create_policy('policy-2', 'ID2')

        result = policy_base.Policy.load_all(self.context)
        policies = [p for p in result]
        self.assertEqual(2, len(policies))
        self.assertEqual(policy1.id, policies[0].id)
        self.assertEqual(policy2.id, policies[1].id)

    def test_policy_store_init(self):
        kwargs = {
            'user': 'test-user',
            'project': 'test-project',
            'domain': 'test-domain'
        }
        policy = policy_base.Policy('DeletionPolicy', 'test-policy', **kwargs)
        self.assertIsNone(policy.id)
        policy_id = policy.store(self.context)
        self.assertIsNotNone(policy_id)
        self.assertEqual(policy_id, policy.id)

        result = db_api.policy_get(self.context, policy_id)

        self.assertIsNotNone(result)
        self.assertEqual('test-policy', result.name)
        self.assertEqual(policy_id, result.id)
        self.assertEqual(policy.type, result.type)
        self.assertEqual(policy.user, result.user)
        self.assertEqual(policy.project, result.project)
        self.assertEqual(policy.domain, result.domain)
        self.assertEqual(policy.level, result.level)
        self.assertEqual(policy.cooldown, result.cooldown)
        self.assertEqual(policy.spec, result.spec)
        self.assertEqual(policy.data, result.data)

        self.assertIsNotNone(result.created_time)
        self.assertIsNone(result.updated_time)
        self.assertIsNone(result.deleted_time)

    def test_policy_store_update(self):
        kwargs = {
            'user': 'test-user',
            'project': 'test-project',
            'domain': 'test-domain'
        }
        policy = policy_base.Policy('DeletionPolicy', 'test-policy', **kwargs)
        self.assertIsNone(policy.id)
        policy_id = policy.store(self.context)
        self.assertIsNotNone(policy_id)
        self.assertEqual(policy_id, policy.id)

        # do an update
        policy.name = 'test-policy-1'
        policy.type = 'PlacementPolicy'
        policy.spec = {'key1': 'value1'}
        policy.level = 10
        policy.cooldown = 60
        policy.data = {'key2': 'value2'}

        new_id = policy.store(self.context)
        self.assertEqual(policy_id, new_id)

        result = db_api.policy_get(self.context, policy_id)
        self.assertIsNotNone(result)
        self.assertEqual('test-policy-1', result.name)
        self.assertEqual('PlacementPolicy', result.type)
        self.assertEqual(10, result.level)
        self.assertEqual(60, result.cooldown)
        self.assertEqual({'key1': 'value1'}, result.spec)
        self.assertEqual({'key2': 'value2'}, result.data)

    @mock.patch.object(schema, 'Spec')
    def test_policy_to_dict(self, mock_schema_spec):
        policy = self._create_policy('test-policy')
        self.assertIsNotNone(policy.id)
        expected = {
            'id': policy.id,
            'name': policy.name,
            'type': policy.type,
            'user': policy.user,
            'project': policy.project,
            'domain': policy.domain,
            'spec': policy.spec,
            'level': policy.level,
            'cooldown': policy.cooldown,
            'data': policy.data,
            'created_time': policy.created_time,
            'updated_time': policy.updated_time,
            'deleted_time': policy.deleted_time,
        }

        result = policy_base.Policy.load(self.context, policy_id=policy.id)
        self.assertEqual(expected, result.to_dict())

    @mock.patch.object(schema, 'Spec')
    def test_policy_from_dict(self, mock_schema_spec):
        params = {
            'user': 'test-user',
            'project': 'test-project',
            'domain': 'test-domain',
            'name': 'test-policy',
            'type': 'DeletionPolicy',
            'level': 10,
            'cooldown': 60,
            'spec': self.spec,
            'data': {},
        }

        policy = policy_base.Policy.from_dict(**params)
        self.assertEqual(params['name'], policy.name)
        self.assertEqual(params['type'], policy.type)
        self.assertEqual(params['user'], policy.user)
        self.assertEqual(params['project'], policy.project)
        self.assertEqual(params['domain'], policy.domain)
        self.assertEqual(params['level'], policy.level)
        self.assertEqual(params['cooldown'], policy.cooldown)
        self.assertEqual(params['spec'], policy.spec)
        self.assertEqual(params['data'], policy.data)

    @mock.patch.object(schema, 'Spec')
    def test_policy_delete(self, mock_schema_spec):
        policy = self._create_policy('test-policy')
        policy_id = policy.id
        result = policy_base.Policy.load(self.context, policy_id)
        self.assertIsNotNone(result)
        self.assertEqual(policy_id, result.id)

        policy_base.Policy.delete(self.context, policy_id)
        self.assertRaises(exception.PolicyNotFound, policy_base.Policy.load,
                          self.context, policy_id, None)

    def test_policy_delete_not_found(self):
        result = policy_base.Policy.delete(self.context, 'fake-policy-id')
        self.assertEqual(None, result)

    def test_policy_build_policy_data(self):
        kwargs = {
            'user': 'test-user',
            'project': 'test-project',
            'domain': 'test-domain'
        }
        policy = policy_base.Policy('DeletionPolicy', 'test-policy', **kwargs)

        data = {'key1': 'value1'}
        res = policy._build_policy_data(data)
        expect_result = {
            'DeletionPolicy': {
                'version': '1.0',
                'data': data
            }
        }
        self.assertEqual(expect_result, res)

    def test_policy_extract_policy_data(self):
        kwargs = {
            'user': 'test-user',
            'project': 'test-project',
            'domain': 'test-domain'
        }
        policy = policy_base.Policy('DeletionPolicy', 'test-policy', **kwargs)

        # Extract data correctly
        data = {'key1': 'value1'}
        policy_data = {
            'DeletionPolicy': {
                'version': '1.0',
                'data': data
            }
        }
        res = policy._extract_policy_data(policy_data)
        self.assertEqual(data, res)

        # Policy class name unmatch
        data = {'key1': 'value1'}
        policy_data = {
            'FakePolicy': {
                'version': '1.0',
                'data': data
            }
        }
        res = policy._extract_policy_data(policy_data)
        self.assertIsNone(res)

        # Policy version unmatch
        data = {'key1': 'value1'}
        policy_data = {
            'DeletionPolicy': {
                'version': '2.0',
                'data': data
            }
        }
        res = policy._extract_policy_data(policy_data)
        self.assertIsNone(res)

    def test_policy_default_pre_op(self):
        environment.global_env().register_policy('DummyPolicy', DummyPolicy)
        policy = policy_base.Policy('DummyPolicy', 'test-policy')
        res = policy.pre_op('CLUSTER_ID', 'FOO')
        self.assertIsNone(res)

    def test_policy_default_post_op(self):
        environment.global_env().register_policy('DummyPolicy', DummyPolicy)
        policy = policy_base.Policy('DummyPolicy', 'test-policy')
        res = policy.post_op('CLUSTER_ID', 'FOO')
        self.assertIsNone(res)

    def test_policy_attach(self):
        cluster = mock.Mock()
        kwargs = {
            'user': 'test-user',
            'project': 'test-project',
            'domain': 'test-domain'
        }
        policy = policy_base.Policy('DeletionPolicy', 'test-policy', **kwargs)

        # Policy targets on ANY profile types
        policy.PROFILE_TYPE = ['ANY']
        res, data = policy.attach(cluster)
        self.assertTrue(res)
        self.assertIsNone(data)

        # Profile type of cluster is not in policy's target scope
        profile = mock.Mock()
        profile.type = 'os.nova.server'
        cluster.rt = {'profile': profile}
        policy.PROFILE_TYPE = ['os.heat.resource']
        msg = _('Policy not applicable on profile type:%s') % 'os.nova.server'
        res, data = policy.attach(cluster)
        self.assertFalse(res)
        self.assertEqual(msg, data)

        # Attaching succeed
        policy.PROFILE_TYPE = ['os.nova.server', 'os.heat.resource']
        res, data = policy.attach(cluster)
        self.assertTrue(res)
        self.assertIsNone(data)

    def test_policy_detach(self):
        cluster = mock.Mock()
        kwargs = {
            'user': 'test-user',
            'project': 'test-project',
            'domain': 'test-domain'
        }
        policy = policy_base.Policy('DeletionPolicy', 'test-policy', **kwargs)

        res, data = policy.detach(cluster)
        self.assertTrue(res)
        self.assertIsNone(data)
