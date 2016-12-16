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
import testtools

from senlin.common import exception as exc
from senlin.objects import receiver as ro


class ReceiverTest(testtools.TestCase):

    def setUp(self):
        super(ReceiverTest, self).setUp()
        self.ctx = mock.Mock()

    @mock.patch.object(ro.Receiver, 'get')
    def test_find_by_uuid(self, mock_get):
        fake_obj = mock.Mock()
        mock_get.return_value = fake_obj
        fake_id = uuidutils.generate_uuid()

        res = ro.Receiver.find(self.ctx, fake_id)

        self.assertEqual(fake_obj, res)
        mock_get.assert_called_once_with(self.ctx, fake_id)

    @mock.patch.object(ro.Receiver, 'get_by_name')
    @mock.patch.object(ro.Receiver, 'get')
    def test_find_by_uuid_as_name(self, mock_get, mock_get_name):
        mock_get.return_value = None
        fake_obj = mock.Mock()
        mock_get_name.return_value = fake_obj
        fake_id = uuidutils.generate_uuid()

        res = ro.Receiver.find(self.ctx, fake_id, project_safe=False)

        self.assertEqual(fake_obj, res)
        mock_get.assert_called_once_with(self.ctx, fake_id, project_safe=False)
        mock_get_name.assert_called_once_with(self.ctx, fake_id,
                                              project_safe=False)

    @mock.patch.object(ro.Receiver, 'get_by_name')
    def test_find_by_name(self, mock_get_name):
        fake_obj = mock.Mock()
        mock_get_name.return_value = fake_obj
        fake_id = 'not-a-uuid'

        res = ro.Receiver.find(self.ctx, fake_id)

        self.assertEqual(fake_obj, res)
        mock_get_name.assert_called_once_with(self.ctx, fake_id)

    @mock.patch.object(ro.Receiver, 'get_by_short_id')
    @mock.patch.object(ro.Receiver, 'get_by_name')
    def test_find_by_short_id(self, mock_get_name, mock_get_shortid):
        mock_get_name.return_value = None
        fake_obj = mock.Mock()
        mock_get_shortid.return_value = fake_obj
        fake_id = '12345678'

        res = ro.Receiver.find(self.ctx, fake_id, project_safe=False)

        self.assertEqual(fake_obj, res)
        mock_get_name.assert_called_once_with(self.ctx, fake_id,
                                              project_safe=False)
        mock_get_shortid.assert_called_once_with(self.ctx, fake_id,
                                                 project_safe=False)

    @mock.patch.object(ro.Receiver, 'get_by_short_id')
    @mock.patch.object(ro.Receiver, 'get_by_name')
    def test_find_not_found(self, mock_get_name, mock_get_shortid):
        mock_get_shortid.return_value = None
        mock_get_name.return_value = None
        fake_id = '12345678'  # not a uuid

        self.assertRaises(exc.ResourceNotFound,
                          ro.Receiver.find,
                          self.ctx, fake_id)

        mock_get_name.assert_called_once_with(self.ctx, fake_id)
