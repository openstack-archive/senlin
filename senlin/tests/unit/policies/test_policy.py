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
from oslo_context import context as oslo_ctx
from oslo_utils import timeutils
import six

from senlin.common import consts
from senlin.common import context as senlin_ctx
from senlin.common import exception
from senlin.common import schema
from senlin.common import utils as common_utils
from senlin.engine import environment
from senlin.engine import parser
from senlin.objects import credential as co
from senlin.objects import policy as po
from senlin.policies import base as pb
from senlin.tests.unit.common import base
from senlin.tests.unit.common import utils

UUID1 = 'aa5f86b8-e52b-4f2b-828a-4c14c770938d'
UUID2 = '2c5139a6-24ba-4a6f-bd53-a268f61536de'

sample_policy = """
  type: senlin.policy.dummy
  version: 1.0
  properties:
    key1: value1
    key2: 2
"""


class DummyPolicy(pb.Policy):
    VERSION = '1.0'

    properties_schema = {
        'key1': schema.String(
            'first key',
            default='value1'
        ),
        'key2': schema.Integer(
            'second key',
            required=True,
        ),
    }

    def __init__(self, name, spec, **kwargs):
        super(DummyPolicy, self).__init__(name, spec, **kwargs)


class TestPolicyBase(base.SenlinTestCase):

    def setUp(self):
        super(TestPolicyBase, self).setUp()
        self.ctx = utils.dummy_context()
        environment.global_env().register_policy('senlin.policy.dummy-1.0',
                                                 DummyPolicy)
        self.spec = parser.simple_parse(sample_policy)

    def _create_policy(self, policy_name, policy_id=None):
        policy = pb.Policy(policy_name, self.spec,
                           user=self.ctx.user_id,
                           project=self.ctx.project_id,
                           domain=self.ctx.domain_id)
        if policy_id:
            policy.id = policy_id

        return policy

    def _create_db_policy(self, **kwargs):
        values = {
            'name': 'test-policy',
            'type': 'senlin.policy.dummy-1.0',
            'spec': self.spec,
            'created_at': timeutils.utcnow(True),
            'user': self.ctx.user_id,
            'project': self.ctx.project_id,
            'domain': self.ctx.domain_id,
        }

        values.update(kwargs)
        return po.Policy.create(self.ctx, values)

    def test_init(self):
        policy = self._create_policy('test-policy')

        self.assertIsNone(policy.id)
        self.assertEqual('test-policy', policy.name)
        self.assertEqual(self.spec, policy.spec)
        self.assertEqual('senlin.policy.dummy-1.0', policy.type)
        self.assertEqual(self.ctx.user_id, policy.user)
        self.assertEqual(self.ctx.project_id, policy.project)
        self.assertEqual(self.ctx.domain_id, policy.domain)
        self.assertEqual({}, policy.data)
        self.assertIsNone(policy.created_at)
        self.assertIsNone(policy.updated_at)
        self.assertTrue(policy.singleton)

        spec_data = policy.spec_data
        self.assertEqual('senlin.policy.dummy', spec_data['type'])
        self.assertEqual('1.0', spec_data['version'])
        self.assertEqual({'key1': 'value1', 'key2': 2},
                         spec_data['properties'])
        self.assertEqual({'key1': 'value1', 'key2': 2}, policy.properties)

    def test_policy_new_type_not_found(self):
        bad_spec = {
            'type': 'bad-type',
            'version': '1.0',
            'properties': '',
        }

        self.assertRaises(exception.ResourceNotFound,
                          pb.Policy,
                          'test-policy', bad_spec)

    def test_load(self):
        policy = utils.create_policy(self.ctx, UUID1)
        result = pb.Policy.load(self.ctx, policy.id)

        self.assertEqual(policy.id, result.id)
        self.assertEqual(policy.name, result.name)
        self.assertEqual(policy.type, result.type)
        self.assertEqual(policy.user, result.user)
        self.assertEqual(policy.project, result.project)
        self.assertEqual(policy.domain, result.domain)
        self.assertEqual(policy.spec, result.spec)
        self.assertEqual(policy.data, result.data)
        self.assertEqual({'key1': 'value1', 'key2': 2}, result.properties)

        self.assertEqual(policy.created_at, result.created_at)
        self.assertEqual(policy.updated_at, result.updated_at)

    def test_load_with_policy(self):
        policy = utils.create_policy(self.ctx, UUID1)
        expected = pb.Policy.load(self.ctx, policy.id)

        res = pb.Policy.load(self.ctx, db_policy=policy)

        self.assertIsNotNone(res)
        self.assertEqual(expected.id, res.id)

    def test_load_diff_project(self):
        policy = utils.create_policy(self.ctx, UUID1)

        new_ctx = utils.dummy_context(project='a-different-project')
        self.assertRaises(exception.ResourceNotFound,
                          pb.Policy.load,
                          new_ctx, policy.id, None)

        res = pb.Policy.load(new_ctx, policy.id, project_safe=False)
        self.assertIsNotNone(res)
        self.assertEqual(policy.id, res.id)

    def test_load_not_found(self):
        ex = self.assertRaises(exception.ResourceNotFound,
                               pb.Policy.load,
                               self.ctx, 'fake-policy', None)
        self.assertEqual("The policy 'fake-policy' could not be found.",
                         six.text_type(ex))

        ex = self.assertRaises(exception.ResourceNotFound,
                               pb.Policy.load,
                               self.ctx, None, None)
        self.assertEqual("The policy 'None' could not be found.",
                         six.text_type(ex))

    def test_delete(self):
        policy = utils.create_policy(self.ctx, UUID1)
        policy_id = policy.id

        res = pb.Policy.delete(self.ctx, policy_id)
        self.assertIsNone(res)
        self.assertRaises(exception.ResourceNotFound,
                          pb.Policy.load,
                          self.ctx, policy_id, None)

    def test_delete_not_found(self):
        result = pb.Policy.delete(self.ctx, 'bogus')
        self.assertIsNone(result)

    def test_store_for_create(self):
        policy = self._create_policy('test-policy')
        self.assertIsNone(policy.id)

        policy_id = policy.store(self.ctx)
        self.assertIsNotNone(policy_id)
        self.assertEqual(policy_id, policy.id)

        result = po.Policy.get(self.ctx, policy_id)

        self.assertIsNotNone(result)
        self.assertEqual('test-policy', result.name)
        self.assertEqual(policy_id, result.id)
        self.assertEqual(policy.type, result.type)
        self.assertEqual(policy.user, result.user)
        self.assertEqual(policy.project, result.project)
        self.assertEqual(policy.domain, result.domain)
        self.assertEqual(policy.spec, result.spec)
        self.assertEqual(policy.data, result.data)

        self.assertIsNotNone(result.created_at)
        self.assertIsNone(result.updated_at)

    def test_store_for_update(self):
        policy = self._create_policy('test-policy')
        self.assertIsNone(policy.id)
        policy_id = policy.store(self.ctx)
        self.assertIsNotNone(policy_id)
        self.assertEqual(policy_id, policy.id)

        # do an update
        policy.name = 'test-policy-1'
        policy.data = {'kk': 'vv'}

        new_id = policy.store(self.ctx)
        self.assertEqual(policy_id, new_id)

        result = po.Policy.get(self.ctx, policy_id)
        self.assertIsNotNone(result)
        self.assertEqual('test-policy-1', result.name)
        self.assertEqual({'kk': 'vv'}, policy.data)
        self.assertIsNotNone(policy.created_at)
        self.assertIsNotNone(policy.updated_at)

    def test_to_dict(self):
        policy = self._create_policy('test-policy')
        policy_id = policy.store(self.ctx)
        self.assertIsNotNone(policy_id)
        expected = {
            'id': policy_id,
            'name': policy.name,
            'type': policy.type,
            'user': policy.user,
            'project': policy.project,
            'domain': policy.domain,
            'spec': policy.spec,
            'data': policy.data,
            'created_at': common_utils.isotime(policy.created_at),
            'updated_at': None,
        }

        result = pb.Policy.load(self.ctx, policy_id=policy.id)
        self.assertEqual(expected, result.to_dict())

    def test_get_schema(self):
        expected = {
            'key1': {
                'default': 'value1',
                'description': 'first key',
                'required': False,
                'updatable': False,
                'type': 'String'
            },
            'key2': {
                'description': 'second key',
                'required': True,
                'updatable': False,
                'type': 'Integer'
            },
        }
        res = DummyPolicy.get_schema()
        self.assertEqual(expected, res)

    def test_build_policy_data(self):
        policy = self._create_policy('test-policy')
        data = {'key1': 'value1'}
        res = policy._build_policy_data(data)
        expect_result = {
            'DummyPolicy': {
                'version': '1.0',
                'data': data
            }
        }
        self.assertEqual(expect_result, res)

    def test_extract_policy_data(self):
        policy = self._create_policy('test-policy')
        # Extract data correctly
        data = {'key1': 'value1'}
        policy_data = {
            'DummyPolicy': {
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

        # Policy version don't match
        data = {'key1': 'value1'}
        policy_data = {
            'DummyPolicy': {
                'version': '2.0',
                'data': data
            }
        }
        res = policy._extract_policy_data(policy_data)
        self.assertIsNone(res)

    @mock.patch.object(pb.Policy, '_build_conn_params')
    @mock.patch('senlin.drivers.base.SenlinDriver')
    def test_keystone(self, mock_sd, mock_params):
        policy = self._create_policy('test-policy')
        fake_params = mock.Mock()
        mock_params.return_value = fake_params
        kc = mock.Mock()
        driver = mock.Mock()
        driver.identity.return_value = kc
        mock_sd.return_value = driver

        res = policy.keystone('user1', 'project1')

        self.assertEqual(kc, res)
        self.assertEqual(kc, policy._keystoneclient)
        mock_params.assert_called_once_with('user1', 'project1')
        mock_sd.assert_called_once_with()
        driver.identity.assert_called_once_with(fake_params)

    def test_keystone_already_initialized(self):
        policy = self._create_policy('test-policy')
        x_keystone = mock.Mock()
        policy._keystoneclient = x_keystone

        result = policy.keystone('foo', 'bar')

        self.assertEqual(x_keystone, result)

    @mock.patch.object(pb.Policy, '_build_conn_params')
    @mock.patch("senlin.drivers.base.SenlinDriver")
    def test_nova(self, mock_driver, mock_params):
        policy = self._create_policy('test-policy')
        fake_params = mock.Mock()
        mock_params.return_value = fake_params
        x_driver = mock.Mock()
        mock_driver.return_value = x_driver

        result = policy.nova('user1', 'project1')

        x_nova = x_driver.compute.return_value
        self.assertEqual(x_nova, result)
        self.assertEqual(x_nova, policy._novaclient)
        mock_params.assert_called_once_with('user1', 'project1')
        x_driver.compute.assert_called_once_with(fake_params)

    def test_nova_already_initialized(self):
        policy = self._create_policy('test-policy')
        x_nova = mock.Mock()
        policy._novaclient = x_nova

        result = policy.nova('foo', 'bar')

        self.assertEqual(x_nova, result)

    @mock.patch.object(pb.Policy, '_build_conn_params')
    @mock.patch("senlin.drivers.base.SenlinDriver")
    def test_network(self, mock_driver, mock_params):
        policy = self._create_policy('test-policy')
        fake_params = mock.Mock()
        mock_params.return_value = fake_params
        x_driver = mock.Mock()
        mock_driver.return_value = x_driver

        result = policy.network('user1', 'project1')

        x_network = x_driver.network.return_value
        self.assertEqual(x_network, result)
        self.assertEqual(x_network, policy._networkclient)
        mock_params.assert_called_once_with('user1', 'project1')
        x_driver.network.assert_called_once_with(fake_params)

    def test_network_already_initialized(self):
        policy = self._create_policy('test-policy')
        x_network = mock.Mock()
        policy._networkclient = x_network

        result = policy.network('foo', 'bar')

        self.assertEqual(x_network, result)

    @mock.patch.object(pb.Policy, '_build_conn_params')
    @mock.patch("senlin.drivers.base.SenlinDriver")
    def test_lbaas(self, mock_driver, mock_params):
        policy = self._create_policy('test-policy')
        fake_params = mock.Mock()
        mock_params.return_value = fake_params
        x_driver = mock.Mock()
        mock_driver.return_value = x_driver

        result = policy.lbaas('user1', 'project1')

        x_lbaas = x_driver.loadbalancing.return_value
        self.assertEqual(x_lbaas, result)
        self.assertEqual(x_lbaas, policy._lbaasclient)
        mock_params.assert_called_once_with('user1', 'project1')
        x_driver.loadbalancing.assert_called_once_with(fake_params)

    def test_lbaas_already_initialized(self):
        policy = self._create_policy('test-policy')
        x_lbaas = mock.Mock()
        policy._lbaasclient = x_lbaas

        result = policy.lbaas('foo', 'bar')

        self.assertEqual(x_lbaas, result)

    def test_default_need_check(self):
        action = mock.Mock()
        action.action = consts.CLUSTER_SCALE_IN
        action.data = {}

        policy = self._create_policy('test-policy')
        res = policy.need_check('BEFORE', action)
        self.assertTrue(res)

        setattr(policy, 'TARGET', [('BEFORE', consts.CLUSTER_SCALE_IN)])
        res = policy.need_check('BEFORE', action)
        self.assertTrue(res)
        res = policy.need_check('AFTER', action)
        self.assertFalse(res)

    def test_default_pre_op(self):
        policy = self._create_policy('test-policy')
        res = policy.pre_op('CLUSTER_ID', 'FOO')
        self.assertIsNone(res)

    def test_default_post_op(self):
        policy = self._create_policy('test-policy')
        res = policy.post_op('CLUSTER_ID', 'FOO')
        self.assertIsNone(res)

    def test_default_attach(self):
        cluster = mock.Mock()
        policy = self._create_policy('test-policy')

        # Policy targets on ANY profile types
        policy.PROFILE_TYPE = ['ANY']
        res = policy.attach(cluster)
        self.assertEqual((True, None), res)

        # Profile type of cluster is not in policy's target scope
        profile = mock.Mock()
        profile.type = 'os.nova.server'
        cluster.rt = {'profile': profile}
        policy.PROFILE_TYPE = ['os.heat.resource']
        msg = 'Policy not applicable on profile type: os.nova.server'
        res = policy.attach(cluster)
        self.assertEqual((False, msg), res)

        # Attaching succeed
        policy.PROFILE_TYPE = ['os.nova.server', 'os.heat.resource']
        res = policy.attach(cluster)
        self.assertEqual((True, None), res)

    def test_default_detach(self):
        cluster = mock.Mock()
        policy = self._create_policy('test-policy')

        res = policy.detach(cluster)
        self.assertEqual((True, None), res)

    @mock.patch.object(co.Credential, 'get')
    @mock.patch.object(senlin_ctx, 'get_service_credentials')
    @mock.patch.object(oslo_ctx, 'get_current')
    def test_build_conn_params(self, mock_get_current, mock_get_service_creds,
                               mock_cred_get):
        service_cred = {
            'auth_url': 'AUTH_URL',
            'username': 'senlin',
            'user_domain_name': 'default',
            'password': '123'
        }
        current_ctx = {
            'auth_url': 'auth_url',
            'user_name': 'user1',
            'user_domain_name': 'default',
            'password': '456'
        }
        cred_info = {
            'openstack': {
                'trust': 'TRUST_ID',
            }
        }

        cred = mock.Mock(cred=cred_info)
        mock_get_service_creds.return_value = service_cred
        mock_get_current.return_value = current_ctx
        mock_cred_get.return_value = cred
        policy = self._create_policy('test-policy')

        res = policy._build_conn_params('user1', 'project1')

        expected_result = {
            'auth_url': 'AUTH_URL',
            'username': 'senlin',
            'user_domain_name': 'default',
            'password': '123',
            'trust_id': 'TRUST_ID'
        }
        self.assertEqual(expected_result, res)
        mock_get_service_creds.assert_called_once_with()
        mock_cred_get.assert_called_once_with(current_ctx, 'user1', 'project1')

    @mock.patch.object(co.Credential, 'get')
    @mock.patch.object(senlin_ctx, 'get_service_credentials')
    @mock.patch.object(oslo_ctx, 'get_current')
    def test_build_conn_params_trust_not_found(
            self, mock_get_current, mock_get_service_creds, mock_cred_get):

        service_cred = {
            'auth_url': 'AUTH_URL',
            'username': 'senlin',
            'user_domain_name': 'default',
            'password': '123'
        }

        mock_get_service_creds.return_value = service_cred
        mock_cred_get.return_value = None
        policy = self._create_policy('test-policy')

        ex = self.assertRaises(exception.TrustNotFound,
                               policy._build_conn_params,
                               'user1', 'project1')

        msg = "The trust for trustor 'user1' could not be found."
        self.assertEqual(msg, six.text_type(ex))
