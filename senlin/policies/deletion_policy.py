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

'''
Policy for deleting node(s) from a cluster.
'''

'''
NOTE: How deletion policy works
Input:
  cluster: cluster whose nodes can be deleted
  policy_data.deletion:
    - count: number of nodes to delete; it can be customized by a
             scaling policy for example. If no scaling policy is in
             effect, deletion count is assumed to be 1
  self.criteria: list of criteria for sorting nodes
Output: policy_data
  {
    'status': 'OK',
    'deletion': {
      'count': '2',
      'candidates': [
        'node-id-1',
        'node-id-2'
      ],
      'destroy_after_delete': 'True',
    }
  }
'''

import random

from senlin.common import consts
from senlin.db import api as db_api
from senlin.policies import base


class DeletionPolicy(base.Policy):

    __type_name__ = 'DeletionPolicy'

    CRITERIA = (
        OLDEST_FIRST,
        OLDEST_PROFILE_FIRST,
        YOUNGEST_FIRST,
        RANDOM,
    ) = (
        'OLDEST_FIRST',
        'OLDEST_PROFILE_FRIST',
        'YOUNGEST_FIRST',
        'random',
    )

    TARGET = [
        ('BEFORE', consts.CLUSTER_SCALE_IN),
        ('BEFORE', consts.CLUSTER_DEL_NODES),
    ]

    PROFILE_TYPE = [
        'ANY'
    ]

    def __init__(self, type_name, name, **kwargs):
        super(DeletionPolicy, self).__init__(type_name, name, **kwargs)

        self.criteria = kwargs.get('criteria', self.RANDOM)
        self.grace_period = kwargs.get('grace_period', 0)
        self.destroy_after_deletion = kwargs.get('destroy_after_deletion',
                                                 True)
        self.reduce_desired_capacity = kwargs.get('reduce_desired_capacity',
                                                  False)
        random.seed()

    def _select_candidates(self, context, cluster_id, count):
        candidates = []
        nodes = db_api.node_get_all_by_cluster(context, cluster_id)
        if count > len(nodes):
            count = len(nodes)

        # Random selection
        if self.criteria == self.RANDOM:
            i = count
            while i > 0:
                rand = random.randrange(i)
                candidates.append(nodes[rand])
                nodes.remove(nodes[rand])
                i = i - 1

            return candidates

        # Node age based selection
        if self.criteria in [self.OLDEST_FIRST, self.YOUNGEST_FIRST]:
            sorted_list = sorted(nodes, key=lambda r: (r.created_time, r.name))
            for i in range(count):
                if self.criteria == self.OLDEST_FIRST:
                    candidates.append(sorted_list[i])
                else:  # YOUNGEST_FIRST
                    candidates.append(sorted_list[-i])
            return candidates

        # Node profile based selection
        if self.criterial == self.OLDEST_PROFILE_FIRST:
            map = []
            for node in nodes:
                created_at = db_api.profile_get(node.profile_id).created_time
                map.append({'id': node.id, 'created_at': created_at})
            sorted_map = sorted(map, key=lambda m: m['created_at'])
            for i in range(count):
                candidates.append(sorted_map[i])

            return candidates

        return []

    def pre_op(self, cluster_id, action, policy_data):
        '''Choose victims that can be deleted.'''

        pd = policy_data.get('deletion', None)
        if pd is not None:
            count = pd.get('count', 1)
            candidates = pd.get('candidates', [])
        else:
            count = 1
            candidates = []

        # For certain operations ( e.g. DEL_NODES), the candidates might
        # have been specified
        if len(candidates) == 0:
            candidates = self._select_candidates(action.context, cluster_id,
                                                 count)
        pd['candidates'] = candidates
        pd['destroy_after_deletion'] = self.destroy_after_deletion
        pd['grace_period'] = self.grace_period
        policy_data.update({'deletion': pd})
        return policy_data
