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


class TestClusterActionCheck(base.BaseSenlinAPITest):

    def setUp(self):
        super(TestClusterActionCheck, self).setUp()
        profile_id = utils.create_a_profile(self)
        self.addCleanup(utils.delete_a_profile, self, profile_id)
        self.cluster_id = utils.create_a_cluster(self, profile_id,
                                                 desired_capacity=1)
        self.addCleanup(utils.delete_a_cluster, self, self.cluster_id)

    @decorators.idempotent_id('0d2063a8-b3d3-489d-b949-e2c61a0997ee')
    def test_cluster_action_check(self):
        params = {
            "check": {}
        }
        # Trigger cluster action
        res = self.client.trigger_action('clusters', self.cluster_id,
                                         params=params)

        # Verify resp code, body and location in headers
        self.assertEqual(202, res['status'])
        self.assertIn('actions', res['location'])

        action_id = res['location'].split('/actions/')[1]
        self.client.wait_for_status('actions', action_id, 'SUCCEEDED')


class TestClusterCheckNegativeInvalidParams(base.BaseSenlinAPITest):

    @decorators.idempotent_id('9a305b4f-2f05-4aa9-95ae-e08fd24b0593')
    def test_cluster_check_params_not_dict(self):
        params = {
            'check': ['k1', 'v1']
        }

        # Verify badrequest exception(400) is raised.
        ex = self.assertRaises(exceptions.BadRequest,
                               self.client.trigger_action,
                               'clusters', 'cluster_id', params)

        message = ex.resp_body['error']['message']
        self.assertEqual("[u'k1', u'v1'] is not of type 'object', 'null'",
                         str(message))


class TestClusterCheckNegativeNotFound(base.BaseSenlinAPITest):

    @decorators.idempotent_id('bbbe3feb-8482-4ae4-9c29-b4732efce931')
    def test_cluster_check_cluster_not_found(self):
        params = {
            'check': {'k1': 'v1'}
        }

        # Verify notfound exception(404) is raised.
        ex = self.assertRaises(exceptions.NotFound,
                               self.client.trigger_action, 'clusters',
                               'bbbe3feb-8482-4ae4-9c29-b4732efce931', params)

        message = ex.resp_body['error']['message']
        self.assertEqual("The cluster 'bbbe3feb-8482-4ae4-9c29-b4732efce931' "
                         "could not be found.", str(message))
