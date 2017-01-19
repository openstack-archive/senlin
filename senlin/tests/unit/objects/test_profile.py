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
from senlin.objects import profile as po


class TestProfile(testtools.TestCase):

    def setUp(self):
        super(TestProfile, self).setUp()
        self.ctx = mock.Mock()

    @mock.patch.object(po.Profile, 'get')
    def test_find_by_uuid(self, mock_get):
        x_profile = mock.Mock()
        mock_get.return_value = x_profile
        aid = uuidutils.generate_uuid()

        result = po.Profile.find(self.ctx, aid, project_safe=True)

        self.assertEqual(x_profile, result)
        mock_get.assert_called_once_with(self.ctx, aid, project_safe=True)

    @mock.patch.object(po.Profile, 'get_by_name')
    @mock.patch.object(po.Profile, 'get')
    def test_find_by_uuid_as_name(self, mock_get, mock_get_name):
        x_profile = mock.Mock()
        mock_get_name.return_value = x_profile
        mock_get.return_value = None
        aid = uuidutils.generate_uuid()

        result = po.Profile.find(self.ctx, aid, project_safe=False)

        self.assertEqual(x_profile, result)
        mock_get.assert_called_once_with(self.ctx, aid, project_safe=False)
        mock_get_name.assert_called_once_with(self.ctx, aid,
                                              project_safe=False)

    @mock.patch.object(po.Profile, 'get_by_name')
    def test_find_by_name(self, mock_get_name):
        x_profile = mock.Mock()
        mock_get_name.return_value = x_profile

        aid = 'this-is-not-uuid'
        result = po.Profile.find(self.ctx, aid, project_safe=True)

        self.assertEqual(x_profile, result)
        mock_get_name.assert_called_once_with(self.ctx, aid, project_safe=True)

    @mock.patch.object(po.Profile, 'get_by_short_id')
    @mock.patch.object(po.Profile, 'get_by_name')
    def test_find_by_shortid(self, mock_get_name, mock_get_shortid):
        x_profile = mock.Mock()
        mock_get_shortid.return_value = x_profile
        mock_get_name.return_value = None

        aid = 'abcd-1234-abcd'
        result = po.Profile.find(self.ctx, aid, project_safe=False)

        self.assertEqual(x_profile, result)
        mock_get_name.assert_called_once_with(self.ctx, aid,
                                              project_safe=False)
        mock_get_shortid.assert_called_once_with(self.ctx, aid,
                                                 project_safe=False)

    @mock.patch.object(po.Profile, 'get_by_short_id')
    @mock.patch.object(po.Profile, 'get_by_name')
    def test_find_not_found(self, mock_get_name, mock_get_shortid):
        mock_get_name.return_value = None
        mock_get_shortid.return_value = None

        ex = self.assertRaises(exc.ResourceNotFound,
                               po.Profile.find,
                               self.ctx, 'Bogus')

        self.assertEqual("The profile 'Bogus' could not be found.",
                         six.text_type(ex))
        mock_get_name.assert_called_once_with(self.ctx, 'Bogus')
