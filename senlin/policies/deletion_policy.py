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

"""
Policy for deleting node(s) from a cluster.

NOTE: For full documentation about how the deletion policy works, check:
https://docs.openstack.org/senlin/latest/developer/policies/deletion_v1.html
"""
from oslo_log import log as logging

from senlin.common import constraints
from senlin.common import consts
from senlin.common.i18n import _
from senlin.common import scaleutils as su
from senlin.common import schema
from senlin.policies import base

LOG = logging.getLogger(__name__)


class DeletionPolicy(base.Policy):
    """Policy for choosing victim node(s) from a cluster for deletion.

    This policy is enforced when nodes are to be removed from a cluster.
    It will yield an ordered list of candidates for deletion based on user
    specified criteria.
    """

    VERSION = '1.1'
    VERSIONS = {
        '1.0': [
            {'status': consts.SUPPORTED, 'since': '2016.04'}
        ],
        '1.1': [
            {'status': consts.SUPPORTED, 'since': '2018.01'}
        ],
    }
    PRIORITY = 400

    KEYS = (
        CRITERIA, DESTROY_AFTER_DELETION, GRACE_PERIOD,
        REDUCE_DESIRED_CAPACITY, HOOKS, TYPE, PARAMS, QUEUE, URL, TIMEOUT
    ) = (
        'criteria', 'destroy_after_deletion', 'grace_period',
        'reduce_desired_capacity', 'hooks', 'type', 'params', 'queue', 'url',
        'timeout'
    )

    CRITERIA_VALUES = (
        OLDEST_FIRST, OLDEST_PROFILE_FIRST, YOUNGEST_FIRST, RANDOM,
    ) = (
        'OLDEST_FIRST', 'OLDEST_PROFILE_FIRST', 'YOUNGEST_FIRST', 'RANDOM',
    )

    HOOK_VALUES = (
        ZAQAR, WEBHOOK
    ) = (
        'zaqar', 'webhook',
    )

    TARGET = [
        ('BEFORE', consts.CLUSTER_SCALE_IN),
        ('BEFORE', consts.CLUSTER_DEL_NODES),
        ('BEFORE', consts.CLUSTER_RESIZE),
        ('BEFORE', consts.NODE_DELETE),
    ]

    PROFILE_TYPE = [
        'ANY'
    ]

    properties_schema = {
        CRITERIA: schema.String(
            _('Criteria used in selecting candidates for deletion'),
            default=RANDOM,
            constraints=[
                constraints.AllowedValues(CRITERIA_VALUES),
            ]
        ),
        DESTROY_AFTER_DELETION: schema.Boolean(
            _('Whether a node should be completely destroyed after '
              'deletion. Default to True'),
            default=True,
        ),
        GRACE_PERIOD: schema.Integer(
            _('Number of seconds before real deletion happens.'),
            default=0,
        ),
        REDUCE_DESIRED_CAPACITY: schema.Boolean(
            _('Whether the desired capacity of the cluster should be '
              'reduced along the deletion. Default to True.'),
            default=True,
        ),
        HOOKS: schema.Map(
            _("Lifecycle hook properties"),
            schema={
                TYPE: schema.String(
                    _("Type of lifecycle hook"),
                    default=ZAQAR,
                    constraints=[
                        constraints.AllowedValues(HOOK_VALUES),
                    ]
                ),
                PARAMS: schema.Map(
                    schema={
                        QUEUE: schema.String(
                            _("Zaqar queue to receive lifecycle hook message"),
                            default="",
                        ),
                        URL: schema.String(
                            _("Url sink to which to send lifecycle hook "
                              "message"),
                            default="",
                        ),
                    },
                    default={}
                ),
                TIMEOUT: schema.Integer(
                    _('Number of seconds before actual deletion happens.'),
                    default=0,
                ),
            },
            default={}
        )
    }

    def __init__(self, name, spec, **kwargs):
        super(DeletionPolicy, self).__init__(name, spec, **kwargs)

        self.criteria = self.properties[self.CRITERIA]
        self.grace_period = self.properties[self.GRACE_PERIOD]
        self.destroy_after_deletion = self.properties[
            self.DESTROY_AFTER_DELETION]
        self.reduce_desired_capacity = self.properties[
            self.REDUCE_DESIRED_CAPACITY]
        self.hooks = self.properties[self.HOOKS]

    def _victims_by_regions(self, cluster, regions):
        victims = []
        for region in sorted(regions.keys()):
            count = regions[region]
            nodes = cluster.nodes_by_region(region)
            if self.criteria == self.RANDOM:
                candidates = su.nodes_by_random(nodes, count)
            elif self.criteria == self.OLDEST_PROFILE_FIRST:
                candidates = su.nodes_by_profile_age(nodes, count)
            elif self.criteria == self.OLDEST_FIRST:
                candidates = su.nodes_by_age(nodes, count, True)
            else:
                candidates = su.nodes_by_age(nodes, count, False)

            victims.extend(candidates)

        return victims

    def _victims_by_zones(self, cluster, zones):
        victims = []
        for zone in sorted(zones.keys()):
            count = zones[zone]
            nodes = cluster.nodes_by_zone(zone)
            if self.criteria == self.RANDOM:
                candidates = su.nodes_by_random(nodes, count)
            elif self.criteria == self.OLDEST_PROFILE_FIRST:
                candidates = su.nodes_by_profile_age(nodes, count)
            elif self.criteria == self.OLDEST_FIRST:
                candidates = su.nodes_by_age(nodes, count, True)
            else:
                candidates = su.nodes_by_age(nodes, count, False)

            victims.extend(candidates)

        return victims

    def _update_action(self, action, victims):
        pd = action.data.get('deletion', {})
        pd['count'] = len(victims)
        pd['candidates'] = victims
        pd['destroy_after_deletion'] = self.destroy_after_deletion
        pd['grace_period'] = self.grace_period
        pd['reduce_desired_capacity'] = self.reduce_desired_capacity
        action.data.update({
            'status': base.CHECK_OK,
            'reason': _('Candidates generated'),
            'deletion': pd
        })
        action.store(action.context)

    def pre_op(self, cluster_id, action):
        """Choose victims that can be deleted.

        :param cluster_id: ID of the cluster to be handled.
        :param action: The action object that triggered this policy.
        """

        victims = action.inputs.get('candidates', [])
        if len(victims) > 0:
            self._update_action(action, victims)
            return

        if action.action == consts.NODE_DELETE:
            self._update_action(action, [action.entity.id])
            return

        cluster = action.entity
        regions = None
        zones = None

        hooks_data = self.hooks
        action.data.update({'status': base.CHECK_OK,
                            'reason': _('lifecycle hook parameters saved'),
                            'hooks': hooks_data})
        action.store(action.context)

        deletion = action.data.get('deletion', {})
        if deletion:
            # there are policy decisions
            count = deletion['count']
            regions = deletion.get('regions', None)
            zones = deletion.get('zones', None)
        # No policy decision, check action itself: SCALE_IN
        elif action.action == consts.CLUSTER_SCALE_IN:
            count = action.inputs.get('count', 1)

        # No policy decision, check action itself: RESIZE
        else:
            current = len(cluster.nodes)
            res, reason = su.parse_resize_params(action, cluster, current)
            if res == base.CHECK_ERROR:
                action.data['status'] = base.CHECK_ERROR
                action.data['reason'] = reason
                LOG.error(reason)
                return

            if 'deletion' not in action.data:
                return
            count = action.data['deletion']['count']

        # Cross-region
        if regions:
            victims = self._victims_by_regions(cluster, regions)
            self._update_action(action, victims)
            return

        # Cross-AZ
        if zones:
            victims = self._victims_by_zones(cluster, zones)
            self._update_action(action, victims)
            return

        if count > len(cluster.nodes):
            count = len(cluster.nodes)

        if self.criteria == self.RANDOM:
            victims = su.nodes_by_random(cluster.nodes, count)
        elif self.criteria == self.OLDEST_PROFILE_FIRST:
            victims = su.nodes_by_profile_age(cluster.nodes, count)
        elif self.criteria == self.OLDEST_FIRST:
            victims = su.nodes_by_age(cluster.nodes, count, True)
        else:
            victims = su.nodes_by_age(cluster.nodes, count, False)

        self._update_action(action, victims)
        return
