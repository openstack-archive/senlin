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

from senlin.common import senlin_consts as consts
from senlin.policies import base


class HealthPolicy(base.Policy):
    '''Policy for health checking for members of a cluster.'''

    __type_name__ = 'HealthPolicy'

    CHECK_TYPES = (
        VM_LIFECYCLE_EVENTS,
        VM_STATUS_POLLING,
        LB_STATUS_POLLING,
    ) = (
        'VM_LIFECYCLE_EVENTS',
        'NODE_STATUS_POLLING',
        'LB_STATUS_POLLING',
    )

    TARGET = [
        ('AFTER', consts.CLUSTER_ADD_NODES),
        ('AFTER', consts.CLUSTER_SCALE_OUT),
        ('BEFORE', consts.CLUSTER_DEL_NODES),
        ('BEFORE', consts.CLUSTER_SCALE_IN),
    ]

    # Should be ANY if profile provides
    # health check support?
    PROFILE_TYPE = [
        'os.nova.server',
        'AWS.AutoScaling.LaunchConfiguration',
    ]

    def __init__(self, type_name, name, **kwargs):
        super(HealthPolicy, self).__init__(type_name, name, kwargs)

        self.interval = self.spec.get('interval')
        self.grace_period = self.spec.get('grace_period')
        self.check_type = self.spec.get('check_type')

    def pre_op(self, cluster_id, action, **args):
        # Ignore actions that are not required to be processed at this stage
        if action not in (consts.CLUSTER_SCALE_IN,
                          consts.CLUSTER_DEL_NODES):
            return True

        # TODO(anyone): Unsubscribe nodes from backend health monitoring
        #               infrastructure
        return True

    def enforce(self, cluster_id, action, **args):
        pass

    def post_op(self, cluster_id, action, **args):
        # Ignore irrelevant action here
        if action not in (consts.CLUSTER_SCALE_OUT,
                          consts.CLUSTER_ADD_NODES):
            return True

        # TODO(anyone): subscribe to vm-lifecycle-events for the specified VM
        #                or add vm to the list of VM status polling
        return True
