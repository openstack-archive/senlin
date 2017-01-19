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
from senlin.objects import event as eo


class TestEvent(testtools.TestCase):

    def setUp(self):
        super(TestEvent, self).setUp()
        self.ctx = mock.Mock()

    @mock.patch.object(eo.Event, 'get')
    def test_find_by_uuid(self, mock_get):
        x_event = mock.Mock()
        mock_get.return_value = x_event
        aid = uuidutils.generate_uuid()

        result = eo.Event.find(self.ctx, aid)

        self.assertEqual(x_event, result)
        mock_get.assert_called_once_with(self.ctx, aid)

    @mock.patch.object(eo.Event, 'get_by_short_id')
    @mock.patch.object(eo.Event, 'get')
    def test_find_by_short_id(self, mock_get, mock_shortid):
        mock_get.return_value = None
        x_event = mock.Mock()
        mock_shortid.return_value = x_event
        aid = uuidutils.generate_uuid()

        result = eo.Event.find(self.ctx, aid, project_safe=False)

        self.assertEqual(x_event, result)
        mock_get.assert_called_once_with(self.ctx, aid, project_safe=False)
        mock_shortid.assert_called_once_with(self.ctx, aid, project_safe=False)

    @mock.patch.object(eo.Event, 'get_by_short_id')
    def test_find_by_short_id_directly(self, mock_shortid):
        x_event = mock.Mock()
        mock_shortid.return_value = x_event
        aid = 'abcdef'

        result = eo.Event.find(self.ctx, aid, project_safe=True)

        self.assertEqual(x_event, result)
        mock_shortid.assert_called_once_with(self.ctx, aid, project_safe=True)

    @mock.patch.object(eo.Event, 'get_by_short_id')
    def test_find_not_found(self, mock_shortid):
        mock_shortid.return_value = None

        ex = self.assertRaises(exc.ResourceNotFound,
                               eo.Event.find,
                               self.ctx, 'BOGUS')
        self.assertEqual("The event 'BOGUS' could not be found.",
                         six.text_type(ex))
        mock_shortid.assert_called_once_with(self.ctx, 'BOGUS')
