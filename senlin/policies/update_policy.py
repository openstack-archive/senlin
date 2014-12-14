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


class UpdatePolicy(base.PolicyBase):
    '''
    Policy for updating a cluster's node profile.

    Note that we differentiate the updates to the size(scale) of a cluster from
    the updates to the node profile.  The former is handled by CreatePolicy,
    DeletePolicy.
    '''

    TARGET = [
        ('WHEN', 'CLUSTER', 'UPDATE'),
    ]

    PROFILE_TYPE = [
        'ANY'
    ]

    def __init__(self, name, type_name, **kwargs):
        super(UpdatePolicy, self).__init__(name, type_name, **kwargs)

        self.min_in_service = kwargs.get('min_in_service')
        self.max_batch_size = kwargs.get('max_batch_size')
        self.pause_time = kwargs.get('pause_time')

    def pre_op(self, cluster_id, action, **args):
        # select candidates for update based on criteria
        return candidates

    def enforce(self, cluster_id, action, **args):
        pass

    def post_op(self, cluster_id, action, **args):
        pass
