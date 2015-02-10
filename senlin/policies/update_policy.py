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

from senlin.common import consts
from senlin.policies import base


class UpdatePolicy(base.Policy):
    '''Policy for updating a cluster's node profile.

    Note that we differentiate the updates to the size(scale) of a cluster from
    the updates to the node profile.  The former is handled by CreatePolicy,
    DeletePolicy.
    '''

    __type_name__ = 'UpdatePolicy'

    TARGET = [
        ('WHEN', consts.CLUSTER_UPDATE),
    ]

    PROFILE_TYPE = [
        'ANY'
    ]

    def __init__(self, type_name, name, **kwargs):
        super(UpdatePolicy, self).__init__(type_name, name, **kwargs)

        self.min_in_service = self.spec.get('min_in_service')
        self.max_batch_size = self.spec.get('max_batch_size')
        self.pause_time = self.spec.get('pause_time')

    def pre_op(self, cluster_id, action, policy_data):
        # TODO(anyone): compute batches
        policy_data['candidates'] = candidates
        return True

    def enforce(self, cluster_id, action, policy_data):
        return candidates

    def post_op(self, cluster_id, action, policy_data):
        # TODO(anyone): handle pause_time here
        return True
