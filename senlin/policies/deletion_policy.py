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

from senlin.db import api as db_api
from senlin.policies import base


class DeletePolicy(base.PolicyBase):
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
        ('CLUSTER', 'DELETE_MEMBER'),
    ]

    PROFILE_TYPE = [
        'ANY'
    ]

    def __init__(self, name, type_name, **kwargs):
        super(DeletePolicy, self).__init__(name, type_name, kwargs)

        self.criteria = kwargs.get('criteria')

    def _sort_members_by_creation_time(members):
        # TODO: do sorting
        return members

    def pre_op(self, cluster_id, action, **args):
        # TODO: choose victims from the given cluster
        members = db_api.get_members(cluster_id)
        sorted = self._sort_members_by_creation_time(members)
        if self.criteria == self.OLDEST_FIRST:
            victim = sorted[0]
        elif self.criteria ==self.YOUNGEST_FIRST:
            victim = sorted[-1]
        else:
            rand = random(len(softed)
            victim = sorted[rand]
        return victim

    def enforce(self, cluster_id, action, **args):
        pass 

    def post_op(self, cluster_id, action, **args):
        pass
