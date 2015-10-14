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
Policy for deleting node(s) from a cluster.

NOTE: How deletion policy works
Input:
  cluster: cluster whose nodes can be deleted
  action.data['deletion']:
    - count: number of nodes to delete; it can be customized by a
             scaling policy for example. If no scaling policy is in
             effect, deletion count is assumed to be 1
  self.criteria: list of criteria for sorting nodes
Output: stored in action.data
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
"""

import random

from senlin.common import constraints
from senlin.common import consts
from senlin.common.i18n import _
from senlin.common import scaleutils
from senlin.common import schema
from senlin.db import api as db_api
from senlin.policies import base


class DeletionPolicy(base.Policy):
    '''Policy for choosing victim node(s) from a cluster for deletion.

    This policy is enforced when nodes are to be removed from a cluster.
    It will yield an ordered list of candidates for deletion based on user
    specified criteria.
    '''

    VERSION = '1.0'

    KEYS = (
        CRITERIA, DESTROY_AFTER_DELETION, GRACE_PERIOD,
        REDUCE_DESIRED_CAPACITY,
    ) = (
        'criteria', 'destroy_after_deletion', 'grace_period',
        'reduce_desired_capacity',
    )

    CRITERIA_VALUES = (
        OLDEST_FIRST, OLDEST_PROFILE_FIRST, YOUNGEST_FIRST, RANDOM,
    ) = (
        'OLDEST_FIRST', 'OLDEST_PROFILE_FRIST', 'YOUNGEST_FIRST', 'RANDOM',
    )

    TARGET = [
        ('BEFORE', consts.CLUSTER_SCALE_IN),
        ('BEFORE', consts.CLUSTER_DEL_NODES),
        ('BEFORE', consts.CLUSTER_RESIZE),
    ]

    PROFILE_TYPE = [
        'ANY'
    ]

    properties_schema = {
        CRITERIA: schema.String(
            _('Criteria used in selecting candidates for deletion'),
            default=RANDOM,
            constraints=[
                constraints.AllowedValues(CRITERIA_VALUES),
            ]
        ),
        DESTROY_AFTER_DELETION: schema.Boolean(
            _('Whethere a node should be completely destroyed after '
              'deletion. Default to True'),
            default=True,
        ),
        GRACE_PERIOD: schema.Integer(
            _('Number of seconds before real deletion happens.'),
            default=0,
        ),
        REDUCE_DESIRED_CAPACITY: schema.Boolean(
            _('Whether the desired capacity of the cluster should be '
              'reduced along the deletion. Default to False.'),
            default=False,
        )
    }

    def __init__(self, name, spec, **kwargs):
        super(DeletionPolicy, self).__init__(name, spec, **kwargs)

        self.criteria = self.properties[self.CRITERIA]
        self.grace_period = self.properties[self.GRACE_PERIOD]
        self.destroy_after_deletion = self.properties[
            self.DESTROY_AFTER_DELETION]
        self.reduce_desired_capacity = self.properties[
            self.REDUCE_DESIRED_CAPACITY]
        random.seed()

    def _select_candidates(self, context, cluster_id, count):
        candidates = []
        nodes = db_api.node_get_all_by_cluster(context, cluster_id)
        if count > len(nodes):
            count = len(nodes)

        err_nodes = [n for n in nodes if n.status == 'ERROR']
        nodes = [n for n in nodes if n.status != 'ERROR']
        if count <= len(err_nodes):
            return [n.id for n in err_nodes[:count]]

        candidates.extend([n.id for n in err_nodes])
        count -= len(err_nodes)

        # Random selection
        if self.criteria == self.RANDOM:
            i = count
            while i > 0:
                rand = random.randrange(i)
                candidates.append(nodes[rand].id)
                nodes.remove(nodes[rand])
                i = i - 1

            return candidates

        # Node age based selection
        if self.criteria in [self.OLDEST_FIRST, self.YOUNGEST_FIRST]:
            sorted_list = sorted(nodes, key=lambda r: (r.created_time, r.name))
            for i in range(count):
                if self.criteria == self.OLDEST_FIRST:
                    candidates.append(sorted_list[i].id)
                else:  # YOUNGEST_FIRST
                    candidates.append(sorted_list[-1-i].id)
            return candidates

        # Node profile based selection
        node_map = []
        for node in nodes:
            profile = db_api.profile_get(context, node.profile_id)
            created_at = profile.created_time
            node_map.append({'id': node.id, 'created_at': created_at})
        sorted_map = sorted(node_map, key=lambda m: m['created_at'])
        for i in range(count):
            candidates.append(sorted_map[i]['id'])

        return candidates

    def pre_op(self, cluster_id, action):
        '''Choose victims that can be deleted.'''

        if action.action == consts.CLUSTER_RESIZE:
            cluster = db_api.cluster_get(action.context, cluster_id)
            scaleutils.parse_resize_params(action, cluster)
            if 'deletion' not in action.data:
                return
            count = action.data['deletion']['count']
        else:  # CLUSTER_SCALE_IN or CLUSTER_DEL_NODES
            count = action.inputs.get('count', 1)
        candidates = action.inputs.get('candidates', [])

        # For CLUSTER_RESIZE and CLUSTER_SCALE_IN actions, use policy
        # creteria to selete candidates.
        if len(candidates) == 0:
            candidates = self._select_candidates(action.context, cluster_id,
                                                 count)
        pd = action.data.get('deletion', {})
        pd['candidates'] = candidates
        pd['destroy_after_deletion'] = self.destroy_after_deletion
        pd['grace_period'] = self.grace_period
        action.data.update({
            'status': base.CHECK_OK,
            'reason': _('Candidates generated'),
            'deletion': pd
        })
        action.store(action.context)

        return
