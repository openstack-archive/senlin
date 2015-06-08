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

from senlin.common import constraints
from senlin.common import consts
from senlin.common.i18n import _
from senlin.common import schema
from senlin.engine import cluster as cluster_mod
from senlin.policies import base


class HealthPolicy(base.Policy):
    '''Policy for health checking for members of a cluster.'''

    __type_name__ = 'HealthPolicy'

    TARGET = [
        ('AFTER', consts.CLUSTER_ADD_NODES),
        ('AFTER', consts.CLUSTER_SCALE_OUT),
        ('BEFORE', consts.CLUSTER_DEL_NODES),
        ('BEFORE', consts.CLUSTER_SCALE_IN),
    ]

    # Should be ANY if profile provides health check support?
    PROFILE_TYPE = [
        'os.nova.server',
        'os.heat.stack',
        'AWS.AutoScaling.LaunchConfiguration',
    ]

    KEYS = (DETECTION, RECOVERY) = ('detection', 'recovery')

    _DETECTION_KEYS = (
        DETECTION_TYPE, DETECTION_INTERVAL
    ) = (
        'type', 'interval'
    )

    DETECTION_TYPES = (
        VM_LIFECYCLE_EVENTS, NODE_STATUS_POLLING, LB_STATUS_POLLING,
    ) = (
        'VM_LIFECYCLE_EVENTS', 'NODE_STATUS_POLLING', 'LB_STATUS_POLLING',
    )

    _RECOVERY_KEYS = (
        RECOVERY_ACTIONS_KEY, RECOVERY_FENCING_KEY
    ) = (
        'actions', 'fencing'
    )

    RECOVERY_ACTIONS = (
        REBOOT, REBUILD, MIGRATE, EVACUATE, RECREATE, NOP
    ) = (
        'REBOOT', 'REBUILD', 'MIGRATE', 'EVACUATE', 'RECREATE', 'NOP',
    )

    FENCING_OPTIONS = (
        COMPUTE, STORAGE, NETWORK,
    ) = (
        'COMPUTE', 'STORAGE', 'NETWORK'
    )

    spec_schema = {
        DETECTION: schema.Map(
            _('Policy aspect for node failure detection.'),
            schema={
                DETECTION_TYPE: schema.String(
                    _('Type of node failure detection.'),
                    constraints=[
                        constraints.AllowedValues(DETECTION_TYPES),
                    ],
                    required=True,
                ),
                DETECTION_INTERVAL: schema.Integer(
                    _('Number of seconds as interval between pollings. '
                      'Only required when type is about polling.'),
                    default=60,
                ),
            },
            required=True,
        ),
        RECOVERY: schema.Map(
            _('Policy aspect for node failure recovery.'),
            schema={
                RECOVERY_ACTIONS_KEY: schema.List(
                    _('List of actions to try for node recovery.'),
                    schema=schema.String(
                        _('Action to try for node recovery.'),
                        constraints=[
                            constraints.AllowedValues(RECOVERY_ACTIONS),
                        ]
                    ),
                ),
                RECOVERY_FENCING_KEY: schema.List(
                    _('List of services to be fenced.'),
                    schema=schema.String(
                        _('Service to be fenced.'),
                        constraints=[
                            constraints.AllowedValues(FENCING_OPTIONS),
                        ],
                    ),
                ),
            }
        ),
    }

    def __init__(self, type_name, name, **kwargs):
        super(HealthPolicy, self).__init__(type_name, name, kwargs)

        self.check_type = self.spec_data[self.DETECTION][self.DETECTION_TYPE]
        self.interval = self.spec_data[self.DETECTION][self.CHECK_INTERVAL]

    def attach(self, cluster_id, action, data):
        '''Hook for policy attach.

        Initialize the health check mechanism for existing nodes in cluster.
        '''
        cluster = cluster_mod.Cluster.load(action.context,
                                           cluster_id=cluster_id)
        cluster.heathy_check_enable()
        cluster.heathy_check_set_interval(self.interval)

        return True

    def detach(self, cluster_id, action, data):
        '''Hook for policy detach.

        Deinitialize the health check mechanism (for the cluster).
        '''
        cluster = cluster_mod.Cluster.load(action.context,
                                           cluster_id=cluster_id)
        cluster.heathy_check_disable()
        return True

    def pre_op(self, cluster_id, action, **args):
        # Ignore actions that are not required to be processed at this stage
        if action not in (consts.CLUSTER_SCALE_IN,
                          consts.CLUSTER_DEL_NODES):
            return True

        # TODO(anyone): Unsubscribe nodes from backend health monitoring
        #               infrastructure
        return True

    def post_op(self, cluster_id, action, **args):
        # Ignore irrelevant action here
        if action not in (consts.CLUSTER_SCALE_OUT,
                          consts.CLUSTER_ADD_NODES):
            return True

        # TODO(anyone): subscribe to vm-lifecycle-events for the specified VM
        #                or add vm to the list of VM status polling
        return True
