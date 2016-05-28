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
from senlin.tests.tempest.api import utils
from senlin.tests.tempest.common import constants


class TestEventList(base.BaseSenlinTest):

    @classmethod
    def resource_setup(cls):
        super(TestEventList, cls).resource_setup()
        cls.profile = cls.create_profile(constants.spec_nova_server)
        cls.cluster = utils.create_a_cluster(cls, cls.profile['id'])

    @classmethod
    def resource_cleanup(cls):
        # Delete test cluster
        cls.delete_test_cluster(cls.cluster['id'])
        # Delete profile
        cls.client.delete_obj('profiles', cls.profile['id'])
        super(TestEventList, cls).resource_cleanup()

    @decorators.idempotent_id('498a7e22-7ada-415b-a7cf-927b0ad3d9f6')
    def test_list_event(self):
        res = self.client.list_objs('events')

        # Verify resp of event list API
        self.assertEqual(200, res['status'])
        self.assertIsNone(res['location'])
        self.assertIsNotNone(res['body'])
        events = res['body']
        for event in events:
            for key in ['action', 'cluster_id', 'id', 'level', 'obj_id',
                        'obj_name', 'obj_type', 'project', 'status',
                        'status_reason', 'timestamp', 'user']:
                self.assertIn(key, event)
