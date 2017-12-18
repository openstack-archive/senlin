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
from oslo_utils import timeutils
from oslo_utils import uuidutils
import six

from senlin.common import exception as exc
from senlin.common import utils as common_utils
from senlin.objects import node as no
from senlin.tests.unit.common import base
from senlin.tests.unit.common import utils


class TestNode(base.SenlinTestCase):

    def setUp(self):
        super(TestNode, self).setUp()
        self.ctx = utils.dummy_context()

    @mock.patch.object(no.Node, 'get')
    def test_find_by_uuid(self, mock_get):
        x_node = mock.Mock()
        mock_get.return_value = x_node
        aid = uuidutils.generate_uuid()

        result = no.Node.find(self.ctx, aid)

        self.assertEqual(x_node, result)
        mock_get.assert_called_once_with(self.ctx, aid, project_safe=True)

    @mock.patch.object(no.Node, 'get_by_name')
    @mock.patch.object(no.Node, 'get')
    def test_find_by_uuid_as_name(self, mock_get, mock_name):
        mock_get.return_value = None
        x_node = mock.Mock()
        mock_name.return_value = x_node
        aid = uuidutils.generate_uuid()

        result = no.Node.find(self.ctx, aid, False)

        self.assertEqual(x_node, result)
        mock_get.assert_called_once_with(self.ctx, aid, project_safe=False)
        mock_name.assert_called_once_with(self.ctx, aid, project_safe=False)

    @mock.patch.object(no.Node, 'get_by_name')
    def test_find_by_name(self, mock_name):
        x_node = mock.Mock()
        mock_name.return_value = x_node
        aid = 'not-a-uuid'

        result = no.Node.find(self.ctx, aid)

        self.assertEqual(x_node, result)
        mock_name.assert_called_once_with(self.ctx, aid, project_safe=True)

    @mock.patch.object(no.Node, 'get_by_short_id')
    @mock.patch.object(no.Node, 'get_by_name')
    def test_find_by_short_id(self, mock_name, mock_shortid):
        mock_name.return_value = None
        x_node = mock.Mock()
        mock_shortid.return_value = x_node
        aid = 'abcdef'

        result = no.Node.find(self.ctx, aid, False)

        self.assertEqual(x_node, result)
        mock_name.assert_called_once_with(self.ctx, aid, project_safe=False)
        mock_shortid.assert_called_once_with(self.ctx, aid, project_safe=False)

    @mock.patch.object(no.Node, 'get_by_name')
    @mock.patch.object(no.Node, 'get_by_short_id')
    def test_find_not_found(self, mock_shortid, mock_name):
        mock_name.return_value = None
        mock_shortid.return_value = None

        ex = self.assertRaises(exc.ResourceNotFound,
                               no.Node.find,
                               self.ctx, 'BOGUS')
        self.assertEqual("The node 'BOGUS' could not be found.",
                         six.text_type(ex))
        mock_name.assert_called_once_with(self.ctx, 'BOGUS', project_safe=True)
        mock_shortid.assert_called_once_with(self.ctx, 'BOGUS',
                                             project_safe=True)

    def test_to_dict(self):
        PROFILE_ID = uuidutils.generate_uuid()
        CLUSTER_ID = uuidutils.generate_uuid()
        values = {
            'name': 'test_node',
            'profile_id': PROFILE_ID,
            'cluster_id': CLUSTER_ID,
            'user': self.ctx.user_id,
            'project': self.ctx.project_id,
            'index': -1,
            'init_at': timeutils.utcnow(True),
            'status': 'Initializing',
        }
        node = no.Node.create(self.ctx, values)
        self.assertIsNotNone(node.id)

        expected = {
            'id': node.id,
            'name': node.name,
            'cluster_id': node.cluster_id,
            'physical_id': node.physical_id,
            'profile_id': node.profile_id,
            'user': node.user,
            'project': node.project,
            'domain': node.domain,
            'index': node.index,
            'role': node.role,
            'init_at': common_utils.isotime(node.init_at),
            'created_at': common_utils.isotime(node.created_at),
            'updated_at': common_utils.isotime(node.updated_at),
            'status': node.status,
            'status_reason': node.status_reason,
            'data': node.data,
            'metadata': node.metadata,
            'dependents': node.dependents,
            'profile_name': node.profile_name,
        }

        result = no.Node.get(self.ctx, node.id)
        dt = result.to_dict()
        self.assertEqual(expected, dt)
