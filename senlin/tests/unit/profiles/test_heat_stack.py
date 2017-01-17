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
import six

from senlin.common import exception as exc
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
                'template_url': '/test_uri',
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
        self.assertIsNone(profile.stack_id)

    def test_do_validate(self):
        oc = mock.Mock()
        profile = stack.StackProfile('t', self.spec)
        profile._orchestrationclient = oc
        node_obj = mock.Mock(user='fake_user', project='fake_project')

        res = profile.do_validate(node_obj)

        props = self.spec['properties']
        call_args = {
            'stack_name': mock.ANY,
            'template': props['template'],
            'template_url': props['template_url'],
            'parameters': props['parameters'],
            'files': props['files'],
            'environment': props['environment'],
            'preview': True,
        }
        self.assertTrue(res)
        oc.stack_create.assert_called_once_with(**call_args)

    def test_do_validate_fails(self):
        oc = mock.Mock()
        profile = stack.StackProfile('t', self.spec)
        profile._orchestrationclient = oc
        err = exc.InternalError(code=400, message='Boom')
        oc.stack_create = mock.Mock(side_effect=err)
        node_obj = mock.Mock()
        node_obj.name = 'stack_node'

        ex = self.assertRaises(exc.InvalidSpec,
                               profile.do_validate, node_obj)

        props = self.spec['properties']
        call_args = {
            'stack_name': mock.ANY,
            'template': props['template'],
            'template_url': props['template_url'],
            'parameters': props['parameters'],
            'files': props['files'],
            'environment': props['environment'],
            'preview': True,
        }
        oc.stack_create.assert_called_once_with(**call_args)
        self.assertEqual('Failed in validating template: Boom',
                         six.text_type(ex))

    def test_do_create(self):
        oc = mock.Mock()
        profile = stack.StackProfile('t', self.spec)
        profile._orchestrationclient = oc
        test_stack = mock.Mock()
        test_stack.name = 'test_stack'
        fake_stack = mock.Mock(id='FAKE_ID')
        oc.stack_create = mock.Mock(return_value=fake_stack)

        # do it
        res = profile.do_create(test_stack)

        # assertions
        kwargs = {
            'stack_name': mock.ANY,
            'template': self.spec['properties']['template'],
            'template_url': self.spec['properties']['template_url'],
            'timeout_mins': self.spec['properties']['timeout'],
            'disable_rollback': self.spec['properties']['disable_rollback'],
            'parameters': self.spec['properties']['parameters'],
            'files': self.spec['properties']['files'],
            'environment': self.spec['properties']['environment'],
        }
        self.assertEqual('FAKE_ID', res)
        oc.stack_create.assert_called_once_with(**kwargs)
        oc.wait_for_stack.assert_called_once_with('FAKE_ID', 'CREATE_COMPLETE',
                                                  timeout=3600)

    def test_do_create_with_template_url(self):
        spec = {
            'type': 'os.heat.stack',
            'version': '1.0',
            'properties': {
                'template': {},
                'template_url': '/test_uri',
                'context': {},
                'parameters': {'foo': 'bar'},
                'files': {},
                'timeout': 60,
                'disable_rollback': True,
                'environment': {}
            }
        }
        oc = mock.Mock()
        profile = stack.StackProfile('t', spec)
        profile._orchestrationclient = oc
        test_stack = mock.Mock()
        test_stack.name = 'test_stack'
        fake_stack = mock.Mock(id='FAKE_ID')
        oc.stack_create = mock.Mock(return_value=fake_stack)

        # do it
        res = profile.do_create(test_stack)

        # assertions
        kwargs = {
            'stack_name': mock.ANY,
            'template': spec['properties']['template'],
            'template_url': spec['properties']['template_url'],
            'timeout_mins': spec['properties']['timeout'],
            'disable_rollback': spec['properties']['disable_rollback'],
            'parameters': spec['properties']['parameters'],
            'files': spec['properties']['files'],
            'environment': spec['properties']['environment'],
        }
        self.assertEqual('FAKE_ID', res)
        oc.stack_create.assert_called_once_with(**kwargs)
        oc.wait_for_stack.assert_called_once_with('FAKE_ID', 'CREATE_COMPLETE',
                                                  timeout=3600)

    def test_do_create_default_timeout(self):
        spec = copy.deepcopy(self.spec)
        del spec['properties']['timeout']
        profile = stack.StackProfile('t', spec)
        oc = mock.Mock()
        profile._orchestrationclient = oc
        test_stack = mock.Mock()
        test_stack.name = 'test_stack'
        fake_stack = mock.Mock(id='FAKE_ID')

        oc.stack_create = mock.Mock(return_value=fake_stack)
        oc.wait_for_stack = mock.Mock()

        # do it
        res = profile.do_create(test_stack)

        # assertions
        self.assertEqual('FAKE_ID', res)
        kwargs = {
            'stack_name': mock.ANY,
            'template': self.spec['properties']['template'],
            'template_url': self.spec['properties']['template_url'],
            'timeout_mins': None,
            'disable_rollback': self.spec['properties']['disable_rollback'],
            'parameters': self.spec['properties']['parameters'],
            'files': self.spec['properties']['files'],
            'environment': self.spec['properties']['environment'],
        }
        oc.stack_create.assert_called_once_with(**kwargs)
        oc.wait_for_stack.assert_called_once_with('FAKE_ID', 'CREATE_COMPLETE',
                                                  timeout=None)

    def test_do_create_failed_create(self):
        oc = mock.Mock()
        profile = stack.StackProfile('t', self.spec)

        stack_node = mock.Mock()
        stack_node.name = 'test_stack'
        err = exc.InternalError(code=400, message='Too Bad')
        oc.stack_create = mock.Mock(side_effect=err)
        profile._orchestrationclient = oc

        # do it
        ex = self.assertRaises(exc.EResourceCreation,
                               profile.do_create,
                               stack_node)

        # assertions
        self.assertEqual('Failed in creating stack: Too Bad.',
                         six.text_type(ex))
        call_args = {
            'stack_name': mock.ANY,
            'template': self.spec['properties']['template'],
            'template_url': self.spec['properties']['template_url'],
            'timeout_mins': self.spec['properties']['timeout'],
            'disable_rollback': self.spec['properties']['disable_rollback'],
            'parameters': self.spec['properties']['parameters'],
            'files': self.spec['properties']['files'],
            'environment': self.spec['properties']['environment'],
        }
        oc.stack_create.assert_called_once_with(**call_args)
        self.assertEqual(0, oc.wait_for_stack.call_count)

    def test_do_create_failed_wait(self):
        spec = copy.deepcopy(self.spec)
        del spec['properties']['timeout']
        profile = stack.StackProfile('t', spec)
        oc = mock.Mock()
        stack_node = mock.Mock()
        stack_node.name = 'test_stack'
        fake_stack = mock.Mock(id='FAKE_ID')

        oc.stack_create = mock.Mock(return_value=fake_stack)
        err = exc.InternalError(code=400, message='Timeout')
        oc.wait_for_stack = mock.Mock(side_effect=err)
        profile._orchestrationclient = oc

        # do it
        ex = self.assertRaises(exc.EResourceCreation,
                               profile.do_create,
                               stack_node)

        # assertions
        self.assertEqual('Failed in creating stack: Timeout.',
                         six.text_type(ex))
        kwargs = {
            'stack_name': mock.ANY,
            'template': self.spec['properties']['template'],
            'template_url': self.spec['properties']['template_url'],
            'timeout_mins': None,
            'disable_rollback': self.spec['properties']['disable_rollback'],
            'parameters': self.spec['properties']['parameters'],
            'files': self.spec['properties']['files'],
            'environment': self.spec['properties']['environment'],
        }
        oc.stack_create.assert_called_once_with(**kwargs)
        oc.wait_for_stack.assert_called_once_with('FAKE_ID', 'CREATE_COMPLETE',
                                                  timeout=None)

    def test_do_delete(self):
        profile = stack.StackProfile('t', self.spec)
        oc = mock.Mock()
        profile._orchestrationclient = oc
        test_stack = mock.Mock(physical_id='FAKE_ID')

        # do it
        res = profile.do_delete(test_stack)

        # assertions
        self.assertTrue(res)
        oc.stack_delete.assert_called_once_with('FAKE_ID', True)
        oc.wait_for_stack_delete.assert_called_once_with('FAKE_ID')

    def test_do_delete_ignore_missing(self):
        profile = stack.StackProfile('t', self.spec)
        oc = mock.Mock()
        test_stack = mock.Mock(physical_id='FAKE_ID')
        profile._orchestrationclient = oc

        # do it
        res = profile.do_delete(test_stack, ignore_missing=False)

        # assertions
        self.assertTrue(res)
        oc.stack_delete.assert_called_once_with('FAKE_ID', False)
        oc.wait_for_stack_delete.assert_called_once_with('FAKE_ID')

    def test_do_delete_failed_deletion(self):
        profile = stack.StackProfile('t', self.spec)
        oc = mock.Mock()
        profile._orchestrationclient = oc
        err = exc.InternalError(code=400, message='Boom')
        oc.stack_delete = mock.Mock(side_effect=err)
        test_stack = mock.Mock(physical_id='FAKE_ID')

        # do it
        ex = self.assertRaises(exc.EResourceDeletion,
                               profile.do_delete,
                               test_stack)

        # assertions
        self.assertEqual("Failed in deleting stack 'FAKE_ID': Boom.",
                         six.text_type(ex))
        oc.stack_delete.assert_called_once_with('FAKE_ID', True)
        self.assertEqual(0, oc.wait_for_stack_delete.call_count)

    def test_do_delete_failed_timeout(self):
        profile = stack.StackProfile('t', self.spec)
        oc = mock.Mock()
        test_stack = mock.Mock(physical_id='FAKE_ID')
        profile._orchestrationclient = oc
        err = exc.InternalError(code=400, message='Boom')
        oc.wait_for_stack_delete = mock.Mock(side_effect=err)

        # do it
        ex = self.assertRaises(exc.EResourceDeletion,
                               profile.do_delete, test_stack)

        # assertions
        self.assertEqual("Failed in deleting stack 'FAKE_ID': Boom.",
                         six.text_type(ex))
        oc.stack_delete.assert_called_once_with('FAKE_ID', True)
        oc.wait_for_stack_delete.assert_called_once_with('FAKE_ID')

    def test_do_update(self):
        profile = stack.StackProfile('t', self.spec)
        oc = mock.Mock()
        profile._orchestrationclient = oc
        test_stack = mock.Mock(physical_id='FAKE_ID')
        new_spec = {
            'type': 'os.heat.stack',
            'version': '1.0',
            'properties': {
                'template': {"Template": "data update"},
                'context': {},
                'parameters': {'new': 'params'},
                'files': {'file1': 'new_content'},
                'timeout': 123,
                'disable_rollback': False,
                'environment': {'foo': 'bar'}
            }
        }
        new_profile = stack.StackProfile('u', new_spec)

        # do it
        res = profile.do_update(test_stack, new_profile)

        # assertions
        self.assertTrue(res)
        kwargs = {
            'template': {'Template': 'data update'},
            'parameters': {'new': 'params'},
            'timeout_mins': 123,
            'disable_rollback': False,
            'files': {'file1': 'new_content'},
            'environment': {'foo': 'bar'},
        }
        oc.stack_update.assert_called_once_with('FAKE_ID', **kwargs)
        oc.wait_for_stack.assert_called_once_with(
            'FAKE_ID', 'UPDATE_COMPLETE', timeout=3600)

    def test_do_update_no_physical_stack(self):
        profile = stack.StackProfile('t', self.spec)
        test_stack = mock.Mock(physical_id=None)
        new_profile = mock.Mock()

        res = profile.do_update(test_stack, new_profile)

        self.assertFalse(res)

    def test_do_update_only_template(self):
        profile = stack.StackProfile('t', self.spec)
        oc = mock.Mock()
        profile._orchestrationclient = oc
        stack_obj = mock.Mock(physical_id='FAKE_ID')
        new_spec = copy.deepcopy(self.spec)
        new_spec['properties']['template'] = {"Template": "data update"}
        new_profile = stack.StackProfile('u', new_spec)

        res = profile.do_update(stack_obj, new_profile)

        self.assertTrue(res)
        oc.stack_update.assert_called_once_with(
            'FAKE_ID', template={"Template": "data update"})
        oc.wait_for_stack.assert_called_once_with(
            'FAKE_ID', 'UPDATE_COMPLETE', timeout=3600)

    def test_do_update_only_params(self):
        profile = stack.StackProfile('t', self.spec)
        oc = mock.Mock()
        profile._orchestrationclient = oc
        stack_obj = mock.Mock(physical_id='FAKE_ID')
        new_spec = copy.deepcopy(self.spec)
        new_spec['properties']['parameters'] = {"new": "params"}
        new_profile = stack.StackProfile('u', new_spec)

        res = profile.do_update(stack_obj, new_profile)

        self.assertTrue(res)
        oc.stack_update.assert_called_once_with(
            'FAKE_ID', parameters={"new": "params"})
        oc.wait_for_stack.assert_called_once_with(
            'FAKE_ID', 'UPDATE_COMPLETE', timeout=3600)

    def test_do_update_with_timeout_value(self):
        profile = stack.StackProfile('t', self.spec)
        oc = mock.Mock()
        profile._orchestrationclient = oc
        stack_obj = mock.Mock(physical_id='FAKE_ID')
        new_spec = copy.deepcopy(self.spec)
        new_spec['properties']['timeout'] = 120
        new_profile = stack.StackProfile('u', new_spec)

        # do it
        res = profile.do_update(stack_obj, new_profile)

        # assertions
        self.assertTrue(res)
        oc.stack_update.assert_called_once_with('FAKE_ID', timeout_mins=120)
        oc.wait_for_stack.assert_called_once_with(
            'FAKE_ID', 'UPDATE_COMPLETE', timeout=3600)

    def test_do_update_disable_rollback(self):
        profile = stack.StackProfile('t', self.spec)
        oc = mock.Mock()
        profile._orchestrationclient = oc
        stack_obj = mock.Mock(physical_id='FAKE_ID')
        new_spec = copy.deepcopy(self.spec)
        new_spec['properties']['disable_rollback'] = False
        new_profile = stack.StackProfile('u', new_spec)

        # do it
        res = profile.do_update(stack_obj, new_profile)

        # assertions
        self.assertTrue(res)
        oc.stack_update.assert_called_once_with('FAKE_ID',
                                                disable_rollback=False)
        oc.wait_for_stack.assert_called_once_with('FAKE_ID', 'UPDATE_COMPLETE',
                                                  timeout=3600)

    def test_do_update_files(self):
        profile = stack.StackProfile('t', self.spec)
        oc = mock.Mock()
        profile._orchestrationclient = oc
        stack_obj = mock.Mock(physical_id='FAKE_ID')
        new_spec = copy.deepcopy(self.spec)
        new_spec['properties']['files'] = {"new": "file1"}
        new_profile = stack.StackProfile('u', new_spec)

        # do it
        res = profile.do_update(stack_obj, new_profile)

        # assertions
        self.assertTrue(res)
        oc.stack_update.assert_called_once_with(
            'FAKE_ID', files={"new": "file1"})
        oc.wait_for_stack.assert_called_once_with(
            'FAKE_ID', 'UPDATE_COMPLETE', timeout=3600)

    def test_do_update_environment(self):
        profile = stack.StackProfile('t', self.spec)
        oc = mock.Mock()
        profile._orchestrationclient = oc
        stack_obj = mock.Mock(physical_id='FAKE_ID')
        new_spec = copy.deepcopy(self.spec)
        new_spec['properties']['environment'] = {"new": "env1"}
        new_profile = stack.StackProfile('u', new_spec)

        # do it
        res = profile.do_update(stack_obj, new_profile)

        # assertions
        self.assertTrue(res)
        oc.stack_update.assert_called_once_with(
            'FAKE_ID', environment={"new": "env1"})
        oc.wait_for_stack.assert_called_once_with(
            'FAKE_ID', 'UPDATE_COMPLETE', timeout=3600)

    def test_do_update_no_change(self):
        profile = stack.StackProfile('t', self.spec)
        oc = mock.Mock()
        profile._orchestrationclient = oc
        stack_obj = mock.Mock(physical_id='FAKE_ID')
        new_spec = copy.deepcopy(self.spec)
        new_profile = stack.StackProfile('u', new_spec)

        res = profile.do_update(stack_obj, new_profile)

        self.assertTrue(res)
        self.assertEqual(0, oc.stack_update.call_count)

    def test_do_update_failed_update(self):
        profile = stack.StackProfile('t', self.spec)
        oc = mock.Mock()
        profile._orchestrationclient = oc
        oc.stack_update = mock.Mock(
            side_effect=exc.InternalError(code=400, message='Failed'))
        stack_obj = mock.Mock(physical_id='FAKE_ID')
        new_spec = copy.deepcopy(self.spec)
        new_spec['properties']['environment'] = {"new": "env1"}
        new_profile = stack.StackProfile('u', new_spec)

        ex = self.assertRaises(exc.EResourceUpdate,
                               profile.do_update,
                               stack_obj, new_profile)

        oc.stack_update.assert_called_once_with(
            'FAKE_ID', environment={"new": "env1"})
        self.assertEqual(0, oc.wait_for_stack.call_count)
        self.assertEqual("Failed in updating stack 'FAKE_ID': "
                         "Failed.", six.text_type(ex))

    def test_do_update_timeout(self):
        profile = stack.StackProfile('t', self.spec)
        oc = mock.Mock()
        profile._orchestrationclient = oc
        oc.wait_for_stack = mock.Mock(
            side_effect=exc.InternalError(code=400, message='Timeout'))
        stack_obj = mock.Mock(physical_id='FAKE_ID')
        new_spec = copy.deepcopy(self.spec)
        new_spec['properties']['environment'] = {"new": "env1"}
        new_profile = stack.StackProfile('u', new_spec)

        ex = self.assertRaises(exc.EResourceUpdate,
                               profile.do_update,
                               stack_obj, new_profile)

        oc.stack_update.assert_called_once_with(
            'FAKE_ID', environment={"new": "env1"})
        oc.wait_for_stack.assert_called_once_with(
            'FAKE_ID', 'UPDATE_COMPLETE', timeout=3600)
        self.assertEqual("Failed in updating stack 'FAKE_ID': "
                         "Timeout.", six.text_type(ex))

    def test_do_check(self):
        node_obj = mock.Mock(physical_id='FAKE_ID')
        profile = stack.StackProfile('t', self.spec)
        oc = mock.Mock()
        profile._orchestrationclient = oc

        # do it
        res = profile.do_check(node_obj)

        # assertions
        self.assertTrue(res)
        oc.stack_check.assert_called_once_with('FAKE_ID')
        oc.wait_for_stack.assert_called_once_with(
            'FAKE_ID', 'CHECK_COMPLETE', timeout=3600)

    def test_do_check_no_physical_id(self):
        node_obj = mock.Mock(physical_id=None)
        profile = stack.StackProfile('t', self.spec)

        res = profile.do_check(node_obj)

        self.assertFalse(res)

    def test_do_check_failed_checking(self):
        node_obj = mock.Mock(physical_id='FAKE_ID')
        profile = stack.StackProfile('t', self.spec)
        oc = mock.Mock()
        profile._orchestrationclient = oc
        oc.stack_check = mock.Mock(
            side_effect=exc.InternalError(code=400, message='BOOM'))

        res = profile.do_check(node_obj)

        self.assertFalse(res)
        oc.stack_check.assert_called_once_with('FAKE_ID')
        self.assertEqual(0, oc.wait_for_stack.call_count)

    def test_do_check_failed_in_waiting(self):
        node_obj = mock.Mock(physical_id='FAKE_ID')
        profile = stack.StackProfile('t', self.spec)
        oc = mock.Mock()
        profile._orchestrationclient = oc
        oc.wait_for_stack = mock.Mock(
            side_effect=exc.InternalError(code=400, message='BOOM'))

        res = profile.do_check(node_obj)

        self.assertFalse(res)
        oc.stack_check.assert_called_once_with('FAKE_ID')
        oc.wait_for_stack.assert_called_once_with(
            'FAKE_ID', 'CHECK_COMPLETE', timeout=3600)

    def test_do_get_details(self):
        profile = stack.StackProfile('t', self.spec)
        oc = mock.Mock()
        profile._orchestrationclient = oc
        details = mock.Mock()
        details.to_dict.return_value = {'foo': 'bar'}
        oc.stack_get = mock.Mock(return_value=details)
        node_obj = mock.Mock(physical_id='FAKE_ID')

        res = profile.do_get_details(node_obj)

        self.assertEqual({'foo': 'bar'}, res)
        oc.stack_get.assert_called_once_with('FAKE_ID')

    def test_do_get_details_no_physical_id(self):
        profile = stack.StackProfile('t', self.spec)
        node_obj = mock.Mock(physical_id=None)

        res = profile.do_get_details(node_obj)

        self.assertEqual({}, res)

    def test_do_get_details_failed_retrieval(self):
        profile = stack.StackProfile('t', self.spec)
        node_obj = mock.Mock(physical_id='STACK_ID')
        oc = mock.Mock()
        oc.stack_get.side_effect = exc.InternalError(message='BOOM')
        profile._orchestrationclient = oc

        res = profile.do_get_details(node_obj)

        self.assertEqual({'Error': {'code': 500, 'message': 'BOOM'}}, res)
        oc.stack_get.assert_called_once_with('STACK_ID')
