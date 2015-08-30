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

from oslo_service import periodic_task

from senlin.common import constraints
from senlin.common import consts
from senlin.common.i18n import _
from senlin.common import schema
from senlin.policies import base


class HealthPolicy(base.Policy):
    '''Policy for health checking for members of a cluster.'''

    VERSION = '1.0'

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
        DETECTION_TYPE, DETECTION_OPTIONS,
    ) = (
        'type', 'options'
    )

    DETECTION_TYPES = (
        VM_LIFECYCLE_EVENTS, NODE_STATUS_POLLING, LB_STATUS_POLLING,
    ) = (
        'VM_LIFECYCLE_EVENTS', 'NODE_STATUS_POLLING', 'LB_STATUS_POLLING',
    )

    _DETECTION_OPTIONS = (
        DETECTION_INTERVAL,
    ) = (
        'interval',
    )

    _RECOVERY_KEYS = (
        RECOVERY_ACTIONS, RECOVERY_FENCING
    ) = (
        'actions', 'fencing'
    )

    RECOVERY_ACTION_VALUES = (
        REBOOT, REBUILD, MIGRATE, EVACUATE, RECREATE, NOP
    ) = (
        'REBOOT', 'REBUILD', 'MIGRATE', 'EVACUATE', 'RECREATE', 'NOP',
    )

    FENCING_OPTION_VALUES = (
        COMPUTE, STORAGE, NETWORK,
    ) = (
        'COMPUTE', 'STORAGE', 'NETWORK'
    )

    properties_schema = {
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
                DETECTION_OPTIONS: schema.Map(
                    schema={
                        DETECTION_INTERVAL: schema.Integer(
                            _("Number of seconds between pollings. Only "
                              "required when type is 'NODE_STATUS_POLLING'."),
                            default=60,
                        ),
                    }
                ),
            },
            required=True,
        ),
        RECOVERY: schema.Map(
            _('Policy aspect for node failure recovery.'),
            schema={
                RECOVERY_ACTIONS: schema.List(
                    _('List of actions to try for node recovery.'),
                    schema=schema.String(
                        _('Action to try for node recovery.'),
                        constraints=[
                            constraints.AllowedValues(RECOVERY_ACTION_VALUES),
                        ]
                    ),
                ),
                RECOVERY_FENCING: schema.List(
                    _('List of services to be fenced.'),
                    schema=schema.String(
                        _('Service to be fenced.'),
                        constraints=[
                            constraints.AllowedValues(FENCING_OPTION_VALUES),
                        ],
                    ),
                ),
            }
        ),
    }

    def __init__(self, name, spec, **kwargs):
        super(HealthPolicy, self).__init__(name, spec, kwargs)

        self.check_type = self.properties[self.DETECTION][self.DETECTION_TYPE]
        options = self.properties[self.DETECTION][self.DETECTION_OPTIONS]
        self.interval = options[self.DETECTION_INTERVAL]

    def attach(self, cluster):
        '''Hook for policy attach.

        Initialize the health check mechanism for existing nodes in cluster.
        '''
        data = {
            'type': self.check_type,
            'interval': self.interval,
            'counter': 0,
        }

        # TODO(anyone): register cluster for periodic checking
        return True, self._build_policy_data(data)

    def detach(self, cluster):
        '''Hook for policy detach.

        Deinitialize the health check mechanism (for the cluster).
        '''
        # TODO(anyone): deregister cluster from periodic checking
        return True, ''

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
        #               or add vm to the list of VM status polling
        return True

    @periodic_task.periodic_task
    def health_check(self):
        if not self.detect_enabled:
            return

        if (self.detect_counter < self.detect_interval):
            self.detect_counter += 1
            return
        self.detect_counter = 0

        failures = 0
        for n in self.rt['nodes']:
            if(n.rt.profile.do_check(n)):
                continue

            failures += 1

        # TODO(Anyone): How to enforce the HA policy?
        pass
