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

from oslo_log import log as logging

from senlin.common import constraints
from senlin.common import consts
from senlin.common.i18n import _
from senlin.common.i18n import _LW
from senlin.common import schema
from senlin.db import api as db_api
from senlin.policies import base

LOG = logging.getLogger(__name__)


class ScalingPolicy(base.Policy):
    '''Policy for changing the size of a cluster.

    This policy is expected to be enforced before the node list of a cluster
    is changed.
    '''

    __type_name__ = 'ScalingPolicy'

    TARGET = [
        ('BEFORE', consts.CLUSTER_SCALE_OUT),
        ('BEFORE', consts.CLUSTER_SCALE_IN),
    ]

    PROFILE_TYPE = [
        'ANY',
    ]

    KEYS = (
        MIN_SIZE, MAX_SIZE, ADJUSTMENT,
    ) = (
        'min_size', 'max_size', 'adjustment',
    )

    ADJUSTMENT_TYPES = (
        EXACT_CAPACITY, CHANGE_IN_CAPACITY, CHANGE_IN_PERCENTAGE,
    ) = (
        'EXACT_CAPACITY', 'CHANGE_IN_CAPACITY', 'CHANGE_IN_PERCENTAGE',
    )

    _ADJUSTMENT_KEYS = (
        ADJUSTMENT_TYPE, ADJUSTMENT_NUMBER, MIN_STEP,
    ) = (
        'type', 'number', 'min_step',
    )

    spec_schema = {
        MIN_SIZE: schema.Integer(
            _('Minumum size for the cluster.'),
            default=0,
        ),
        MAX_SIZE: schema.Integer(
            _('Maximum size for the cluster.'),
        ),
        ADJUSTMENT: schema.Map(
            _('Detailed specification for scaling adjustments.'),
            schema={
                ADJUSTMENT_TYPE: schema.String(
                    _('Type of adjustment when scaling is triggered.'),
                    constraints=[
                        constraints.AllowedValues(ADJUSTMENT_TYPES),
                    ],
                    default=CHANGE_IN_CAPACITY,
                ),
                ADJUSTMENT_NUMBER: schema.Number(
                    _('A number specifying the amount of adjustment.'),
                    default=1,
                ),
                MIN_STEP: schema.Integer(
                    _('When adjustment type is set to "CHANGE_IN_PERCENTAGE",'
                      ' this specifies the cluster size will be changed by '
                      'at least this number of nodes.'),
                    default=1,
                ),
            }
        ),
    }

    def __init__(self, type_name, name, **kwargs):
        super(ScalingPolicy, self).__init__(type_name, name, **kwargs)

        self.min_size = self.spec_data[self.MIN_SIZE]
        self.max_size = self.spec_data[self.MAX_SIZE]
        adjustment = self.spec_data[self.ADJUSTMENT]

        self.adjustment_type = adjustment[self.ADJUSTMENT_TYPE]
        self.adjustment_number = adjustment[self.ADJUSTMENT_NUMBER]
        self.adjustment_min_step = adjustment[self.MIN_STEP]

        # TODO(anyone): Make sure the default cooldown can be used if
        # not specified

    def pre_op(self, cluster_id, action, policy_data):
        nodes = db_api.node_get_all_by_cluster(action.context, cluster_id)
        current_size = len(nodes)

        if self.adjustment_type == self.EXACT_CAPACITY:
            count = self.adjustment_number - current_size
        elif self.adjustment_type == self.CHANGE_IN_CAPACITY:
            count = self.adjustment_number
        elif self.adjustment_type == self.CHANGE_IN_PERCENTAGE:
            count = int((self.adjustment_number * current_size) / 100.0)
            if count < self.adjustment_min_step:
                count = self.adjustment_min_step
        if current_size + count > self.max_size:
            policy_data.status = base.CHECK_ERROR
            policy_data.reason = _('Attempted scaling exceeds maximum size')
        elif current_size + count < self.min_size:
            policy_data.status = base.CHECK_ERROR
            policy_data.reason = _('Attempted scaling exceeds minimum size')
        else:
            policy_data.status = base.CHECK_OK
            policy_data.reason = _('Scaling request validated')

        pd = {'count': count}
        if action.action == consts.CLUSTER_SCALE_OUT:
            if count < 0:
                LOG.warning(_LW('Requesting a scale out operation but scaling '
                                'policy generates a negative count.'))
            policy_data['creation'] = pd
        elif action.action == consts.CLUSTER_SCALE_IN:
            if count > 0:
                LOG.warning(_LW('Requesting a scale out operation but scaling '
                                'policy generates a negative count.'))
            policy_data['deletion'] = pd

        return policy_data
