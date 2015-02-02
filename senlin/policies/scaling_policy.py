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

from senlin.common import senlin_consts as consts
from senlin.db import api as db_api
from senlin.policies import base


class ScalingPolicy(base.Policy):
    '''Policy for chaning the size of a cluster.

    This policy is expected to be enforced before the member list of a cluster
    is changed.
    '''

    __type_name__ = 'ScalingPolicy'

    TARGET = [
        ('BEFORE', consts.CLUSTER_SCALE_UP),
        ('BEFORE', consts.CLUSTER_SCALE_DOWN),
    ]

    PROFILE_TYPE = [
        'ANY',
    ]

    def __init__(self, type_name, name, **kwargs):
        super(ScalingPolicy, self).__init__(type_name, name, **kwargs)

        self.min_size = self.spec.get('min_size')
        self.max_size = self.spec.get('max_size')
        self.adjustment_type = self.spec.get('adjustment_type')
        self.adjustment_number = self.spec.get('adjustment_number')

        # TODO(anyone): Make sure the default cooldown can be used if
        # not specified

    def pre_op(self, cluster_id, action, **kwargs):
        # TODO(anyone): get cluster size, calculate new size and return
        # count of nodes need to create or delete;
        # TODO(anyone): check if new size will break min_size or max_size
        # constraints
        data = kwargs.get('data')
        data['result'] = self.CHECK_SUCCEED

        adjustment = self.adjustment_number
        nodes = db_api.node_get_all_by_cluster(cluster_id)
        current_size = len(nodes)
        if current_size + adjustment > self.max_size:
            adjustment = self.max_size - current_size
        elif current_size + adjustment < self.min_size:
            adjustment = current_size - self.min_size

        data['count'] = adjustment

        return data

    def enforce(self, cluster_id, action, **kwargs):
        data = kwargs.get('data')

        # Mark this policy check succeeded
        data['result'] = self.CHECK_SUCCEED

        return data

    def post_op(self, cluster_id, action, **kwargs):
        data = kwargs.get('data')

        # Mark this policy check succeeded
        data['result'] = self.CHECK_SUCCEED

        return data
