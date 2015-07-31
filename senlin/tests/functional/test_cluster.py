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

from oslo_log import log as logging

from senlin.tests.functional import base

LOG = logging.getLogger(__name__)


class TestCluster(base.SenlinFunctionalTest):

    def test_get_clusters(self):
        # Check that listing clusters works.
        rel_url = 'clusters'
        status = [200]
        resp = self.client.api_request('GET', rel_url,
                                       expected_resp_status=status)
        clusters = resp.body['clusters']
        self.assertEqual([], clusters)
