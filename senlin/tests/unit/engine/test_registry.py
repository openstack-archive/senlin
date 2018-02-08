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

from senlin.engine import registry
from senlin.tests.unit.common import base


class PluginInfoTest(base.SenlinTestCase):

    def setUp(self):
        super(PluginInfoTest, self).setUp()
        self.reg = registry.Registry('SENLIN', None)

    def test_create(self):
        plugin = mock.Mock()
        pi = registry.PluginInfo(self.reg, 'FOO', plugin)

        self.assertIsInstance(pi, registry.PluginInfo)
        self.assertEqual(self.reg, pi.registry)
        self.assertEqual('FOO', pi.name)
        self.assertEqual(plugin, pi.plugin)
        self.assertTrue(pi.user_provided)

    def test_eq_ne(self):
        plugin1 = mock.Mock()
        plugin2 = mock.Mock()
        pi1 = registry.PluginInfo(self.reg, 'FOO', plugin1)
        pi2 = registry.PluginInfo(self.reg, 'FOO', plugin1)
        pi3 = registry.PluginInfo(self.reg, 'BAR', plugin1)
        pi4 = registry.PluginInfo(self.reg, 'FOO', plugin2)

        self.assertIsNotNone(pi1)
        self.assertEqual(pi1, pi2)
        self.assertNotEqual(pi1, pi3)
        self.assertNotEqual(pi1, pi4)
        self.assertNotEqual(pi2, pi4)
        self.assertNotEqual(pi3, pi4)
        self.assertEqual(pi1, pi2)
        self.assertNotEqual(pi1, pi3)
        self.assertNotEqual(pi1, pi4)
        self.assertNotEqual(pi2, pi4)
        self.assertNotEqual(pi3, pi4)
        self.assertIsNotNone(pi1)

    def test_ordering(self):
        plugin1 = mock.Mock()
        plugin2 = mock.Mock()
        pi1 = registry.PluginInfo(self.reg, 'FOO', plugin1)
        pi2 = registry.PluginInfo(self.reg, 'FOO', plugin1)
        pi2.user_provided = False
        self.assertLess(pi1, pi2)

        pi3 = registry.PluginInfo(self.reg, 'FOO_LONG', plugin1)
        self.assertLess(pi3, pi1)

        pi4 = registry.PluginInfo(self.reg, 'BAR', plugin2)
        self.assertLess(pi4, pi1)
        self.assertNotEqual(pi4, pi1)

    def test_str(self):
        plugin = mock.Mock()
        pi = registry.PluginInfo(self.reg, 'FOO', plugin)
        expected = '[Plugin](User:True) FOO -> %s' % str(plugin)
        self.assertEqual(expected, str(pi))


class RegistryTest(base.SenlinTestCase):

    def test_create(self):
        reg = registry.Registry('SENLIN', None)
        self.assertEqual('SENLIN', reg.registry_name)
        self.assertEqual({}, reg._registry)
        self.assertTrue(reg.is_global)
        self.assertIsNone(reg.global_registry)

        reg_sub = registry.Registry('SUB', reg)
        self.assertEqual('SUB', reg_sub.registry_name)
        self.assertEqual({}, reg_sub._registry)
        self.assertFalse(reg_sub.is_global)
        self.assertEqual(reg, reg_sub.global_registry)

    def test_register_info(self):
        reg = registry.Registry('SENLIN', None)
        plugin = mock.Mock()
        pi = registry.PluginInfo(reg, 'FOO', plugin)
        reg._register_info('FOO', pi)

        result = reg._registry.get('FOO')
        self.assertEqual(pi, result)

        # register the same name and same PluginInfo, no new entry added
        reg._register_info('FOO', pi)
        self.assertEqual(1, len(reg._registry))

        # register the same name with different PluginInfo -> replacement
        new_pi = registry.PluginInfo(reg, 'FOO', plugin)
        reg._register_info('FOO', new_pi)
        self.assertEqual(1, len(reg._registry))

        # additional check: this is a global registry
        self.assertFalse(new_pi.user_provided)

        # removal
        reg._register_info('FOO', None)
        self.assertEqual(0, len(reg._registry))

    def test_register_plugin(self):
        reg = registry.Registry('SENLIN', None)
        plugin = mock.Mock()
        reg.register_plugin('FOO', plugin)

        pi = reg._registry.get('FOO')
        self.assertIsInstance(pi, registry.PluginInfo)
        self.assertEqual(plugin, pi.plugin)
        self.assertEqual('FOO', pi.name)

    def test_load(self):
        snippet = {
            'K2': 'Class2',
            'K4': 'Class4',
            'K5': 'Class5',
        }

        reg = registry.Registry('SENLIN', None)
        reg.load(snippet)
        pi2 = reg._registry.get('K2')
        self.assertIsInstance(pi2, registry.PluginInfo)
        self.assertEqual('K2', pi2.name)
        self.assertEqual('Class2', pi2.plugin)
        pi4 = reg._registry.get('K4')
        self.assertIsInstance(pi4, registry.PluginInfo)
        self.assertEqual('K4', pi4.name)
        self.assertEqual('Class4', pi4.plugin)
        pi5 = reg._registry.get('K5')
        self.assertIsInstance(pi5, registry.PluginInfo)
        self.assertEqual('K5', pi5.name)
        self.assertEqual('Class5', pi5.plugin)

        # load with None
        snippet = {
            'K5': None
        }
        reg.load(snippet)
        res = reg._registry.get('K5')
        self.assertIsNone(res)

    def test_iterable_by(self):
        reg = registry.Registry('GLOBAL', None)
        plugin = mock.Mock()
        reg.register_plugin('FOO', plugin)

        res = [r for r in reg.iterable_by('FOO')]
        self.assertEqual(1, len(res))
        self.assertEqual('FOO', res[0].name)

    def test_get_plugin(self):
        # Global registry
        reg = registry.Registry('GLOBAL', None)
        self.assertTrue(reg.is_global)

        # Register plugin in global
        plugin = mock.Mock()
        reg.register_plugin('FOO', plugin)
        self.assertEqual(plugin, reg.get_plugin('FOO'))

        # Sub registry
        sub = registry.Registry('SUB', reg)
        self.assertFalse(sub.is_global)

        # Retrieve plugin from global registry
        self.assertEqual(plugin, sub.get_plugin('FOO'))

        # Plugin in local registry overrides that in the global registry
        plugin_new = mock.Mock()
        sub.register_plugin('FOO', plugin_new)
        self.assertEqual(plugin_new, sub.get_plugin('FOO'))

    def test_as_dict(self):
        reg = registry.Registry('GLOBAL', None)
        plugin1 = mock.Mock()
        reg.register_plugin('FOO', plugin1)
        plugin2 = mock.Mock()
        reg.register_plugin('BAR', plugin2)

        res = reg.as_dict()
        self.assertIsInstance(res, dict)
        self.assertEqual(plugin1, res.get('FOO'))
        self.assertEqual(plugin2, res.get('BAR'))

    def test_get_types(self):
        reg = registry.Registry('GLOBAL', None)
        plugin1 = mock.Mock(VERSIONS={'1.0': 'bar'})
        reg.register_plugin('FOO-1.0', plugin1)
        plugin2 = mock.Mock(VERSIONS={'1.1': 'car'})
        reg.register_plugin('BAR-1.1', plugin2)

        self.assertIn(
            {
                'name': 'FOO',
                'version': '1.0',
                'support_status': {'1.0': 'bar'}
            },
            reg.get_types())
        self.assertIn(
            {
                'name': 'BAR',
                'version': '1.1',
                'support_status': {'1.1': 'car'}
            },
            reg.get_types())
