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

from oslo_messaging.rpc import dispatcher as rpc

from senlin.common import consts
from senlin.common import exception as exc
from senlin.engine import service
from senlin.objects import cluster as co
from senlin.objects import event as eo
from senlin.objects.requests import events as oreo
from senlin.tests.unit.common import base
from senlin.tests.unit.common import utils


class EventTest(base.SenlinTestCase):

    def setUp(self):
        super(EventTest, self).setUp()
        self.ctx = utils.dummy_context(project='event_test_project')
        self.eng = service.EngineService('host-a', 'topic-a')

    @mock.patch.object(eo.Event, 'get_all')
    def test_event_list(self, mock_load):
        obj_1 = mock.Mock()
        obj_1.as_dict.return_value = {'level': consts.EVENT_LEVELS['DEBUG']}
        obj_2 = mock.Mock()
        obj_2.as_dict.return_value = {'level': consts.EVENT_LEVELS['INFO']}

        mock_load.return_value = [obj_1, obj_2]

        req = oreo.EventListRequest()
        result = self.eng.event_list(self.ctx, req.obj_to_primitive())
        expected = [{'level': 'DEBUG'}, {'level': 'INFO'}]

        self.assertEqual(expected, result)
        mock_load.assert_called_once_with(self.ctx, project_safe=True)

    @mock.patch.object(eo.Event, 'get_all')
    def test_event_list_with_params(self, mock_load):
        obj_1 = mock.Mock()
        obj_1.as_dict.return_value = {'level': consts.EVENT_LEVELS['DEBUG']}
        obj_2 = mock.Mock()
        obj_2.as_dict.return_value = {'level': consts.EVENT_LEVELS['INFO']}

        mock_load.return_value = [obj_1, obj_2]

        marker_uuid = '8216a86c-1bdc-442e-b493-329385d37cbc'
        req = oreo.EventListRequest(level=['DEBUG', 'INFO'],
                                    limit=123,
                                    marker=marker_uuid,
                                    sort=consts.EVENT_TIMESTAMP,
                                    project_safe=True)
        result = self.eng.event_list(self.ctx, req.obj_to_primitive())
        expected = [{'level': 'DEBUG'}, {'level': 'INFO'}]
        self.assertEqual(expected, result)

        filters = {'level': [consts.EVENT_LEVELS['DEBUG'],
                             consts.EVENT_LEVELS['INFO']]}
        mock_load.assert_called_once_with(self.ctx, filters=filters,
                                          sort=consts.EVENT_TIMESTAMP,
                                          limit=123,
                                          marker=marker_uuid,
                                          project_safe=True)

    @mock.patch.object(co.Cluster, 'find')
    @mock.patch.object(eo.Event, 'get_all')
    def test_event_list_with_cluster_id(self, mock_load, mock_find):
        obj_1 = mock.Mock()
        obj_1.as_dict.return_value = {'level': consts.EVENT_LEVELS['DEBUG']}
        obj_2 = mock.Mock()
        obj_2.as_dict.return_value = {'level': consts.EVENT_LEVELS['INFO']}
        mock_load.return_value = [obj_1, obj_2]
        fake_clusters = [mock.Mock(id='FAKE1'), mock.Mock(id='FAKE2')]
        mock_find.side_effect = fake_clusters

        req = oreo.EventListRequest(cluster_id=['CLUSTERA', 'CLUSTER2'],
                                    project_safe=True)

        result = self.eng.event_list(self.ctx, req.obj_to_primitive())

        expected = [{'level': 'DEBUG'}, {'level': 'INFO'}]
        self.assertEqual(expected, result)

        filters = {'cluster_id': ['FAKE1', 'FAKE2']}
        mock_load.assert_called_once_with(self.ctx, filters=filters,
                                          project_safe=True)
        mock_find.assert_has_calls([
            mock.call(self.ctx, 'CLUSTERA'),
            mock.call(self.ctx, 'CLUSTER2')
        ])

    @mock.patch.object(co.Cluster, 'find')
    @mock.patch.object(eo.Event, 'get_all')
    def test_event_list_with_cluster_not_found(self, mock_load, mock_find):
        mock_find.side_effect = [
            mock.Mock(id='FAKE1'),
            exc.ResourceNotFound(type='cluster', id='CLUSTER2'),
        ]
        req = oreo.EventListRequest(cluster_id=['CLUSTERA', 'CLUSTER2'],
                                    project_safe=True)

        result = self.eng.event_list(self.ctx, req.obj_to_primitive())

        self.assertEqual([], result)
        self.assertEqual(0, mock_load.call_count)
        mock_find.assert_has_calls([
            mock.call(self.ctx, 'CLUSTERA'),
            mock.call(self.ctx, 'CLUSTER2')
        ])

    def test_event_list_with_bad_params(self):
        req = oreo.EventListRequest(project_safe=False)
        ex = self.assertRaises(rpc.ExpectedException,
                               self.eng.event_list,
                               self.ctx, req.obj_to_primitive())
        self.assertEqual(exc.Forbidden, ex.exc_info[0])

    @mock.patch.object(eo.Event, 'get_all')
    def test_event_list_with_Auth(self, mock_load):
        mock_load.return_value = []

        req = oreo.EventListRequest(project_safe=True)
        result = self.eng.event_list(self.ctx, req.obj_to_primitive())
        self.assertEqual([], result)
        mock_load.assert_called_once_with(self.ctx, project_safe=True)

        self.ctx.is_admin = True

        mock_load.reset_mock()
        req = oreo.EventListRequest(project_safe=True)
        result = self.eng.event_list(self.ctx, req.obj_to_primitive())
        self.assertEqual([], result)
        mock_load.assert_called_once_with(self.ctx, project_safe=True)

        mock_load.reset_mock()
        req = oreo.EventListRequest(project_safe=False)
        result = self.eng.event_list(self.ctx, req.obj_to_primitive())
        self.assertEqual([], result)
        mock_load.assert_called_once_with(self.ctx, project_safe=False)

    @mock.patch.object(eo.Event, 'find')
    def test_event_get(self, mock_find):
        x_event = mock.Mock()
        x_event.as_dict.return_value = {'level': consts.EVENT_LEVELS['DEBUG']}
        mock_find.return_value = x_event

        req = oreo.EventGetRequest(identity='EVENT_ID')
        result = self.eng.event_get(self.ctx, req.obj_to_primitive())

        self.assertEqual({'level': 'DEBUG'}, result)
        mock_find.assert_called_once_with(self.ctx, 'EVENT_ID')

    @mock.patch.object(eo.Event, 'find')
    def test_event_get_not_found(self, mock_find):
        mock_find.side_effect = exc.ResourceNotFound(type='event', id='BOGUS')
        req = oreo.EventGetRequest(identity='BOGUS')
        ex = self.assertRaises(rpc.ExpectedException,
                               self.eng.event_get,
                               self.ctx, req.obj_to_primitive())

        self.assertEqual(exc.ResourceNotFound, ex.exc_info[0])
        mock_find.assert_called_once_with(self.ctx, 'BOGUS')
