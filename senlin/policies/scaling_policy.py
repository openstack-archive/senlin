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

from senlin.engine import cluster
from senlin.policies import base


class ScalingPolicy(base.PolicyBase):
    '''
    Policy for chaning the size of a cluster.

    This policy is expected to be enforced before the member list of a cluster
    is changed.
    '''

    TARGET = [
        ('BEFORE', 'CLUSTER', 'ADD_MEMBER'),
        ('BEFORE', 'CLUSTER', 'DEL_MEMBER'),
        ('WHEN', 'CLUSTER', 'ADD_MEMBER'),
        ('WHEN', 'CLUSTER', 'DEL_MEMBER'),
    ]

    PROFILE_TYPE = [
        'ANY',
    ]

    def __init__(self, name, type_name, **kwargs):
        super(ScalingPolicy, self).__init__(name, type_name, kwargs)

        self.min_size = kwargs.get('min_size')
        self.max_size = kwargs.get('max_size')
        self.adjustment_type = kwargs.get('adjustment_type')
        self.adjustment_number = kwargs.get('adjustment_number')

        # TODO: Make sure the default cooldown can be used if not specified 
        self.cooldown = kwargs.get('cooldown')

    def pre_op(self, cluster_id, action, **args):
        # TODO: get cluster size 
        # TODO: calculate new size
        # TODO: check if new size will break min_size or max_size constraints
        return True

    def enforce(self, cluster_id, action, **args):
        # calculate new size
        # create or delete members
        pass

    def post_op(self, cluster_id, action, **args):
        pass
