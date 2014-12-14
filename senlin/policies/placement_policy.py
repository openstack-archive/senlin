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

from senlin.policies import base


class PlacementPolicy(base.PolicyBase):
    '''
    Policy for placing members of a cluster.

    This policy is expected to be enforced before new member(s) added to an
    existing cluster.
    '''

    TARGET = [
        ('BEFORE', 'CLUSTER', 'ADD_MEMBER'),
    ]

    PROFILE_TYPE = [
        'os.nova.server',
        'aws.autoscaling.launchconfig',
    ]

    def __init__(self, name, type_name, **kwargs):
        super(PlacementPolicy, self).__init__(name, type_name, kwargs)

        self.regions = kwargs.get('regions')
        self.AZs = kwargs.get('AZs')

    def pre_op(self, cluster_id, action, **args):
        # calculate available AZs and or regions 
        return True

    def enforce(self, cluster_id, action, **args):
        # modify member's scheduler hints
        return True

    def post_op(self, cluster_id, action, **args):
        pass
