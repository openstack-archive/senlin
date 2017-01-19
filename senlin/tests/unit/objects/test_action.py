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
from oslo_utils import uuidutils
import six
import testtools

from senlin.common import exception as exc
from senlin.objects import action as ao


class TestAction(testtools.TestCase):

    def setUp(self):
        super(TestAction, self).setUp()
        self.ctx = mock.Mock()

    @mock.patch.object(ao.Action, 'get')
    def test_find_by_uuid(self, mock_get):
        x_action = mock.Mock()
        mock_get.return_value = x_action
        aid = uuidutils.generate_uuid()

        result = ao.Action.find(self.ctx, aid)

        self.assertEqual(x_action, result)
        mock_get.assert_called_once_with(self.ctx, aid)

    @mock.patch.object(ao.Action, 'get_by_name')
    @mock.patch.object(ao.Action, 'get')
    def test_find_by_uuid_as_name(self, mock_get, mock_name):
        mock_get.return_value = None
        x_action = mock.Mock()
        mock_name.return_value = x_action
        aid = uuidutils.generate_uuid()

        result = ao.Action.find(self.ctx, aid, project_safe=False)

        self.assertEqual(x_action, result)
        mock_get.assert_called_once_with(self.ctx, aid, project_safe=False)
        mock_name.assert_called_once_with(self.ctx, aid, project_safe=False)

    @mock.patch.object(ao.Action, 'get_by_name')
    def test_find_by_name(self, mock_name):
        x_action = mock.Mock()
        mock_name.return_value = x_action
        aid = 'not-a-uuid'

        result = ao.Action.find(self.ctx, aid, project_safe=True)

        self.assertEqual(x_action, result)
        mock_name.assert_called_once_with(self.ctx, aid, project_safe=True)

    @mock.patch.object(ao.Action, 'get_by_short_id')
    @mock.patch.object(ao.Action, 'get_by_name')
    def test_find_by_short_id(self, mock_name, mock_shortid):
        mock_name.return_value = None
        x_action = mock.Mock()
        mock_shortid.return_value = x_action
        aid = 'abcdef'

        result = ao.Action.find(self.ctx, aid)

        self.assertEqual(x_action, result)
        mock_name.assert_called_once_with(self.ctx, aid)
        mock_shortid.assert_called_once_with(self.ctx, aid)

    @mock.patch.object(ao.Action, 'get_by_name')
    @mock.patch.object(ao.Action, 'get_by_short_id')
    def test_find_not_found(self, mock_shortid, mock_name):
        mock_name.return_value = None
        mock_shortid.return_value = None

        ex = self.assertRaises(exc.ResourceNotFound,
                               ao.Action.find,
                               self.ctx, 'BOGUS')
        self.assertEqual("The action 'BOGUS' could not be found.",
                         six.text_type(ex))
        mock_name.assert_called_once_with(self.ctx, 'BOGUS')
        mock_shortid.assert_called_once_with(self.ctx, 'BOGUS')
