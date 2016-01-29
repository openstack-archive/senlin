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

from senlin.drivers import base as driver_base
from senlin.profiles.os.heat import stack
from senlin.tests.unit.common import base
from senlin.tests.unit.common import utils


class TestHeatStackProfile(base.SenlinTestCase):

    def setUp(self):
        super(TestHeatStackProfile, self).setUp()
        self.context = utils.dummy_context()
        self.spec = {
            'type': 'os.heat.stack',
            'version': '1.0',
            'properties': {
                'template': {"Template": "data"},
                'context': {},
                'parameters': {'foo': 'bar'},
                'files': {},
                'timeout': 60,
                'disable_rollback': True,
                'environment': {}
            }
        }

    def test_stack_init(self):
        profile = stack.StackProfile('t', self.spec)
        self.assertIsNone(profile.hc)
        self.assertIsNone(profile.stack_id)

    @mock.patch.object(driver_base, 'SenlinDriver')
    def test_heat_client_create_new_hc(self, mock_senlindriver):
        test_stack = mock.Mock()
        hc = mock.Mock()
        sd = mock.Mock()
        sd.orchestration.return_value = hc
        mock_senlindriver.return_value = sd

        profile = stack.StackProfile('t', self.spec)

        # New hc will be created if no cache is found
        profile.hc = None
        params = mock.Mock()
        mock_param = self.patchobject(profile, '_build_conn_params',
                                      return_value=params)
        res = profile.heat(test_stack)
        self.assertEqual(hc, res)
        self.assertEqual(hc, profile.hc)
        mock_param.assert_called_once_with(test_stack.user, test_stack.project)
        sd.orchestration.assert_called_once_with(params)

    @mock.patch.object(driver_base, 'SenlinDriver')
    def test_heat_client_use_cached_hc(self, mock_senlindriver):
        test_stack = mock.Mock()
        hc = mock.Mock()
        sd = mock.Mock()
        sd.orchestration.return_value = hc
        mock_senlindriver.return_value = sd

        profile = stack.StackProfile('t', self.spec)

        # Cache hc will be used
        profile.hc = hc
        self.assertEqual(hc, profile.heat(test_stack))

    def test_do_validate(self):
        profile = stack.StackProfile('t', self.spec)

        profile.hc = mock.MagicMock()
        test_stack = mock.Mock()
        test_stack.name = 'test_stack'
        self.assertTrue(profile.do_validate(test_stack))
        self.assertTrue(profile.hc.stacks.validate.called)

    def test_check_action_complete(self):
        profile = stack.StackProfile('t', self.spec)

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
        profile = stack.StackProfile('t', self.spec)

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
        profile = stack.StackProfile('t', self.spec)

        test_stack = mock.Mock()
        test_stack.physical_id = 'ce8ae86c-9810-4cb1-8888-7fb53bc523bf'
        profile.hc = mock.MagicMock()
        profile._check_action_complete = mock.MagicMock(return_value=True)
        profile.hc.stack_delete = mock.MagicMock()
        self.assertTrue(profile.do_delete(test_stack))
        self.assertTrue(profile.hc.stack_delete.called)
        self.assertTrue(profile.hc.wait_for_stack_delete.called)

    def test_do_update(self):
        profile = stack.StackProfile('t', self.spec)

        # Check New Stack Path
        test_stack = mock.Mock()
        test_stack.physical_id = None
        new_profile = mock.Mock()
        self.assertTrue(profile.do_update(test_stack, new_profile))

        # New Profile
        new_spec = {
            'type': 'os.heat.stack',
            'version': '1.0',
            'properties': {
                'template': {"Template": "data update"},
                'context': {},
                'parameters': {'new': 'params'},
                'files': {},
                'timeout': 60,
                'disable_rollback': True,
                'environment': {}
            }
        }
        new_profile = stack.StackProfile('u', new_spec)

        # Check Update Stack Path
        test_stack.physical_id = 'ce8ae86c-9810-4cb1-8888-7fb53bc523bf'
        profile.hc = mock.MagicMock()
        profile._check_action_complete = mock.MagicMock(return_value=True)
        profile.hc.stack_update = mock.MagicMock()
        self.assertTrue(profile.do_update(test_stack, new_profile))
        self.assertTrue(profile.hc.stack_update.called)
        self.assertTrue(profile._check_action_complete.called)

    def test_do_update_template(self):
        profile = stack.StackProfile('t', self.spec)
        hc = mock.Mock()
        self.patchobject(profile, 'heat', return_value=hc)
        mock_check = self.patchobject(profile, '_check_action_complete',
                                      return_value=True)
        stack_obj = mock.Mock()
        stack_obj.physical_id = 'STACKID'
        new_spec = copy.deepcopy(self.spec)
        new_spec['properties']['template'] = {"Template": "data update"}
        new_profile = stack.StackProfile('u', new_spec)

        profile.do_update(stack_obj, new_profile)
        hc.stack_update.assert_called_once_with(
            'STACKID', template={"Template": "data update"})
        mock_check.assert_called_once_with(stack_obj, 'UPDATE')

    def test_do_update_params(self):
        profile = stack.StackProfile('t', self.spec)
        hc = mock.Mock()
        self.patchobject(profile, 'heat', return_value=hc)
        mock_check = self.patchobject(profile, '_check_action_complete',
                                      return_value=True)
        stack_obj = mock.Mock()
        stack_obj.physical_id = 'STACKID'
        new_spec = copy.deepcopy(self.spec)
        new_spec['properties']['parameters'] = {"new": "params"}
        new_profile = stack.StackProfile('u', new_spec)

        profile.do_update(stack_obj, new_profile)
        hc.stack_update.assert_called_once_with('STACKID',
                                                parameters={"new": "params"})
        mock_check.assert_called_once_with(stack_obj, 'UPDATE')

    def test_do_update_timeout(self):
        profile = stack.StackProfile('t', self.spec)
        hc = mock.Mock()
        self.patchobject(profile, 'heat', return_value=hc)
        mock_check = self.patchobject(profile, '_check_action_complete',
                                      return_value=True)
        stack_obj = mock.Mock()
        stack_obj.physical_id = 'STACKID'
        new_spec = copy.deepcopy(self.spec)
        new_spec['properties']['timeout'] = 120
        new_profile = stack.StackProfile('u', new_spec)

        profile.do_update(stack_obj, new_profile)
        hc.stack_update.assert_called_once_with('STACKID', timeout_mins=120)
        mock_check.assert_called_once_with(stack_obj, 'UPDATE')

    def test_do_update_disable_rollback(self):
        profile = stack.StackProfile('t', self.spec)
        hc = mock.Mock()
        self.patchobject(profile, 'heat', return_value=hc)
        mock_check = self.patchobject(profile, '_check_action_complete',
                                      return_value=True)
        stack_obj = mock.Mock()
        stack_obj.physical_id = 'STACKID'
        new_spec = copy.deepcopy(self.spec)
        new_spec['properties']['disable_rollback'] = False
        new_profile = stack.StackProfile('u', new_spec)

        profile.do_update(stack_obj, new_profile)
        hc.stack_update.assert_called_once_with('STACKID',
                                                disable_rollback=False)
        mock_check.assert_called_once_with(stack_obj, 'UPDATE')

    def test_do_update_files(self):
        profile = stack.StackProfile('t', self.spec)
        hc = mock.Mock()
        self.patchobject(profile, 'heat', return_value=hc)
        mock_check = self.patchobject(profile, '_check_action_complete',
                                      return_value=True)
        stack_obj = mock.Mock()
        stack_obj.physical_id = 'STACKID'
        new_spec = copy.deepcopy(self.spec)
        new_spec['properties']['files'] = {"new": "file1"}
        new_profile = stack.StackProfile('u', new_spec)

        profile.do_update(stack_obj, new_profile)
        hc.stack_update.assert_called_once_with('STACKID',
                                                files={"new": "file1"})
        mock_check.assert_called_once_with(stack_obj, 'UPDATE')

    def test_do_update_environment(self):
        profile = stack.StackProfile('t', self.spec)
        hc = mock.Mock()
        self.patchobject(profile, 'heat', return_value=hc)
        mock_check = self.patchobject(profile, '_check_action_complete',
                                      return_value=True)
        stack_obj = mock.Mock()
        stack_obj.physical_id = 'STACKID'
        new_spec = copy.deepcopy(self.spec)
        new_spec['properties']['environment'] = {"new": "env1"}
        new_profile = stack.StackProfile('u', new_spec)

        profile.do_update(stack_obj, new_profile)
        hc.stack_update.assert_called_once_with('STACKID',
                                                environment={"new": "env1"})
        mock_check.assert_called_once_with(stack_obj, 'UPDATE')

    def test_do_update_no_change(self):
        profile = stack.StackProfile('t', self.spec)
        hc = mock.Mock()
        self.patchobject(profile, 'heat', return_value=hc)
        stack_obj = mock.Mock()
        stack_obj.physical_id = 'STACKID'
        new_spec = copy.deepcopy(self.spec)
        new_profile = stack.StackProfile('u', new_spec)

        res = profile.do_update(stack_obj, new_profile)
        self.assertTrue(res)

    def test_do_update_failed(self):
        profile = stack.StackProfile('t', self.spec)
        hc = mock.Mock()
        self.patchobject(profile, 'heat', return_value=hc)
        hc.stack_update.side_effect = Exception('Stack update failed.')
        stack_obj = mock.Mock()
        stack_obj.physical_id = 'STACKID'
        new_spec = copy.deepcopy(self.spec)
        new_spec['properties']['environment'] = {"new": "env1"}
        new_profile = stack.StackProfile('u', new_spec)

        res = profile.do_update(stack_obj, new_profile)
        hc.stack_update.assert_called_once_with('STACKID',
                                                environment={"new": "env1"})
        self.assertFalse(res)

    def test_do_check(self):
        profile = stack.StackProfile('t', self.spec)

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
        profile = stack.StackProfile('t', self.spec)

        hc = mock.Mock()
        details = mock.Mock()
        hc.stack_get.return_value = details
        test_stack = mock.Mock()
        profile.heat = mock.MagicMock(return_value=hc)

        test_stack.physical_id = None
        self.assertEqual({}, profile.do_get_details(test_stack))

        test_stack.physical_id = ''
        self.assertEqual({}, profile.do_get_details(test_stack))

        test_stack.physical_id = 'ce8ae86c-9810-4cb1-8888-7fb53bc523bf'
        res = profile.do_get_details(test_stack)
        hc.stack_get.assert_called_once_with(test_stack.physical_id)
        self.assertEqual(details, res)
