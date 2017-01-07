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
Policy for batching operations on a cluster.

NOTE: How update policy works

Input:
   cluster: the cluster whose nodes are to be updated.
Output:
   stored in action.data: A dictionary containing a detailed update schedule.
   {
     'status': 'OK',
     'update': {
       'pause_time': 2,
       'plan': [{
           'node-id-1',
           'node-id-2',
         }, {
           'node-id-3',
           'node-id-4',
         }, {
           'node-id-5',
         }
       ]
     }
   }
"""
import math

from senlin.common import consts
from senlin.common.i18n import _
from senlin.common import scaleutils as su
from senlin.common import schema
from senlin.engine import cluster as cm
from senlin.objects import node as no
from senlin.policies import base


class BatchPolicy(base.Policy):
    """Policy for batching the operations on a cluster's nodes."""

    VERSION = '1.0'
    VERSIONS = {
        '1.0': [
            {'status': consts.EXPERIMENTAL, 'since': '2017.02'}
        ]
    }
    PRIORITY = 200

    TARGET = [
        ('BEFORE', consts.CLUSTER_UPDATE),
        ('BEFORE', consts.CLUSTER_DELETE),
    ]

    PROFILE_TYPE = [
        'ANY'
    ]

    KEYS = (
        MIN_IN_SERVICE, MAX_BATCH_SIZE, PAUSE_TIME,
    ) = (
        'min_in_service', 'max_batch_size', 'pause_time',
    )

    properties_schema = {
        MIN_IN_SERVICE: schema.Integer(
            _('Minimum number of nodes in service when performing updates.'),
            default=1,
        ),
        MAX_BATCH_SIZE: schema.Integer(
            _('Maximum number of nodes that can be updated at the same '
              'time.'),
            default=-1,
        ),
        PAUSE_TIME: schema.Integer(
            _('Number of seconds between update batches if any.'),
            default=60,
        )
    }

    def __init__(self, name, spec, **kwargs):
        super(BatchPolicy, self).__init__(name, spec, **kwargs)

        self.min_in_service = self.properties[self.MIN_IN_SERVICE]
        self.max_batch_size = self.properties[self.MAX_BATCH_SIZE]
        self.pause_time = self.properties[self.PAUSE_TIME]

    def _cal_batch_size(self, total, action_name):
        batch_num = 0
        batch_size = 0
        diff = 0

        # if the action is CLUSTER_DELETE or number of nodes less than
        # min_in_service, we divided it to 2 batches
        diff = int(math.ceil(float(total) / 2))
        if (action_name == consts.CLUSTER_UPDATE and
                total > self.min_in_service):
            diff = total - self.min_in_service

        # max_batch_size is -1 if not specified
        if self.max_batch_size == -1 or diff < self.max_batch_size:
            batch_size = diff
        else:
            batch_size = self.max_batch_size

        batch_num = int(math.ceil(float(total) / float(batch_size)))

        return batch_size, batch_num

    def _pick_nodes(self, batch_size, batch_num, candidates, good):
        """Select nodes based on size and number of batches.

        :param batch_size: the number of nodes of each batch.
        :param batch_num: the number of batches.
        :param candidates: a list of IDs for 'ERROR' nodes.
        :param good: a list of active node objects.
        :returns: a list of sets containing the nodes' IDs we
                  selected based on the input params.
        """

        nodes_list = []
        # NOTE: we leave the nodes known to be good (ACTIVE)
        # at the end of the list so that we have a better
        # chance to ensure 'min_in_service' constraint
        for node in good:
            candidates.append(node.id)

        for start in range(0, len(candidates), batch_size):
            end = start + batch_size
            nodes_list.append(set(candidates[start:end]))

        return nodes_list

    def _create_plan(self, cluster, action):
        current = no.Node.count_by_cluster(action.context, cluster.id)
        action_name = action.action
        plan_list = [{}]
        plan = {
            'pause_time': self.pause_time,
        }
        if current == 0:
            if action_name == consts.CLUSTER_UPDATE:
                plan['plan'] = plan_list
                return True, plan
            else:
                plan['batch_size'] = 0
                return True, plan

        batch_size, batch_num = self._cal_batch_size(current, action_name)
        if action_name == consts.CLUSTER_DELETE:
            plan['batch_size'] = batch_size
            return True, plan

        nodes_list = cluster.nodes
        bad_list, good_list = su.filter_error_nodes(nodes_list)
        plan_list = self._pick_nodes(batch_size, batch_num, bad_list,
                                     good_list)
        plan['plan'] = plan_list

        return True, plan

    def pre_op(self, cluster_id, action):
        cluster = cm.Cluster.load(action.context, cluster_id)
        pd = {
            'status': base.CHECK_OK,
            'reason': _('Batching request validated.'),
        }
        # for updating and deleting
        result, value = self._create_plan(cluster, action)

        if result is False:
            pd = {
                'status': base.CHECK_ERROR,
                'reason': value,
            }
        else:
            if action.action == consts.CLUSTER_UPDATE:
                pd['update'] = value
            else:
                pd['delete'] = value

        action.data.update(pd)
        action.store(action.context)

        return
