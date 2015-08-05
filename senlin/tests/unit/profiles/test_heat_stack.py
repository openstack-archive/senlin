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

from senlin.drivers.openstack import heat_v1 as heatclient
from senlin.profiles.os.heat import stack
from senlin.tests.unit.common import base
from senlin.tests.unit.common import utils


class TestHeatStackProfile(base.SenlinTestCase):

    def setUp(self):
        super(TestHeatStackProfile, self).setUp()
        self.context = utils.dummy_context()
        self.spec = {
            'template': {"Template": "data"},
            'context': {},
            'parameters': {'foo': 'bar'},
            'files': {},
            'timeout': 60,
            'disable_rollback': True,
            'environment': {}
        }

    def test_stack_init(self):
        kwargs = {
            'spec': self.spec
        }
        profile = stack.StackProfile('os.heat.stack',
                                     'test-profile',
                                     **kwargs)

        self.assertIsNone(profile.hc)
        self.assertIsNone(profile.stack_id)

    def test_heat_client(self):
        kwargs = {
            'spec': self.spec
        }
        profile = stack.StackProfile('os.heat.stack',
                                     'test-profile',
                                     **kwargs)

        profile.hc = mock.Mock()
        test_stack = mock.Mock()
        profile.heat(test_stack)
        self.assertIsNotNone(profile.hc)

        with mock.patch('senlin.drivers.openstack.heat_v1.HeatClient',
                        mock.MagicMock()):
            profile._get_connection_params = mock.MagicMock()
            profile.hc = None
            profile.heat(test_stack)
            self.assertIsNotNone(profile.hc)
            self.assertTrue(heatclient.HeatClient.called)

    def test_do_validate(self):
        kwargs = {
            'spec': self.spec
        }
        profile = stack.StackProfile('os.heat.stack',
                                     'test-profile',
                                     **kwargs)

        profile.hc = mock.MagicMock()
        test_stack = mock.Mock()
        test_stack.name = 'test_stack'
        self.assertTrue(profile.do_validate(test_stack))
        self.assertTrue(profile.hc.stacks.validate.called)

    def test_check_action_complete(self):
        kwargs = {
            'spec': self.spec
        }
        profile = stack.StackProfile('os.heat.stack',
                                     'test-profile',
                                     **kwargs)

        # Check 'IN_PROGRESS' Status Path
        test_stack = mock.Mock()
        fake_action = 'FAKE'
        fake_stack = mock.Mock()
        profile.hc = mock.MagicMock()
        fake_stack.status = 'FAKE_IN_PROGRESS'
        profile.hc.stack_get = mock.MagicMock(return_value=fake_stack)
        self.assertFalse(profile._check_action_complete(test_stack,
                                                        fake_action))
        self.assertTrue(profile.hc.stack_get.called)

        # Check 'COMPLETE' Status Path
        fake_stack.status = 'FAKE_COMPLETE'
        self.assertTrue(profile._check_action_complete(test_stack,
                                                       fake_action))
        self.assertEqual(2, profile.hc.stack_get.call_count)

    def test_do_create(self):
        kwargs = {
            'spec': self.spec
        }
        profile = stack.StackProfile('os.heat.stack',
                                     'test-profile',
                                     **kwargs)

        test_stack = mock.Mock()
        test_stack.name = 'test_stack'
        fake_stack = mock.Mock()
        profile.hc = mock.MagicMock()
        fake_stack.id = 'ce8ae86c-9810-4cb1-8888-7fb53bc523bf'
        profile._check_action_complete = mock.MagicMock(return_value=True)
        profile.hc.stack_create = mock.MagicMock(return_value=fake_stack)
        self.assertEqual(fake_stack.id, profile.do_create(test_stack))
        self.assertTrue(profile.hc.stack_create.called)
        self.assertTrue(profile._check_action_complete.called)

    def test_do_delete(self):
        kwargs = {
            'spec': self.spec
        }
        profile = stack.StackProfile('os.heat.stack',
                                     'test-profile',
                                     **kwargs)

        test_stack = mock.Mock()
        test_stack.physical_id = 'ce8ae86c-9810-4cb1-8888-7fb53bc523bf'
        profile.hc = mock.MagicMock()
        profile._check_action_complete = mock.MagicMock(return_value=True)
        profile.hc.stack_delete = mock.MagicMock()
        self.assertTrue(profile.do_delete(test_stack))
        self.assertTrue(profile.hc.stack_delete.called)
        self.assertTrue(profile._check_action_complete.called)

    def test_do_update(self):
        kwargs = {
            'spec': self.spec
        }
        profile = stack.StackProfile('os.heat.stack',
                                     'test-profile',
                                     **kwargs)

        # Check New Stack Path
        test_stack = mock.Mock()
        test_stack.physical_id = None
        new_profile = mock.Mock()
        self.assertTrue(profile.do_update(test_stack, new_profile))

        # New Profile
        update_spec = {
            'template': {"Template": "data update"},
            'context': {},
            'parameters': {'new': 'params'},
            'files': {},
            'timeout': 60,
            'disable_rollback': True,
            'environment': {}
        }
        kwargs = {
            'spec': update_spec
        }
        new_profile = stack.StackProfile('os.heat.stack',
                                         'update-profile',
                                         **kwargs)

        # Check Update Stack Path
        test_stack.physical_id = 'ce8ae86c-9810-4cb1-8888-7fb53bc523bf'
        profile.hc = mock.MagicMock()
        profile._check_action_complete = mock.MagicMock(return_value=True)
        profile.hc.stack_update = mock.MagicMock()
        self.assertTrue(profile.do_update(test_stack, new_profile))
        self.assertTrue(profile.hc.stack_update.called)
        self.assertTrue(profile._check_action_complete.called)

    def test_do_check(self):
        kwargs = {
            'spec': self.spec
        }
        profile = stack.StackProfile('os.heat.stack',
                                     'test-profile',
                                     **kwargs)
        heat_client = mock.Mock()
        test_stack = mock.Mock()
        test_stack.physical_id = 'ce8ae86c-9810-4cb1-8888-7fb53bc523bf'
        fake_stack = mock.Mock()
        fake_stack_complete = mock.Mock()
        fake_stack_complete.status = 'CHECK_COMPLETE'

        # Setup side effect of mock call to handle checking status
        # within while loop. 3rd call in while loop results in
        # fake_stack_complete mock object with a "complete" status.
        side_effect = [fake_stack, fake_stack, fake_stack_complete]

        # Check path where stack status can't be checked
        fake_stack.check = mock.MagicMock(side_effect=Exception())
        heat_client.stack_get = mock.MagicMock(side_effect=side_effect)
        profile.heat = mock.MagicMock(return_value=heat_client)
        self.assertFalse(profile.do_check(test_stack))
        self.assertTrue(profile.heat.called)
        self.assertTrue(heat_client.stack_get.called)
        self.assertTrue(fake_stack.check.called)

        # Check normal status path
        fake_stack.check = mock.MagicMock()
        fake_stack.status = 'CHECK_IN_PROGRESS'
        self.assertTrue(profile.do_check(test_stack))
        self.assertEqual(2, profile.heat.call_count)
        self.assertEqual(3, heat_client.stack_get.call_count)
        self.assertTrue(fake_stack.check.called)

    def test_do_get_details(self):
        kwargs = {
            'spec': self.spec
        }
        profile = stack.StackProfile('os.heat.stack',
                                     'test-profile',
                                     **kwargs)

        heat_client = mock.Mock()
        heat_client.stack_get = mock.MagicMock()
        test_stack = mock.Mock()
        profile.heat = mock.MagicMock(return_value=heat_client)

        test_stack.physical_id = None
        self.assertEqual({}, profile.do_get_details(test_stack))

        test_stack.physical_id = ''
        self.assertEqual({}, profile.do_get_details(test_stack))

        test_stack.physical_id = 'ce8ae86c-9810-4cb1-8888-7fb53bc523bf'
        profile.do_get_details(test_stack)
        self.assertTrue(heat_client.stack_get.called)
