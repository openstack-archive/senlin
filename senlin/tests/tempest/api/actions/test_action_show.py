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


class TestActionShow(base.BaseSenlinTest):

    @classmethod
    def resource_setup(cls):
        super(TestActionShow, cls).resource_setup()
        cls.profile_id = utils.create_a_profile(cls)
        params = {
            'cluster': {
                'profile_id': cls.profile_id,
                'desired_capacity': 0,
                'min_size': 0,
                'max_size': -1,
                'timeout': None,
                'metadata': {},
                'name': 'test-cluster-action-show'
            }
        }
        res = cls.client.create_obj('clusters', params)
        cls.action_id = res['location'].split('/actions/')[1]
        cls.cluster_id = res['body']['id']
        cls.wait_for_status('actions', cls.action_id, 'SUCCEEDED')

    @classmethod
    def resource_cleanup(cls):
        utils.delete_a_cluster(cls, cls.cluster_id)
        utils.delete_a_profile(cls, cls.profile_id)
        super(TestActionShow, cls).resource_cleanup()

    @decorators.idempotent_id('c6376f60-8f52-4384-8b6d-57df264f2e23')
    def test_action_show(self):
        res = self.client.get_obj('actions', self.action_id)

        self.assertEqual(200, res['status'])
        self.assertIsNone(res['location'])
        self.assertIsNotNone(res['body'])

        action = res['body']
        for key in ['action', 'cause', 'created_at', 'data',
                    'depended_by', 'depends_on', 'end_time', 'id',
                    'inputs', 'interval', 'name', 'outputs', 'owner',
                    'start_time', 'status', 'status_reason', 'target',
                    'timeout', 'updated_at']:
            self.assertIn(key, action)
