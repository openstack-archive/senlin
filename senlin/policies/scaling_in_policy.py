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
from senlin.common import exception
from senlin.common.i18n import _
from senlin.common import schema
from senlin.db import api as db_api
from senlin.policies import base

LOG = logging.getLogger(__name__)


class ScalingInPolicy(base.Policy):
    '''Policy for decreasing the size of a cluster.

    This policy is expected to be enforced before the node count of a cluster
    is decreased.
    '''

    __type_name__ = 'ScalingInPolicy'

    TARGET = [
        ('BEFORE', consts.CLUSTER_SCALE_IN),
    ]

    PROFILE_TYPE = [
        'ANY',
    ]

    KEYS = (
        ADJUSTMENT,
    ) = (
        'adjustment',
    )

    _ADJUSTMENT_KEYS = (
        ADJUSTMENT_TYPE, ADJUSTMENT_NUMBER, MIN_STEP, BEST_EFFORT,
    ) = (
        'type', 'number', 'min_step', 'best_effort',
    )

    spec_schema = {
        ADJUSTMENT: schema.Map(
            _('Detailed specification for scaling adjustments.'),
            schema={
                ADJUSTMENT_TYPE: schema.String(
                    _('Type of adjustment when scaling is triggered.'),
                    constraints=[
                        constraints.AllowedValues(consts.ADJUSTMENT_TYPES),
                    ],
                    default=consts.CHANGE_IN_CAPACITY,
                ),
                ADJUSTMENT_NUMBER: schema.Number(
                    _('A number specifying the amount of adjustment.'),
                    default=1,
                ),
                MIN_STEP: schema.Integer(
                    _('When adjustment type is set to "CHANGE_IN_PERCENTAGE",'
                      ' this specifies the cluster size will be decreased by '
                      'at least this number of nodes.'),
                    default=1,
                ),
                BEST_EFFORT: schema.Boolean(
                    _('Whether do best effort scaling when new size of '
                      'cluster will break the size limitation'),
                    default=False,
                ),
            }
        ),
    }

    def __init__(self, type_name, name, **kwargs):
        super(ScalingInPolicy, self).__init__(type_name, name, **kwargs)

        adjustment = self.spec_data[self.ADJUSTMENT]
        self.adjustment_type = adjustment[self.ADJUSTMENT_TYPE]
        self.adjustment_number = adjustment[self.ADJUSTMENT_NUMBER]
        self.adjustment_min_step = adjustment[self.MIN_STEP]
        self.best_effort = adjustment[self.BEST_EFFORT]

    def validate(self):
        super(ScalingInPolicy, self).validate()

        if self.adjustment_number < 0:
            msg = _('Adjustment number is not allowed to be negative.')
            raise exception.PolicyValidationFailed(message=msg)

    def pre_op(self, cluster_id, action):
        cluster = db_api.cluster_get(action.context, cluster_id)
        nodes = db_api.node_get_all_by_cluster(action.context, cluster_id)
        current_size = len(nodes)
        count = self._calculate_adjustment_count(current_size)

        # Use action input if count is provided
        count = action.inputs.get('count', count)

        # Check size constraints
        if count < 0:
            status = base.CHECK_ERROR
            reason = _('Negative number is invalid for scaling in policy.')
        elif current_size - count < cluster.min_size:
            if not self.best_effort:
                status = base.CHECK_ERROR
                reason = _('Attempted scaling exceeds minimum size.')
            else:
                status = base.CHECK_OK
                count = current_size - cluster.min_size
                reason = _('Do best effort scaling.')
        else:
            status = base.CHECK_OK
            reason = _('Scaling request validated.')

        pd = {
            'deletion': {
                'count': count,
            },
            'status': status,
            'reason': reason,
        }
        action.data.update(pd)
        action.store(action.context)

        return

    def _calculate_adjustment_count(self, current_size):
        '''Calculate adjustment count based on current_size'''

        if self.adjustment_type == consts.EXACT_CAPACITY:
            count = current_size - self.adjustment_number
        elif self.adjustment_type == consts.CHANGE_IN_CAPACITY:
            count = self.adjustment_number
        elif self.adjustment_type == consts.CHANGE_IN_PERCENTAGE:
            count = int((self.adjustment_number * current_size) / 100.0)
            if count < self.adjustment_min_step:
                count = self.adjustment_min_step

        return count
