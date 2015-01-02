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
from senlin.policies import base


class ScalingPolicy(base.Policy):
    '''
    Policy for chaning the size of a cluster.

    This policy is expected to be enforced before the member list of a cluster
    is changed.
    '''

    TARGET = [
        ('BEFORE', consts.CLUSTER_ADD_NODES),
        ('BEFORE', consts.CLUSTER_DEL_NODES),
        ('BEFORE', consts.CLUSTER_SCALE_UP),
        ('BEFORE', consts.CLUSTER_SCALE_DOWN),
        ('WHEN', consts.CLUSTER_ADD_NODES),
        ('WHEN', consts.CLUSTER_DEL_NODES),
        ('WHEN', consts.CLUSTER_SCALE_UP),
        ('WHEN', consts.CLUSTER_SCALE_DOWN),
        ('AFTER', consts.CLUSTER_SCALE_UP),
        ('AFTER', consts.CLUSTER_SCALE_DOWN),
        ('AFTER', consts.CLUSTER_ADD_NODES),
        ('AFTER', consts.CLUSTER_DEL_NODES),
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

    def pre_op(self, cluster_id, action, **args):
        # TODO(anyone): get cluster size, calculate new size
        # TODO(anyone): check if new size will break min_size or max_size
        # constraints
        return True

    def enforce(self, cluster_id, action, **kwargs):
        # if action in (consts.CLUSTER_SCALE_UP, consts.CLUSTER_SCALE_DOWN):
        #     amount = get_adjustment(action)

        # TODO(anyone): return new nodes to be added/removed.
        pass

    def post_op(self, cluster_id, action, **kwargs):
        return True
