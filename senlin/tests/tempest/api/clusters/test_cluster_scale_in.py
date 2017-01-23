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
from tempest.lib import exceptions

from senlin.tests.tempest.api import base
from senlin.tests.tempest.common import utils


class TestClusterActionScaleIn(base.BaseSenlinAPITest):

    def setUp(self):
        super(TestClusterActionScaleIn, self).setUp()
        profile_id = utils.create_a_profile(self)
        self.addCleanup(utils.delete_a_profile, self, profile_id)
        self.cluster_id = utils.create_a_cluster(self, profile_id,
                                                 desired_capacity=1)
        self.addCleanup(utils.delete_a_cluster, self, self.cluster_id)

    @decorators.idempotent_id('a579cd01-8096-4bee-9978-d095025f605c')
    def test_cluster_action_scale_in(self):
        params = {
            "scale_in": {
                "count": "1"
            }
        }
        # Trigger cluster action
        res = self.client.trigger_action('clusters', self.cluster_id,
                                         params=params)

        # Verify resp code, body and location in headers
        self.assertEqual(202, res['status'])
        self.assertIn('actions', res['location'])

        action_id = res['location'].split('/actions/')[1]
        self.client.wait_for_status('actions', action_id, 'SUCCEEDED')


class TestClusterScaleInInvalidRequest(base.BaseSenlinAPITest):

    @decorators.idempotent_id('d826dc0f-ef1c-47ee-b31f-3042aaa8ec54')
    def test_cluster_scale_in_invalid_count(self):
        params = {
            "scale_in": {
                "count": "bad-count"
            }
        }

        # Verify badrequest exception(400) is raised.
        ex = self.assertRaises(exceptions.BadRequest,
                               self.client.trigger_action,
                               'clusters', 'fake', params)

        message = ex.resp_body['error']['message']
        self.assertEqual(
            "The value for count must be an integer: 'bad-count'.",
            str(message))


class TestClusterScaleInNegativeBadRequest(base.BaseSenlinAPITest):

    def setUp(self):
        super(TestClusterScaleInNegativeBadRequest, self).setUp()
        profile_id = utils.create_a_profile(self)
        self.addCleanup(utils.delete_a_profile, self, profile_id)
        self.cluster_id = utils.create_a_cluster(self, profile_id,
                                                 min_size=0, max_size=5,
                                                 desired_capacity=1)
        self.addCleanup(utils.delete_a_cluster, self, self.cluster_id)

    @decorators.idempotent_id('337a8a8f-a368-4d4f-949a-8b116dbb6a75')
    def test_cluster_scale_in_invalid_count(self):
        params = {
            "scale_in": {
                "count": -1
            }
        }

        # Verify badrequest exception(400) is raised.
        ex = self.assertRaises(exceptions.BadRequest,
                               self.client.trigger_action,
                               'clusters', self.cluster_id, params)

        message = ex.resp_body['error']['message']
        self.assertEqual("Value must be >= 0 for field 'count'.",
                         str(message))


class TestClusterScaleInNegativeNotFound(base.BaseSenlinAPITest):

    @decorators.idempotent_id('0124c7de-66d0-4a84-9c8f-80bc4d246b79')
    def test_cluster_scale_in_cluster_not_found(self):
        params = {
            "scale_in": {
                "count": 1
            }
        }

        # Verify notfound exception(404) is raised.
        ex = self.assertRaises(exceptions.NotFound,
                               self.client.trigger_action, 'clusters',
                               '0124c7de-66d0-4a84-9c8f-80bc4d246b79',
                               params)

        message = ex.resp_body['error']['message']
        self.assertEqual(
            "The cluster '0124c7de-66d0-4a84-9c8f-80bc4d246b79' could "
            "not be found.", str(message))
