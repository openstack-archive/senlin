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


class TestClusterActionScaleOut(base.BaseSenlinAPITest):

    def setUp(self):
        super(TestClusterActionScaleOut, self).setUp()
        profile_id = utils.create_a_profile(self)
        self.addCleanup(utils.delete_a_profile, self, profile_id)
        self.cluster_id = utils.create_a_cluster(self, profile_id)
        self.addCleanup(utils.delete_a_cluster, self, self.cluster_id)

    @decorators.idempotent_id('f15ff8cc-4be3-4c93-9979-6be428e83cd7')
    def test_cluster_action_scale_out(self):
        params = {
            "scale_out": {
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


class TestClusterScaleOutNegativeBadRequest(base.BaseSenlinAPITest):

    def setUp(self):
        super(TestClusterScaleOutNegativeBadRequest, self).setUp()
        profile_id = utils.create_a_profile(self)
        self.addCleanup(utils.delete_a_profile, self, profile_id)
        self.cluster_id = utils.create_a_cluster(self, profile_id,
                                                 min_size=0, max_size=5,
                                                 desired_capacity=1)
        self.addCleanup(utils.delete_a_cluster, self, self.cluster_id)

    @decorators.idempotent_id('2bbf6e0c-a8cc-4b29-8060-83652ffd6cd2')
    def test_cluster_scale_out_invalid_count(self):
        params = {
            "scale_out": {
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


class TestClusterScaleOutInvalidRequest(base.BaseSenlinAPITest):

    @decorators.idempotent_id('7aa3fd0c-c092-4a54-8dae-3814492101b0')
    def test_cluster_scale_out_invalid_count(self):
        params = {
            "scale_out": {
                "count": "bad-count"
            }
        }

        # Verify badrequest exception(400) is raised.
        ex = self.assertRaises(exceptions.BadRequest,
                               self.client.trigger_action,
                               'clusters', 'fake', params)

        message = ex.resp_body['error']['message']
        self.assertEqual(
            "invalid literal for int() with base 10: 'bad-count'",
            str(message))


class TestClusterScaleOutNegativeNotFound(base.BaseSenlinAPITest):

    @decorators.idempotent_id('b7038d95-204c-455f-a866-94dc535dd840')
    def test_cluster_scale_out_cluster_not_found(self):
        params = {
            "scale_out": {
                "count": 1
            }
        }

        # Verify notfound exception(404) is raised.
        ex = self.assertRaises(exceptions.NotFound,
                               self.client.trigger_action, 'clusters',
                               'b7038d95-204c-455f-a866-94dc535dd840',
                               params)

        message = ex.resp_body['error']['message']
        self.assertEqual(
            "The cluster 'b7038d95-204c-455f-a866-94dc535dd840' could "
            "not be found.", str(message))
