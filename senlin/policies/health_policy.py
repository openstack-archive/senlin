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


class HealthPolicy(base.PolicyBase):
    '''
    Policy for health checking for members of a cluster.
    '''
    
    CHECK_TYPES = (
        VM_LIFECYCLE_EVENTS,
        VM_STATUS_POLLING,
        LB_STATUS_POLLING,
    ) = (
        'vm_lifecycle_events',
        'vm_status_polling',
        'lb_status_polling',
    )

    TARGET = [
        ('AFTER', 'CLUSTER', 'ADD_MEMBER')
    ]

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
        pass

    def enforce(self, cluster_id, action, **args):
        pass

    def post_op(self, cluster_id, action, **args):
        # TODO(Qiming): subscribe to vm-lifecycle-events for the specified VM
        #               or add vm to the list of VM status polling
        pass
