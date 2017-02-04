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

from datetime import timedelta
import testtools

from oslo_utils import timeutils

from senlin.objects import cluster_policy as cpo

CLUSTER_ID = "8286fcaa-6474-44e2-873e-28b5cb2c204c"
POLICY_ID = "da958a16-f384-49a1-83a9-abac8b4ec46e"


class TestClusterPolicy(testtools.TestCase):

    def test_cooldown_inprogress(self):
        last_op = timeutils.utcnow(True)
        cp = cpo.ClusterPolicy(cluster_id=CLUSTER_ID, policy_id=POLICY_ID,
                               last_op=last_op)

        res = cp.cooldown_inprogress(60)

        self.assertTrue(res)

        cp.last_op -= timedelta(hours=1)

        res = cp.cooldown_inprogress(60)

        self.assertFalse(res)
