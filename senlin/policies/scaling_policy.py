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

from oslo_config import cfg

from senlin.common import constraints
from senlin.common import consts
from senlin.common import exception as exc
from senlin.common.i18n import _
from senlin.common import scaleutils as su
from senlin.common import schema
from senlin.common import utils
from senlin.policies import base


CONF = cfg.CONF


class ScalingPolicy(base.Policy):
    """Policy for changing the size of a cluster.

    This policy is expected to be enforced before the node count of a cluster
    is changed.
    """

    VERSION = '1.0'
    VERSIONS = {
        '1.0': [
            {'status': consts.SUPPORTED, 'since': '2016.04'}
        ]
    }

    PRIORITY = 100

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
        COOLDOWN,
    ) = (
        'type', 'number', 'min_step', 'best_effort',
        'cooldown',
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
                COOLDOWN: schema.Integer(
                    _('Number of seconds to hold the cluster for cool-down '
                      'before allowing cluster to be resized again.'),
                    default=0,
                ),

            }
        ),
    }

    def __init__(self, name, spec, **kwargs):
        """Initialize a scaling policy object.

        :param name: Name for the policy object.
        :param spec: A dictionary containing the detailed specification for
                     the policy.
        :param dict kwargs: Other optional parameters for policy object
                            creation.
        :return: An object of `ScalingPolicy`.
        """
        super(ScalingPolicy, self).__init__(name, spec, **kwargs)

        self.singleton = False

        self.event = self.properties[self.EVENT]

        adjustment = self.properties[self.ADJUSTMENT]
        self.adjustment_type = adjustment[self.ADJUSTMENT_TYPE]
        self.adjustment_number = adjustment[self.ADJUSTMENT_NUMBER]
        self.adjustment_min_step = adjustment[self.MIN_STEP]

        self.best_effort = adjustment[self.BEST_EFFORT]
        self.cooldown = adjustment[self.COOLDOWN]

    def validate(self, context, validate_props=False):
        super(ScalingPolicy, self).validate(context, validate_props)

        if self.adjustment_number <= 0:
            msg = _("the 'number' for 'adjustment' must be > 0")
            raise exc.InvalidSpec(message=msg)

        if self.adjustment_min_step < 0:
            msg = _("the 'min_step' for 'adjustment' must be >= 0")
            raise exc.InvalidSpec(message=msg)

        if self.cooldown < 0:
            msg = _("the 'cooldown' for 'adjustment' must be >= 0")
            raise exc.InvalidSpec(message=msg)

    def _calculate_adjustment_count(self, current_size):
        """Calculate adjustment count based on current_size.

        :param current_size: The current size of the target cluster.
        :return: The number of nodes to add or to remove.
        """

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
        """The hook function that is executed before the action.

        The checking result is stored in the ``data`` property of the action
        object rather than returned directly from the function.

        :param cluster_id: The ID of the target cluster.
        :param action: Action instance against which the policy is being
                       checked.
        :return: None.
        """

        # Use action input if count is provided
        count_value = action.inputs.get('count', None)
        cluster = action.entity
        current = len(cluster.nodes)

        if count_value is None:
            # count not specified, calculate it
            count_value = self._calculate_adjustment_count(current)

        # Count must be positive value
        success, count = utils.get_positive_int(count_value)
        if not success:
            action.data.update({
                'status': base.CHECK_ERROR,
                'reason': _("Invalid count (%(c)s) for action '%(a)s'."
                            ) % {'c': count_value, 'a': action.action}
            })
            action.store(action.context)
            return

        # Check size constraints
        max_size = cluster.max_size
        if max_size == -1:
            max_size = cfg.CONF.max_nodes_per_cluster
        if action.action == consts.CLUSTER_SCALE_IN:
            if self.best_effort:
                count = min(count, current - cluster.min_size)
            result = su.check_size_params(cluster, current - count,
                                          strict=not self.best_effort)
        else:
            if self.best_effort:
                count = min(count, max_size - current)
            result = su.check_size_params(cluster, current + count,
                                          strict=not self.best_effort)

        if result:
            # failed validation
            pd = {
                'status': base.CHECK_ERROR,
                'reason': result
            }
        else:
            # passed validation
            pd = {
                'status': base.CHECK_OK,
                'reason': _('Scaling request validated.'),
            }
            if action.action == consts.CLUSTER_SCALE_IN:
                pd['deletion'] = {'count': count}
            else:
                pd['creation'] = {'count': count}

        action.data.update(pd)
        action.store(action.context)

        return

    def need_check(self, target, action):
        res = super(ScalingPolicy, self).need_check(target, action)
        if res:
            # Check if the action is expected by the policy
            res = (self.event == action.action)

        return res
