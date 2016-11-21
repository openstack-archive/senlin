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

from senlin.objects.requests import events
from senlin.tests.unit.common import base as test_base


class TestEventList(test_base.SenlinTestCase):

    def test_action_list_request_body_full(self):
        params = {
            'oid': ['f23ff00c-ec4f-412d-bd42-7f6e209819cb'],
            'otype': ['NODE'],
            'oname': ['mynode1'],
            'action': ['NODE_CREATE'],
            'cluster_id': ['f23ff00c-ec4f-412d-bd42-7f6e209819cb'],
            'level': ['ERROR'],
            'limit': 5,
            'marker': '98625fd0-b120-416c-a978-2fbe28c46820',
            'sort': 'timestamp:asc',
            'project_safe': False,
        }
        sot = events.EventListRequest(**params)
        self.assertEqual(['f23ff00c-ec4f-412d-bd42-7f6e209819cb'], sot.oid)
        self.assertEqual(['NODE'], sot.otype)
        self.assertEqual(['mynode1'], sot.oname)
        self.assertEqual(['NODE_CREATE'], sot.action)
        self.assertEqual(['f23ff00c-ec4f-412d-bd42-7f6e209819cb'],
                         sot.cluster_id)
        self.assertEqual(['ERROR'], sot.level)
        self.assertEqual(5, sot.limit)
        self.assertEqual('98625fd0-b120-416c-a978-2fbe28c46820', sot.marker)
        self.assertEqual('timestamp:asc', sot.sort)
        self.assertFalse(sot.project_safe)

    def test_event_list_request_body_default(self):
        sot = events.EventListRequest()
        sot.obj_set_defaults()
        self.assertTrue(sot.project_safe)


class TestEventGet(test_base.SenlinTestCase):

    body = {
        'identity': 'test-event'
    }

    def test_event_get_request(self):
        sot = events.EventListRequest(**self.body)
        self.assertEqual('test-event', sot.identity)
