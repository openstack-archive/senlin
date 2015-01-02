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

    CRITERIA = (
        OLDEST_FIRST, YOUNGEST_FIRST, RANDOM,
    ) = (
        'oldest_first',
        'youngest_first',
        'random',
    )

    TARGET = [
        ('WHEN', consts.CLUSTER_SCALE_DOWN),
        ('AFTER', consts.CLUSTER_DEL_NODES),
        ('AFTER', consts.CLUSTER_SCALE_DOWN),
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

    def pre_op(self, cluster_id, action, **args):
        '''
        We don't block the deletion anyhow.
        '''
        return True

    def enforce(self, cluster_id, action, **args):
        '''
        The enforcement of a deletion policy returns the chosen victims
        that will be deleted.
        '''
        nodes = db_api.node_get_all_by_cluster_id(cluster_id)
        if self.criteria == self.RANDOM:
            rand = random.randrange(len(nodes))
            return nodes[rand]

        sorted_list = sorted(nodes, key=lambda r: (r.created_time, r.name))
        if self.criteria == self.OLDEST_FIRST:
            victim = sorted_list[0]
        else:  # self.criteria == self.YOUNGEST_FIRST:
            victim = sorted_list[-1]

        return victim

    def post_op(self, cluster_id, action, **args):
        # TODO(Qiming): process grace period here if needed
        pass
