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
Policy for scheduling nodes across availability zones.

NOTE: For full documentation about how the policy works, check:
https://docs.openstack.org/senlin/latest/developer/policies/zone_v1.html
"""

import math
import operator

from oslo_log import log as logging

from senlin.common import consts
from senlin.common import exception as exc
from senlin.common.i18n import _
from senlin.common import scaleutils
from senlin.common import schema
from senlin.engine import cluster as cm
from senlin.objects import cluster as co
from senlin.objects import node as no
from senlin.policies import base

LOG = logging.getLogger(__name__)


class ZonePlacementPolicy(base.Policy):
    """Policy for placing members of a cluster across availability zones."""

    VERSION = '1.0'
    VERSIONS = {
        '1.0': [
            {'status': consts.EXPERIMENTAL, 'since': '2016.04'},
            {'status': consts.SUPPORTED, 'since': '2016.10'},
        ]
    }
    PRIORITY = 300

    TARGET = [
        ('BEFORE', consts.CLUSTER_SCALE_OUT),
        ('BEFORE', consts.CLUSTER_SCALE_IN),
        ('BEFORE', consts.CLUSTER_RESIZE),
        ('BEFORE', consts.NODE_CREATE),
    ]

    PROFILE_TYPE = [
        'os.nova.server-1.0',
    ]

    KEYS = (
        ZONES,
    ) = (
        'zones',
    )

    _AZ_KEYS = (
        ZONE_NAME, ZONE_WEIGHT,
    ) = (
        'name', 'weight',
    )

    properties_schema = {
        ZONES: schema.List(
            _('List of availability zones to choose from.'),
            schema=schema.Map(
                _('An availability zone as candidate.'),
                schema={
                    ZONE_NAME: schema.String(
                        _('Name of an availability zone.'),
                    ),
                    ZONE_WEIGHT: schema.Integer(
                        _('Weight of the availability zone (default is 100).'),
                        default=100,
                        required=False,
                    )
                },
            ),
        ),
    }

    def __init__(self, name, spec, **kwargs):
        super(ZonePlacementPolicy, self).__init__(name, spec, **kwargs)

        self.zones = dict((z[self.ZONE_NAME], z[self.ZONE_WEIGHT])
                          for z in self.properties.get(self.ZONES))

    def validate(self, context, validate_props=False):
        super(ZonePlacementPolicy, self).validate(context, validate_props)

        if not validate_props:
            return True

        nc = self.nova(context.user_id, context.project_id)
        input_azs = sorted(self.zones.keys())
        valid_azs = nc.validate_azs(input_azs)
        invalid_azs = sorted(set(input_azs) - set(valid_azs))
        if invalid_azs:
            msg = _("The specified %(key)s '%(value)s' could not be "
                    "found.") % {'key': self.ZONE_NAME,
                                 'value': list(invalid_azs)}
            raise exc.InvalidSpec(message=msg)

        return True

    def _create_plan(self, current, zones, count, expand):
        """Compute a placement plan based on the weights of AZs.

        :param current: Distribution of existing nodes.
        :returns: A dict that contains a placement plan.
        """
        # sort candidate zones by distribution and covert it into a list
        candidates = sorted(zones.items(), key=operator.itemgetter(1),
                            reverse=expand)

        sum_weight = sum(zones.values())
        if expand:
            total = count + sum(current.values())
        else:
            total = sum(current.values()) - count

        remain = count
        plan = dict.fromkeys(zones.keys(), 0)

        for i in range(len(zones)):
            zone = candidates[i][0]
            weight = candidates[i][1]
            q = total * weight / float(sum_weight)
            if expand:
                quota = int(math.ceil(q))
                headroom = quota - current[zone]
            else:
                quota = int(math.floor(q))
                headroom = current[zone] - quota

            if headroom <= 0:
                continue

            if headroom < remain:
                plan[zone] = headroom
                remain -= headroom
            else:
                plan[zone] = remain if remain > 0 else 0
                remain = 0
                break

        if remain > 0:
            return None

        # filter out zero values
        result = {}
        for z, c in plan.items():
            if c > 0:
                result[z] = c

        return result

    def _get_count(self, cluster_id, action):
        """Get number of nodes to create or delete.

        :param cluster_id: The ID of the target cluster.
        :param action: The action object which triggered this policy check.
        :return: An integer value which can be 1) positive - number of nodes
                 to create; 2) negative - number of nodes to delete; 3) 0 -
                 something wrong happened, and the policy check failed.
        """
        if action.action == consts.NODE_CREATE:
            # skip the policy if availability zone is specified in profile
            profile = action.entity.rt['profile']
            if profile.properties[profile.AVAILABILITY_ZONE]:
                return 0
            return 1

        if action.action == consts.CLUSTER_RESIZE:
            if action.data.get('deletion', None):
                return -action.data['deletion']['count']
            elif action.data.get('creation', None):
                return action.data['creation']['count']

            db_cluster = co.Cluster.get(action.context, cluster_id)
            current = no.Node.count_by_cluster(action.context, cluster_id)
            res = scaleutils.parse_resize_params(action, db_cluster, current)
            if res[0] == base.CHECK_ERROR:
                action.data['status'] = base.CHECK_ERROR
                action.data['reason'] = res[1]
                LOG.error(res[1])
                return 0

            if action.data.get('deletion', None):
                return -action.data['deletion']['count']
            else:
                return action.data['creation']['count']

        if action.action == consts.CLUSTER_SCALE_IN:
            pd = action.data.get('deletion', None)
            if pd is None:
                return -action.inputs.get('count', 1)
            else:
                return -pd.get('count', 1)

        # CLUSTER_SCALE_OUT: an action that inflates the cluster
        pd = action.data.get('creation', None)
        if pd is None:
            return action.inputs.get('count', 1)
        else:
            return pd.get('count', 1)

    def pre_op(self, cluster_id, action):
        """Callback function when cluster membership is about to change.

        :param cluster_id: ID of the target cluster.
        :param action: The action that triggers this policy check.
        """
        count = self._get_count(cluster_id, action)
        if count == 0:
            return

        expand = True
        if count < 0:
            expand = False
            count = -count

        cluster = cm.Cluster.load(action.context, cluster_id)

        nc = self.nova(cluster.user, cluster.project)
        zones_good = nc.validate_azs(self.zones.keys())
        if len(zones_good) == 0:
            action.data['status'] = base.CHECK_ERROR
            action.data['reason'] = _('No availability zone found available.')
            LOG.error('No availability zone found available.')
            return

        zones = {}
        for z, w in self.zones.items():
            if z in zones_good:
                zones[z] = w

        current = cluster.get_zone_distribution(action.context, zones.keys())
        result = self._create_plan(current, zones, count, expand)

        if not result:
            action.data['status'] = base.CHECK_ERROR
            action.data['reason'] = _('There is no feasible plan to '
                                      'handle all nodes.')
            LOG.error('There is no feasible plan to handle all nodes.')
            return

        if expand:
            if 'creation' not in action.data:
                action.data['creation'] = {}
            action.data['creation']['count'] = count
            action.data['creation']['zones'] = result
        else:
            if 'deletion' not in action.data:
                action.data['deletion'] = {}
            action.data['deletion']['count'] = count
            action.data['deletion']['zones'] = result
