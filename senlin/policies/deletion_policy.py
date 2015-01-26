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

import random

from senlin.common import senlin_consts as consts
from senlin.db import api as db_api
from senlin.policies import base


class DeletionPolicy(base.Policy):
    '''
    Policy for deleting member(s) from a cluster.
    '''

    __type_name__ = 'DeletionPolicy'

    CRITERIA = (
        OLDEST_FIRST, YOUNGEST_FIRST, RANDOM,
    ) = (
        'oldest_first',
        'youngest_first',
        'random',
    )

    TARGET = [
        ('BEFORE', consts.CLUSTER_SCALE_DOWN),
        ('BEFORE', consts.CLUSTER_DEL_NODES),
    ]

    PROFILE_TYPE = [
        'ANY'
    ]

    def __init__(self, type_name, name, **kwargs):
        super(DeletionPolicy, self).__init__(type_name, name, **kwargs)

        self.criteria = kwargs.get('criteria', '')
        self.grace_period = kwargs.get('grace_period', 0)
        self.reduce_desired_capacity = kwargs.get('reduce_desired_capacity',
                                                  False)
        random.seed()

    def pre_op(self, cluster_id, action, **kwargs):
        '''
        The pre-op of a deletion policy returns the chosen victims
        that will be deleted.
        '''
        data = kwargs.get('data')
        data['result'] = self.CHECK_SUCCEED

        if 'count' not in data:
            # We need input from scaling policy,
            # let's retry
            data['result'] = self.CHECK_RETRY
            return data

        data['candidates'] = []
        count = kwargs.get('count')
        if count == 0:
            # No candidates is choosen for deletion
            return data

        nodes = db_api.node_get_all_by_cluster(cluster_id)
        # TODO(anyone): Add count check to ensure it is not larger
        # then the current size of cluster.
        if count > len(nodes):
            count = len(nodes)

        if self.criteria == self.RANDOM:
            for i in range(1, count):
                rand = random.randrange(len(nodes))
                data['candidates'].append(nodes[rand])
                nodes.remove(nodes[rand])
            return data

        sorted_list = sorted(nodes, key=lambda r: (r.created_time, r.name))
        for i in range(1, count):
            if self.criteria == self.OLDEST_FIRST:
                data['candidates'].append(sorted_list[i - 1])
            else:  # self.criteria == self.YOUNGEST_FIRST:
                data['candidates'].append(sorted_list[-i])

        return data

    def enforce(self, cluster_id, action, **kwargs):
        data = kwargs.get('data')

        # Mark this policy check succeeded
        data['result'] = self.CHECK_SUCCEED

        return data

    def post_op(self, cluster_id, action, **kwargs):
        # TODO(Qiming): process grace period here if needed
        data = kwargs.get('data')

        # Mark this policy check succeeded
        data['result'] = self.CHECK_SUCCEED

        return data
