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

from senlin.drivers.os import mistral_v2
from senlin.drivers import sdk
from senlin.tests.unit.common import base
from senlin.tests.unit.common import utils


class TestMistralV2(base.SenlinTestCase):

    def setUp(self):
        super(TestMistralV2, self).setUp()

        self.ctx = utils.dummy_context()
        self.conn_params = self.ctx.to_dict()
        self.mock_conn = mock.Mock()
        self.mock_create = self.patchobject(
            sdk, 'create_connection',
            return_value=self.mock_conn)
        self.workflow = self.mock_conn.workflow

    def test_init(self):
        d = mistral_v2.MistralClient(self.conn_params)

        self.mock_create.assert_called_once_with(self.conn_params)
        self.assertEqual(self.mock_conn, d.conn)

    def test_workflow_find(self):
        d = mistral_v2.MistralClient(self.conn_params)

        d.workflow_find('foo')

        self.workflow.find_workflow.assert_called_once_with(
            'foo', ignore_missing=True)
        self.workflow.find_workflow.reset_mock()

        d.workflow_find('foo', True)

        self.workflow.find_workflow.assert_called_once_with(
            'foo', ignore_missing=True)
        self.workflow.find_workflow.reset_mock()

        d.workflow_find('foo', False)

        self.workflow.find_workflow.assert_called_once_with(
            'foo', ignore_missing=False)

    def test_workflow_create(self):
        d = mistral_v2.MistralClient(self.conn_params)
        attrs = {
            'definition': 'fake_definition',
            'scope': 'private',
        }

        d.workflow_create('fake_definition', 'private')

        self.workflow.create_workflow.assert_called_once_with(**attrs)

    def test_workflow_delete(self):
        d = mistral_v2.MistralClient(self.conn_params)

        d.workflow_delete('foo', True)

        self.workflow.delete_workflow.assert_called_once_with(
            'foo', ignore_missing=True)
        self.workflow.delete_workflow.reset_mock()

        d.workflow_delete('foo', False)

        self.workflow.delete_workflow.assert_called_once_with(
            'foo', ignore_missing=False)

    def test_execution_create(self):
        d = mistral_v2.MistralClient(self.conn_params)
        attrs = {
            'workflow_name': 'workflow_name',
            'input': 'input'
        }
        d.execution_create('workflow_name', 'input')
        self.workflow.create_execution.assert_called_once_with(**attrs)

    def test_execution_delete(self):
        d = mistral_v2.MistralClient(self.conn_params)

        d.execution_delete('goo', True)

        self.workflow.delete_execution.assert_called_once_with(
            'goo', ignore_missing=True)

        self.workflow.delete_execution.reset_mock()

        d.execution_delete('goo', False)

        self.workflow.delete_execution.assert_called_once_with(
            'goo', ignore_missing=False)

    def test_wait_for_execution(self):
        self.workflow.find_execution.return_value = 'exn'
        d = mistral_v2.MistralClient(self.conn_params)

        d.wait_for_execution('exn', 'STATUS1', ['STATUS2'], 5, 10)

        self.workflow.wait_for_status.assert_called_once_with(
            'exn', 'STATUS1', ['STATUS2'], 5, 10)
