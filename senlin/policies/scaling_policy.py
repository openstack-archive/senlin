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
from senlin.common import schema
from senlin.db import api as db_api
from senlin.policies import base

LOG = logging.getLogger(__name__)


class ScalingPolicy(base.Policy):
    '''Policy for changing the size of a cluster.

    This policy is expected to be enforced before the node count of a cluster
    is changed.
    '''

    VERSION = '1.0'

    TARGET = [
        ('BEFORE', consts.CLUSTER_SCALE_IN),
        ('BEFORE', consts.CLUSTER_SCALE_OUT),
    ]

    PROFILE_TYPE = [
        'ANY',
    ]

    KEYS = (
        EVENT, ADJUSTMENT,
    ) = (
        'event', 'adjustment',
    )

    _SUPPORTED_EVENTS = (
        CLUSTER_SCALE_IN, CLUSTER_SCALE_OUT,
    ) = (
        consts.CLUSTER_SCALE_IN, consts.CLUSTER_SCALE_OUT,
    )

    _ADJUSTMENT_KEYS = (
        ADJUSTMENT_TYPE, ADJUSTMENT_NUMBER, MIN_STEP, BEST_EFFORT,
    ) = (
        'type', 'number', 'min_step', 'best_effort',
    )

    properties_schema = {
        EVENT: schema.String(
            _('Event that will trigger this policy. Must be one of '
              'CLUSTER_SCALE_IN and CLUSTER_SCALE_OUT.'),
            constraints=[
                constraints.AllowedValues(_SUPPORTED_EVENTS),
            ],
            required=True,
        ),
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

    def __init__(self, name, spec, **kwargs):
        super(ScalingPolicy, self).__init__(name, spec, **kwargs)

        self.event = self.properties[self.EVENT]
        self.singleton = False
        adjustment = self.properties[self.ADJUSTMENT]

        self.adjustment_type = adjustment[self.ADJUSTMENT_TYPE]
        self.adjustment_number = adjustment[self.ADJUSTMENT_NUMBER]
        self.adjustment_min_step = adjustment[self.MIN_STEP]
        self.best_effort = adjustment[self.BEST_EFFORT]

    def _calculate_adjustment_count(self, current_size):
        '''Calculate adjustment count based on current_size'''

        if self.adjustment_type == consts.EXACT_CAPACITY:
            if self.event == consts.CLUSTER_SCALE_IN:
                count = current_size - self.adjustment_number
            else:
                count = self.adjustment_number - current_size
        elif self.adjustment_type == consts.CHANGE_IN_CAPACITY:
            count = self.adjustment_number
        else:   # consts.CHANGE_IN_PERCENTAGE:
            count = int((self.adjustment_number * current_size) / 100.0)
            if count < self.adjustment_min_step:
                count = self.adjustment_min_step

        return count

    def pre_op(self, cluster_id, action):

        status = base.CHECK_OK
        reason = _('Scaling request validated.')

        # Check if the action is expected by the policy
        if self.event != action.action:
            action.data.update({'status': status, 'reason': reason})
            action.store(action.context)
            return

        cluster = db_api.cluster_get(action.context, cluster_id)
        nodes = db_api.node_get_all_by_cluster(action.context, cluster_id)
        current_size = len(nodes)
        count = self._calculate_adjustment_count(current_size)

        # Use action input if count is provided
        count = action.inputs.get('count', count)

        if count <= 0:
            status = base.CHECK_ERROR
            reason = _("Count (%(count)s) invalid for action %(action)s."
                       ) % {'count': count, 'action': action.action}

        # Check size constraints
        if action.action == consts.CLUSTER_SCALE_IN:
            new_size = current_size - count
            if (new_size < cluster.min_size):
                if self.best_effort:
                    count = current_size - cluster.min_size
                    reason = _('Do best effort scaling.')
                else:
                    status = base.CHECK_ERROR
                    reason = _('Attempted scaling below minimum size.')
        else:
            new_size = current_size + count
            if (new_size > cluster.max_size):
                if self.best_effort:
                    count = cluster.max_size - current_size
                    reason = _('Do best effort scaling.')
                else:
                    status = base.CHECK_ERROR
                    reason = _('Attempted scaling above maximum size.')

        pd = {'status': status, 'reason': reason}
        if status == base.CHECK_OK:
            if action.action == consts.CLUSTER_SCALE_IN:
                pd['deletion'] = {'count': count}
            else:
                pd['creation'] = {'count': count}

        action.data.update(pd)
        action.store(action.context)

        return
