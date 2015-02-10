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


class PlacementPolicy(base.Policy):
    '''Policy for placing members of a cluster.

    This policy is expected to be enforced before new member(s) added to an
    existing cluster.
    '''

    __type_name__ = 'PlacementPolicy'

    TARGET = [
        ('BEFORE', consts.CLUSTER_SCALE_OUT),
    ]

    PROFILE_TYPE = [
        'os.nova.server',
        'aws.autoscaling.launchconfig',
    ]

    def __init__(self, type_name, name, **kwargs):
        super(PlacementPolicy, self).__init__(type_name, name, kwargs)

        self.regions = self.spec.get('regions')
        self.AZs = self.spec.get('AZs')

    def pre_op(self, cluster_id, action, **args):
        # TODO(anyone): calculate available AZs and or regions
        return True

    def enforce(self, cluster_id, action, **kwargs):
        # we expect kwargs to carry node profile information before the node
        # is created.
        # TODO(anyone): modify node's scheduler hints and return them
        return True

    def post_op(self, cluster_id, action, **kwargs):
        pass
