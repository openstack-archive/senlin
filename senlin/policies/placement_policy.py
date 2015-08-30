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

"""
Policy for placing nodes across AZs and/or regions.

NOTE: How placement policy works
Input:
  cluster: cluster whose nodes are to be manipulated.
  action.data['placement']:
    - count: number of nodes to create; it can be decision from a scaling
             policy. If no scaling policy is in effect, the count will be
             assumed to be 1.
Output:
  stored in action.data: A dictionary containing scheduling decisions made.
  {
    'status': 'OK',
    'placement': {
      'count': 2,
      'placements': [
        {
          'AZ': 'nova-1',
          'region': 'RegionOne',
        },
        {
          'AZ': 'nova-2',
          'region': 'RegionTwo',
        }
      ]
    }
  }
"""

from senlin.common import consts
from senlin.policies import base


class PlacementPolicy(base.Policy):
    '''Policy for placing members of a cluster.

    This policy is expected to be enforced before new member(s) added to an
    existing cluster.
    '''

    VERSION = '1.0'

    TARGET = [
        ('BEFORE', consts.CLUSTER_SCALE_OUT),
    ]

    PROFILE_TYPE = [
        'os.nova.server',
    ]

    properties_schema = {
    }

    def __init__(self, name, spec, **kwargs):
        super(PlacementPolicy, self).__init__(name, spec, **kwargs)

        self.regions = self.properties.get('regions')
        self.AZs = self.properties.get('availability_zones')

    def pre_op(self, cluster_id, action):
        '''Call back when new nodes are created for a cluster.'''
        # TODO(anyone): calculate available AZs and or regions
        return
