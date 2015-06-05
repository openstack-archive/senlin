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

import glob
import mock
import six

from senlin.common import exception
from senlin.engine import environment
from senlin.tests.common import base

fake_env_str = """
parameters:
  pa: va
  pb: vb
custom_profiles:
  prof_1: plugin_1
custom_policies:
  policy_2: plugin_2
"""


class TestEnvironment(base.SenlinTestCase):

    def setUp(self):
        super(TestEnvironment, self).setUp()

    def test_create_global(self):
        e = environment.Environment(is_global=True)

        self.assertEqual({}, e.params)
        self.assertEqual('profiles', e.profile_registry.registry_name)
        self.assertEqual('policies', e.policy_registry.registry_name)
        self.assertTrue(e.profile_registry.is_global)
        self.assertTrue(e.policy_registry.is_global)

    def test_create_default(self):
        ge = environment.global_env()
        e = environment.Environment()

        reg_prof = e.profile_registry
        reg_plcy = e.policy_registry

        self.assertEqual({}, e.params)
        self.assertEqual('profiles', reg_prof.registry_name)
        self.assertEqual('policies', reg_plcy.registry_name)
        self.assertFalse(reg_prof.is_global)
        self.assertFalse(reg_plcy.is_global)
        self.assertEqual('profiles', ge.profile_registry.registry_name)
        self.assertEqual('policies', ge.policy_registry.registry_name)
        self.assertEqual(ge.profile_registry, reg_prof.global_registry)
        self.assertEqual(ge.policy_registry, reg_plcy.global_registry)

    def test_create_with_env(self):
        env = {
            'parameters': {
                'p1': 'v1',
                'p2': True,
            },
            'custom_profiles': {
                'PROFILE_FOO': 'some.class',
                'PROFILE_BAR': 'other.class',
            },
            'custom_policies': {
                'POLICY_Alpha': 'package.alpha',
                'POLICY_Beta': 'package.beta',
            }
        }

        e = environment.Environment(env=env, is_global=True)

        self.assertEqual('v1', e.params['p1'])
        self.assertEqual(True, e.params['p2'])
        self.assertEqual('some.class', e.get_profile('PROFILE_FOO'))
        self.assertEqual('other.class', e.get_profile('PROFILE_BAR'))
        self.assertEqual('package.alpha', e.get_policy('POLICY_Alpha'))
        self.assertEqual('package.beta', e.get_policy('POLICY_Beta'))

    def test_parse(self):
        env = environment.Environment()
        result = env.parse(fake_env_str)

        self.assertEqual('va', result['parameters']['pa'])
        self.assertEqual('vb', result['parameters']['pb'])
        self.assertEqual('plugin_1', result['custom_profiles']['prof_1'])
        self.assertEqual('plugin_2', result['custom_policies']['policy_2'])

        # unknown sections
        env_str = "variables:\n  p1: v1"
        err = self.assertRaises(ValueError, env.parse, env_str)
        self.assertEqual('environment has unknown section "variables"',
                         six.text_type(err))

        # omitted sections
        env_str = "parameters:\n  p1: v1"
        result = env.parse(env_str)
        self.assertEqual('v1', result['parameters']['p1'])
        self.assertEqual({}, result['custom_profiles'])
        self.assertEqual({}, result['custom_policies'])

    def test_load(self):
        env = environment.Environment()
        env.load({})
        self.assertEqual({}, env.params)
        self.assertEqual({}, env.profile_registry._registry)
        self.assertEqual({}, env.policy_registry._registry)

        env_dict = {
            'parameters': {
                'P': 'V'
            },
            'custom_profiles': {
                'C1': 'class1',
            },
            'custom_policies': {
                'C2': 'class2',
            }
        }
        env.load(env_dict)
        self.assertEqual('V', env.params['P'])
        self.assertEqual('class1', env.get_profile('C1'))
        self.assertEqual('class2', env.get_policy('C2'))

    def test_check_profile_type_name(self):
        env = environment.Environment()
        env._check_profile_type_name('abc')

        ex = self.assertRaises(exception.ProfileValidationFailed,
                               env._check_profile_type_name, '')
        self.assertEqual('Profile type name not specified', six.text_type(ex))
        ex = self.assertRaises(exception.ProfileValidationFailed,
                               env._check_profile_type_name, None)
        self.assertEqual('Profile type name not specified', six.text_type(ex))

        for v in [123, {}, ['a'], ('b', 'c'), True]:
            ex = self.assertRaises(exception.ProfileValidationFailed,
                                   env._check_profile_type_name, v)
            self.assertEqual('Profile type name is not a string',
                             six.text_type(ex))

    def test_register_and_get_profile(self):
        plugin = mock.Mock()
        env = environment.Environment()

        ex = self.assertRaises(exception.ProfileTypeNotFound,
                               env.get_profile, 'foo')
        self.assertEqual('Profile type (foo) is not found.',
                         six.text_type(ex))

        env.register_profile('foo', plugin)
        self.assertEqual(plugin, env.get_profile('foo'))

    def test_get_profile_types(self):
        env = environment.Environment()
        plugin1 = mock.Mock()
        env.register_profile('foo', plugin1)
        plugin2 = mock.Mock()
        env.register_profile('bar', plugin2)

        actual = env.get_profile_types()
        self.assertIn({'name': 'foo'}, actual)
        self.assertIn({'name': 'bar'}, actual)

    def test_check_policy_type_name(self):
        env = environment.Environment()
        env._check_policy_type_name('abc')

        ex = self.assertRaises(exception.PolicyValidationFailed,
                               env._check_policy_type_name, '')
        self.assertEqual('Policy type name not specified', six.text_type(ex))
        ex = self.assertRaises(exception.PolicyValidationFailed,
                               env._check_policy_type_name, None)
        self.assertEqual('Policy type name not specified', six.text_type(ex))

        for v in [123, {}, ['a'], ('b', 'c'), True]:
            ex = self.assertRaises(exception.PolicyValidationFailed,
                                   env._check_policy_type_name, v)
            self.assertEqual('Policy type name is not a string',
                             six.text_type(ex))

    def test_register_and_get_policy(self):
        plugin = mock.Mock()
        env = environment.Environment()

        ex = self.assertRaises(exception.PolicyTypeNotFound,
                               env.get_policy, 'foo')
        self.assertEqual('Policy type (foo) is not found.',
                         six.text_type(ex))

        env.register_policy('foo', plugin)
        self.assertEqual(plugin, env.get_policy('foo'))

    def test_get_policy_types(self):
        env = environment.Environment()
        plugin1 = mock.Mock()
        env.register_policy('foo', plugin1)
        plugin2 = mock.Mock()
        env.register_policy('bar', plugin2)

        actual = env.get_policy_types()
        self.assertIn({'name': 'foo'}, actual)
        self.assertIn({'name': 'bar'}, actual)

    def test_read_global_environment(self):
        mock_dir = self.patchobject(glob, 'glob')
        mock_dir.return_value = ['/etc/senlin/environments/e.yaml']
        env_dir = '/etc/senlin/environments'
        env_contents = 'parameters:\n  p1: v1'
        env = environment.Environment()
        with mock.patch('senlin.engine.environment.open',
                        mock.mock_open(read_data=env_contents),
                        create=True) as mock_open:
            env.read_global_environment()

        mock_dir.assert_called_once_with(env_dir + '/*')
        mock_open.assert_called_once_with('%s/e.yaml' % env_dir)

    def test_empty_environment_dir(self):
        mock_dir = self.patchobject(glob, 'glob', return_value=[])
        env_dir = '/etc/senlin/environments'
        env = environment.Environment()
        env.read_global_environment()

        mock_dir.assert_called_once_with(env_dir + '/*')

    def test_read_global_environment_ioerror(self):
        mock_dir = self.patchobject(glob, 'glob')
        mock_dir.return_value = ['/etc/senlin/environments/e.yaml']
        env_dir = '/etc/senlin/environments'
        env = environment.Environment()
        env_contents = ''

        with mock.patch('senlin.engine.environment.open',
                        mock.mock_open(read_data=env_contents),
                        create=True) as mock_open:
            mock_open.side_effect = IOError
            env.read_global_environment()

        mock_dir.assert_called_once_with(env_dir + '/*')
        mock_open.assert_called_once_with('%s/e.yaml' % env_dir)

    def test_read_global_environment_parse_error(self):
        mock_dir = self.patchobject(glob, 'glob')
        mock_dir.return_value = ['/etc/senlin/environments/e.yaml']
        env_dir = '/etc/senlin/environments'
        env_contents = 'aii$%@@$#7'
        env = environment.Environment()

        with mock.patch('senlin.engine.environment.open',
                        mock.mock_open(read_data=env_contents),
                        create=True) as mock_open:
            env.read_global_environment()

        mock_dir.assert_called_once_with(env_dir + '/*')
        mock_open.assert_called_once_with('%s/e.yaml' % env_dir)

    def test_global_initialize(self):
        mock_mapping = mock.Mock(return_value=[['aaa', mock.Mock()]])

        environment._environment = None
        environment.initialize(mapping_func=mock_mapping)

        expected = [mock.call('senlin.profiles'),
                    mock.call('senlin.policies')]

        self.assertIsNotNone(environment._environment)
        self.assertEqual(expected, mock_mapping.call_args_list)
        self.assertIsNotNone(environment.global_env().get_profile('aaa'))
        self.assertIsNotNone(environment.global_env().get_policy('aaa'))
