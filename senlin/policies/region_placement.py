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
Policy for scheduling nodes across multiple regions.

NOTE: For full documentation about how the policy works, check:
https://docs.openstack.org/senlin/latest/developer/policies/region_v1.html
"""

import math
from oslo_log import log as logging

from senlin.common import consts
from senlin.common import exception as exc
from senlin.common.i18n import _
from senlin.common import scaleutils
from senlin.common import schema
from senlin.engine import cluster as cm
from senlin.policies import base

LOG = logging.getLogger(__name__)


class RegionPlacementPolicy(base.Policy):
    """Policy for placing members of a cluster across multiple regions."""

    VERSION = '1.0'
    VERSIONS = {
        '1.0': [
            {'status': consts.EXPERIMENTAL, 'since': '2016.04'},
            {'status': consts.SUPPORTED, 'since': '2016.10'},
        ]
    }

    PRIORITY = 200

    TARGET = [
        ('BEFORE', consts.CLUSTER_SCALE_OUT),
        ('BEFORE', consts.CLUSTER_SCALE_IN),
        ('BEFORE', consts.CLUSTER_RESIZE),
        ('BEFORE', consts.NODE_CREATE),
    ]

    PROFILE_TYPE = [
        'ANY'
    ]

    KEYS = (
        REGIONS,
    ) = (
        'regions',
    )

    _AZ_KEYS = (
        REGION_NAME, REGION_WEIGHT, REGION_CAP,
    ) = (
        'name', 'weight', 'cap',
    )

    properties_schema = {
        REGIONS: schema.List(
            _('List of regions to choose from.'),
            schema=schema.Map(
                _('An region as a candidate.'),
                schema={
                    REGION_NAME: schema.String(
                        _('Name of a region.'),
                    ),
                    REGION_WEIGHT: schema.Integer(
                        _('Weight of the region. The default is 100.'),
                        default=100,
                    ),
                    REGION_CAP: schema.Integer(
                        _('Maximum number of nodes in this region. The '
                          'default is -1 which means no cap set.'),
                        default=-1,
                    ),
                },
            ),
        ),
    }

    def __init__(self, name, spec, **kwargs):
        super(RegionPlacementPolicy, self).__init__(name, spec, **kwargs)

        regions = {}
        for r in self.properties.get(self.REGIONS):
            regions[r[self.REGION_NAME]] = {
                'weight': r[self.REGION_WEIGHT],
                'cap': r[self.REGION_CAP],
            }
        self.regions = regions

    def validate(self, context, validate_props=False):
        super(RegionPlacementPolicy, self).validate(context, validate_props)

        if not validate_props:
            return True

        kc = self.keystone(context.user_id, context.project_id)
        input_regions = sorted(self.regions.keys())
        valid_regions = kc.validate_regions(input_regions)
        invalid_regions = sorted(set(input_regions) - set(valid_regions))
        if invalid_regions:
            msg = _("The specified regions '%(value)s' could not be "
                    "found.") % {'value': invalid_regions}
            raise exc.InvalidSpec(message=msg)

        return True

    def _create_plan(self, current, regions, count, expand):
        """Compute a placement plan based on the weights of regions.

        :param current: Distribution of existing nodes.
        :param regions: Usable regions for node creation.
        :param count: Number of nodes to create/delete in this plan.
        :param expand: True if the plan is for inflating the cluster, False
                       otherwise.

        :returns: A list of region names selected for the nodes.
        """
        # sort candidate regions by distribution and covert it into a list
        candidates = sorted(regions.items(), key=lambda x: x[1]['weight'],
                            reverse=expand)
        sum_weight = sum(r['weight'] for r in regions.values())
        if expand:
            total = count + sum(current.values())
        else:
            total = sum(current.values()) - count
        remain = count
        plan = dict.fromkeys(regions.keys(), 0)

        for i in range(len(candidates)):
            region = candidates[i]
            r_name = region[0]
            r_weight = region[1]['weight']
            r_cap = region[1]['cap']

            # maximum number of nodes on current region
            q = total * r_weight / float(sum_weight)
            if expand:
                quota = int(math.ceil(q))
                # respect the cap setting, if any
                if r_cap >= 0:
                    quota = min(quota, r_cap)
                headroom = quota - current[r_name]
            else:
                quota = int(math.floor(q))
                headroom = current[r_name] - quota

            if headroom <= 0:
                continue

            if headroom < remain:
                plan[r_name] = headroom
                remain -= headroom
            else:
                plan[r_name] = remain if remain > 0 else 0
                remain = 0
                break

        # we have leftovers
        if remain > 0:
            return None

        result = {}
        for reg, count in plan.items():
            if count > 0:
                result[reg] = count

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
            # skip node if the context already contains a region_name
            profile = action.entity.rt['profile']
            if 'region_name' in profile.properties[profile.CONTEXT]:
                return 0
            else:
                return 1

        if action.action == consts.CLUSTER_RESIZE:
            if action.data.get('deletion', None):
                return -action.data['deletion']['count']
            elif action.data.get('creation', None):
                return action.data['creation']['count']

            cluster = action.entity
            curr = len(cluster.nodes)
            res = scaleutils.parse_resize_params(action, cluster, curr)
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
        :returns: ``None``.
        """
        count = self._get_count(cluster_id, action)
        if count == 0:
            return

        expand = True
        if count < 0:
            expand = False
            count = -count

        cluster = cm.Cluster.load(action.context, cluster_id)
        kc = self.keystone(cluster.user, cluster.project)

        regions_good = kc.validate_regions(self.regions.keys())
        if len(regions_good) == 0:
            action.data['status'] = base.CHECK_ERROR
            action.data['reason'] = _('No region is found usable.')
            LOG.error('No region is found usable.')
            return

        regions = {}
        for r in self.regions.items():
            if r[0] in regions_good:
                regions[r[0]] = r[1]

        current_dist = cluster.get_region_distribution(regions_good)
        result = self._create_plan(current_dist, regions, count, expand)
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
            action.data['creation']['regions'] = result
        else:
            if 'deletion' not in action.data:
                action.data['deletion'] = {}
            action.data['deletion']['count'] = count
            action.data['deletion']['regions'] = result
