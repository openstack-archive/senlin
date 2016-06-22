# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

from tempest.lib import decorators

from senlin.tests.tempest.api import base
from senlin.tests.tempest.common import utils


class TestEventShow(base.BaseSenlinAPITest):

    def setUp(self):
        super(TestEventShow, self).setUp()
        profile_id = utils.create_a_profile(self)
        self.addCleanup(utils.delete_a_profile, self, profile_id)
        self.cluster_id = utils.create_a_cluster(self, profile_id)
        self.addCleanup(utils.delete_a_cluster, self, self.cluster_id)

    @decorators.idempotent_id('b23490a7-0ae2-44be-a1f9-9f2d82dfe6aa')
    def test_event_show(self):
        # Get cluster events
        events = self.client.list_objs('events',
                                       {'oid': self.cluster_id})['body']
        res = self.client.get_obj('events', events[0]['id'])

        # Verify resp of event list API
        self.assertEqual(200, res['status'])
        self.assertIsNone(res['location'])
        self.assertIsNotNone(res['body'])
        event = res['body']
        for key in ['action', 'cluster_id', 'id', 'level', 'oid',
                    'oname', 'otype', 'project', 'status',
                    'status_reason', 'timestamp', 'user']:
            self.assertIn(key, event)
