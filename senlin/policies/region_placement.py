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

NOTE: How placement policy works
Input:
  cluster: cluster whose nodes are to be manipulated.
  action.data['creation']:
    - count: number of nodes to create; it can be decision from a scaling
             policy. If no scaling policy is in effect, the count will be
             assumed to be 1.
  action.data['deletion']:
    - count: number of nodes to delete. It can be a decision from a scaling
             policy. If there is no scaling policy in effect, we assume the
             count value to be 1.
Output:
  action.data: A dictionary containing scheduling decisions made.

  For actions that increase the size of a cluster, the output will look like::

  {
    'status': 'OK',
    'creation': {
      'count': 2,
      'regions': {'RegionOne': 1, 'RegionTwo': 1}
    }
  }

  For actions that shrink the size of a cluster, the output will look like::

  {
    'status': 'OK',
    'deletion': {
      'count': 3,
      'regions': {'RegionOne': 1, 'RegionTwo': 2}
    }
  }

"""

import math
from oslo_log import log as logging

from senlin.common import consts
from senlin.common.i18n import _
from senlin.common.i18n import _LE
from senlin.common import schema

from senlin.drivers import base as driver_base
from senlin.engine import cluster as cluster_mod

from senlin.policies import base

LOG = logging.getLogger(__name__)


class RegionPlacementPolicy(base.Policy):
    """Policy for placing members of a cluster across multiple regions."""

    VERSION = '1.0'

    PRIORITY = 200

    TARGET = [
        # TODO(anyone): enable this to handle CLUSTER_RESIZE action
        ('BEFORE', consts.CLUSTER_SCALE_OUT),
        ('BEFORE', consts.CLUSTER_SCALE_IN),
    ]

    PROFILE_TYPE = [
        'os.nova.server-1.0',
        'os.heat.stack-1.0',
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

        self._keystoneclient = None
        regions = {}
        for r in self.properties.get(self.REGIONS):
            regions[r[self.REGION_NAME]] = {
                'weight': r[self.REGION_WEIGHT],
                'cap': r[self.REGION_CAP],
            }
        self.regions = regions

    def _keystone(self, obj):
        """Construct keystone client based on object.

        :param obj: Object for which the client is created. It is expected to
                    be None when retrieving an existing client. When creating
                    a client, it contains the user and project to be used.
        """
        if self._keystoneclient is not None:
            return self._keystoneclient
        params = self._build_conn_params(obj)
        self._keystoneclient = driver_base.SenlinDriver().identity(params)
        return self._keystoneclient

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

    def pre_op(self, cluster_id, action):
        """Callback function when cluster membership is about to change.

        :param cluster_id: ID of the target cluster.
        :param action: The action that triggers this policy check.
        :returns: ``None``.
        """
        if action.action == consts.CLUSTER_SCALE_IN:
            expand = False
            # use action input directly if available
            count = action.inputs.get('count', None)
            if not count:
                # check if policy decisions available
                pd = action.data.get('deletion', None)
                count = pd.get('count', 1) if pd else 1
        else:
            # this is an action that inflates the cluster
            expand = True
            count = action.inputs.get('count', None)
            if not count:
                # check if policy decisions available
                pd = action.data.get('creation', None)
                count = pd.get('count', 1) if pd else 1

        cluster = cluster_mod.Cluster.load(action.context, cluster_id)

        kc = self._keystone(cluster)

        regions_good = kc.validate_regions(self.regions.keys())
        if len(regions_good) == 0:
            action.data['status'] = base.CHECK_ERROR
            action.data['reason'] = _('No region is found usable.')
            LOG.error(_LE('No region is found usable.'))
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
            LOG.error(_LE('There is no feasible plan to handle all nodes.'))
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
