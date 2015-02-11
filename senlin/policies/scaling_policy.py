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

from senlin.common import consts
from senlin.db import api as db_api
from senlin.policies import base


class ScalingPolicy(base.Policy):
    '''Policy for changing the size of a cluster.

    This policy is expected to be enforced before the node list of a cluster
    is changed.
    '''

    __type_name__ = 'ScalingPolicy'

    TARGET = [
        ('BEFORE', consts.CLUSTER_SCALE_OUT),
        ('BEFORE', consts.CLUSTER_SCALE_IN),
    ]

    PROFILE_TYPE = [
        'ANY',
    ]

    def __init__(self, type_name, name, **kwargs):
        super(ScalingPolicy, self).__init__(type_name, name, **kwargs)

        self.min_size = self.spec.get('min_size')
        self.max_size = self.spec.get('max_size')
        adjustment = self.spec.get('adjustment')
        if adjustment is not None:
            self.adjustment_type = adjustment.get('type')
            self.adjustment_number = adjustment.get('number')
        else:
            self.adjustment_type = self.DEFAULT_TYPE
            self.adjustment_number = self.DEFAULT_NUMBER

        self.min_step = self.spec.get('min_step')

        # TODO(anyone): Make sure the default cooldown can be used if
        # not specified

    def pre_op(self, cluster_id, action, policy_data):
        # TODO(anyone): get cluster size, calculate new size and return
        # count of nodes need to create or delete;
        # TODO(anyone): check if new size will break min_size or max_size
        # constraints
        policy_data['status'] = self.CHECK_OK
        adjustment = self.adjustment_number
        nodes = db_api.node_get_all_by_cluster(cluster_id)
        current_size = len(nodes)
        if current_size + adjustment > self.max_size:
            adjustment = self.max_size - current_size
        elif current_size + adjustment < self.min_size:
            adjustment = current_size - self.min_size

        pd = {'count': adjustment}
        if action == consts.CLUSTER_SCALE_OUT:
            policy_data['placement'] = pd
        elif action == consts.CLUSTER_SCALE_IN:
            policy_data['deletion'] = pd

        return policy_data
