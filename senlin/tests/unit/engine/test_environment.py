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
from senlin.tests.unit.common import base

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

    def test_create_global(self):
        e = environment.Environment(is_global=True)

        self.assertEqual({}, e.params)
        self.assertEqual('profiles', e.profile_registry.registry_name)
        self.assertEqual('policies', e.policy_registry.registry_name)
        self.assertEqual('drivers', e.driver_registry.registry_name)
        self.assertEqual('endpoints', e.endpoint_registry.registry_name)
        self.assertTrue(e.profile_registry.is_global)
        self.assertTrue(e.policy_registry.is_global)
        self.assertTrue(e.driver_registry.is_global)
        self.assertTrue(e.endpoint_registry.is_global)

    def test_create_default(self):
        ge = environment.global_env()
        e = environment.Environment()

        reg_prof = e.profile_registry
        reg_plcy = e.policy_registry
        reg_driv = e.driver_registry
        reg_endp = e.endpoint_registry

        self.assertEqual({}, e.params)
        self.assertEqual('profiles', reg_prof.registry_name)
        self.assertEqual('policies', reg_plcy.registry_name)
        self.assertEqual('drivers', reg_driv.registry_name)
        self.assertEqual('endpoints', reg_endp.registry_name)
        self.assertFalse(reg_prof.is_global)
        self.assertFalse(reg_plcy.is_global)
        self.assertFalse(reg_driv.is_global)
        self.assertFalse(reg_endp.is_global)
        self.assertEqual('profiles', ge.profile_registry.registry_name)
        self.assertEqual('policies', ge.policy_registry.registry_name)
        self.assertEqual('drivers', ge.driver_registry.registry_name)
        self.assertEqual('endpoints', ge.endpoint_registry.registry_name)
        self.assertEqual(ge.profile_registry, reg_prof.global_registry)
        self.assertEqual(ge.policy_registry, reg_plcy.global_registry)
        self.assertEqual(ge.driver_registry, reg_driv.global_registry)
        self.assertEqual(ge.endpoint_registry, reg_endp.global_registry)

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
            },
        }

        e = environment.Environment(env=env, is_global=True)

        self.assertEqual('v1', e.params['p1'])
        self.assertTrue(e.params['p2'])
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

    def test_parse_empty(self):
        env = environment.Environment()
        result = env.parse(None)
        self.assertEqual({}, result)

    def test_load(self):
        env = environment.Environment()
        env.load({})
        self.assertEqual({}, env.params)
        self.assertEqual({}, env.profile_registry._registry)
        self.assertEqual({}, env.policy_registry._registry)
        self.assertEqual({}, env.driver_registry._registry)

        env_dict = {
            'parameters': {
                'P': 'V'
            },
            'custom_profiles': {
                'C1': 'class1',
            },
            'custom_policies': {
                'C2': 'class2',
            },
        }
        env.load(env_dict)
        self.assertEqual('V', env.params['P'])
        self.assertEqual('class1', env.get_profile('C1'))
        self.assertEqual('class2', env.get_policy('C2'))

    def test_check_plugin_name(self):
        env = environment.Environment()

        for pt in ['Profile', 'Policy', 'Driver', 'Endpoint']:
            res = env._check_plugin_name(pt, 'abc')
            self.assertIsNone(res)

            ex = self.assertRaises(exception.InvalidPlugin,
                                   env._check_plugin_name, pt, '')
            self.assertEqual('%s type name not specified' % pt,
                             six.text_type(ex))

            ex = self.assertRaises(exception.InvalidPlugin,
                                   env._check_plugin_name, pt, None)
            self.assertEqual('%s type name not specified' % pt,
                             six.text_type(ex))

            for v in [123, {}, ['a'], ('b', 'c'), True]:
                ex = self.assertRaises(exception.InvalidPlugin,
                                       env._check_plugin_name, pt, v)
            self.assertEqual('%s type name is not a string' % pt,
                             six.text_type(ex))

    def test_register_and_get_profile(self):
        plugin = mock.Mock()
        env = environment.Environment()

        ex = self.assertRaises(exception.ResourceNotFound,
                               env.get_profile, 'foo')
        self.assertEqual("The profile_type 'foo' could not be found.",
                         six.text_type(ex))

        env.register_profile('foo', plugin)
        self.assertEqual(plugin, env.get_profile('foo'))

    def test_get_profile_types(self):
        env = environment.Environment()
        plugin1 = mock.Mock(VERSIONS={'1.0': 'v'})
        env.register_profile('foo-1.0', plugin1)
        plugin2 = mock.Mock(VERSIONS={'1.2': 'v1'})
        env.register_profile('bar-1.2', plugin2)

        actual = env.get_profile_types()
        self.assertIn(
            {'name': 'foo', 'version': '1.0', 'support_status': {'1.0': 'v'}},
            actual)
        self.assertIn(
            {'name': 'bar', 'version': '1.2', 'support_status': {'1.2': 'v1'}},
            actual)

    def test_register_and_get_policy(self):
        plugin = mock.Mock()
        env = environment.Environment()

        ex = self.assertRaises(exception.ResourceNotFound,
                               env.get_policy, 'foo')
        self.assertEqual("The policy_type 'foo' could not be found.",
                         six.text_type(ex))

        env.register_policy('foo', plugin)
        self.assertEqual(plugin, env.get_policy('foo'))

    def test_get_policy_types(self):
        env = environment.Environment()
        plugin1 = mock.Mock(VERSIONS={'0.1': 'v'})
        env.register_policy('foo-0.1', plugin1)
        plugin2 = mock.Mock(VERSIONS={'0.1': 'v1'})
        env.register_policy('bar-0.1', plugin2)

        actual = env.get_policy_types()
        self.assertIn(
            {'name': 'foo', 'version': '0.1', 'support_status': {'0.1': 'v'}},
            actual)
        self.assertIn(
            {'name': 'bar', 'version': '0.1', 'support_status': {'0.1': 'v1'}},
            actual)

    def test_register_and_get_driver_types(self):
        plugin = mock.Mock()
        env = environment.Environment()

        ex = self.assertRaises(exception.InvalidPlugin,
                               env.get_driver, 'foo')
        self.assertEqual('Driver plugin foo is not found.',
                         six.text_type(ex))

        env.register_driver('foo', plugin)
        self.assertEqual(plugin, env.get_driver('foo'))

    def test_get_driver_types(self):
        env = environment.Environment()
        plugin1 = mock.Mock(VERSIONS={})
        env.register_driver('foo', plugin1)
        plugin2 = mock.Mock(VERSIONS={})
        env.register_driver('bar', plugin2)

        actual = env.get_driver_types()
        self.assertIn(
            {'name': 'foo', 'version': '', 'support_status': {'': ''}},
            actual)
        self.assertIn(
            {'name': 'bar', 'version': '', 'support_status': {'': ''}},
            actual)

    def test_register_and_get_endpoints(self):
        plugin = mock.Mock()
        env = environment.Environment()

        ex = self.assertRaises(exception.InvalidPlugin,
                               env.get_endpoint, 'foo')
        self.assertEqual('Endpoint plugin foo is not found.',
                         six.text_type(ex))

        env.register_endpoint('foo', plugin)
        self.assertEqual(plugin, env.get_endpoint('foo'))

    def test_read_global_environment(self):
        mock_dir = self.patchobject(glob, 'glob')
        mock_dir.return_value = ['/etc/senlin/environments/e.yaml']
        env_dir = '/etc/senlin/environments'
        env_contents = 'parameters:\n  p1: v1'
        env = environment.Environment(is_global=True)
        with mock.patch('senlin.engine.environment.open',
                        mock.mock_open(read_data=env_contents),
                        create=True) as mock_open:
            env.read_global_environment()

        mock_dir.assert_called_with(env_dir + '/*')
        mock_open.assert_called_with('%s/e.yaml' % env_dir)

    def test_empty_environment_dir(self):
        mock_dir = self.patchobject(glob, 'glob', return_value=[])
        env_dir = '/etc/senlin/environments'
        env = environment.Environment()
        env.read_global_environment()

        mock_dir.assert_called_once_with(env_dir + '/*')

    def test_read_global_environment_oserror(self):
        mock_dir = self.patchobject(glob, 'glob')
        mock_dir.side_effect = OSError

        env = environment.Environment(is_global=True)
        env_dir = '/etc/senlin/environments'
        env.read_global_environment()

        mock_dir.assert_called_once_with(env_dir + '/*')

    def test_read_global_environment_ioerror(self):
        mock_dir = self.patchobject(glob, 'glob')
        mock_dir.return_value = ['/etc/senlin/environments/e.yaml']
        env_dir = '/etc/senlin/environments'
        env = environment.Environment(is_global=True)
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
        env = environment.Environment(is_global=True)

        with mock.patch('senlin.engine.environment.open',
                        mock.mock_open(read_data=env_contents),
                        create=True) as mock_open:
            env.read_global_environment()

        mock_dir.assert_called_once_with(env_dir + '/*')
        mock_open.assert_called_once_with('%s/e.yaml' % env_dir)

    @mock.patch.object(environment, '_get_mapping')
    def test_global_initialize(self, mock_mapping):
        mock_mapping.return_value = [['aaa', mock.Mock()]]

        environment._environment = None
        environment.initialize()

        expected = [mock.call('senlin.profiles'),
                    mock.call('senlin.policies'),
                    mock.call('senlin.drivers'),
                    mock.call('senlin.endpoints')]

        self.assertIsNotNone(environment._environment)
        self.assertEqual(expected, mock_mapping.call_args_list)
        self.assertIsNotNone(environment.global_env().get_profile('aaa'))
        self.assertIsNotNone(environment.global_env().get_policy('aaa'))
        self.assertIsNotNone(environment.global_env().get_driver('aaa'))
        self.assertIsNotNone(environment.global_env().get_endpoint('aaa'))
        environment._environment = None
