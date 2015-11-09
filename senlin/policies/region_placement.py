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
Policy for placing nodes across multiple regions.

NOTE: How placement policy works
Input:
  cluster: cluster whose nodes are to be manipulated.
  action.data['creation']:
    - count: number of nodes to create; it can be decision from a scaling
             policy. If no scaling policy is in effect, the count will be
             assumed to be 1.
Output:
  stored in action.data: A dictionary containing scheduling decisions made.
  {
    'status': 'OK',
    'placement': {
      'count': 2,
      'placements': [
        {
          'region': 'RegionOne',
        },
        {
          'region': 'RegionTwo',
        }
      ]
    }
  }
"""

import math
from oslo_log import log as logging

from senlin.common import consts
from senlin.common.i18n import _
from senlin.common.i18n import _LE
from senlin.common.i18n import _LW
from senlin.common import schema

from senlin.drivers import base as driver_base
from senlin.engine import cluster as cluster_mod

from senlin.policies import base

LOG = logging.getLogger(__name__)


class RegionPlacementPolicy(base.Policy):
    """Policy for placing members of a cluster across multiple regions."""

    VERSION = '1.0'

    TARGET = [
        # TODO(anyone): enable this to handle CLUSTER_RESIZE action
        ('BEFORE', consts.CLUSTER_SCALE_OUT),
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

    def keystone(self, obj):
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

    def _validate_regions(self, cluster):
        """check whether regions in spec are valid.

        :param cluster: the cluster object that policy attached to.
        :returns: A list of regions that are found available on Nova.
        """
        known_regions = [r['id'] for r in self.keystone(cluster).region_list()]

        regions = {}
        for r in self.regions:
            if r not in known_regions:
                LOG.warning(_LW('Region %s is not found.'), r)
            else:
                regions[r] = self.regions[r]

        return regions

    def _get_current_dist(self, regions, nodes):
        """Calculate the region distribution for exiting nodes.

        :param regions: list of regions to check.
        :param nodes: the nodes for which the distribution is checked.

        :returns: a dict containing region-count pairs.
        """
        dist = dict.fromkeys(regions.keys(), 0)

        for node in nodes:
            placement = node.data.get('placement', {})
            if placement and 'region_name' in placement:
                region = placement['region_name']
                dist[region] += 1

        return dist

    def _create_plan(self, current, regions, count):
        """Compute a placement plan based on the weights of regions.

        :param current: Distribution of existing nodes.
        :param regions: Usable regions for node creation.
        :param count: Number of nodes to create in this plan.

        :returns: A dict that contains a placement plan.
        """
        # sort candidate regions by distribution and covert it into a list
        candidates = sorted(regions.items(), key=lambda x: x[1]['weight'],
                            reverse=True)
        sum_weight = sum(r['weight'] for r in regions.values())
        total = count + sum(current.values())
        remain = count
        plan = dict.fromkeys(regions.keys(), 0)

        for i in range(len(candidates)):
            region = candidates[i]
            r_name = region[0]
            r_weight = region[1]['weight']
            r_cap = region[1]['cap']

            # maximum number of nodes on current region
            quota = int(math.ceil(total * r_weight / float(sum_weight)))
            # respect the cap setting, if any
            if r_cap >= 0:
                quota = min(quota, r_cap)
            # number of nodes that can be allocated to region candidates[i]
            headroom = quota - current[r_name]

            if headroom <= 0:
                continue

            if headroom < remain:
                plan[r_name] = headroom
                remain -= headroom
            else:
                plan[r_name] = remain if remain > 0 else 0
                return plan

        # we have leftovers that cannot fit into any region
        if remain > 0:
            return None

        return plan

    def pre_op(self, cluster_id, action):
        """Callback function when new nodes are to be created for a cluster.

        :param cluster_id: ID of the target cluster.
        :param action: The action that triggers this policy check.
        :returns: ``None``.
        """
        pd = action.data.get('creation', None)
        if pd:
            count = pd.get('count', 1)
        else:
            # If no scaling policy is attached, use the input count directly
            count = action.inputs.get('count', 1)

        cluster = cluster_mod.Cluster.load(action.context, cluster_id)

        regions = self._validate_regions(cluster)
        if len(regions) == 0:
            action.data['status'] = base.CHECK_ERROR
            action.data['reason'] = _('No region is found usable.')
            LOG.error(_LE('No region is found usable.'))
            return

        # Calculate AZ distribution for exiting nodes
        current_dist = self._get_current_dist(regions, cluster.nodes)

        # Calculate placement plan for new nodes
        plan = self._create_plan(current_dist, regions, count)
        if plan is None:
            action.data['status'] = base.CHECK_ERROR
            action.data['reason'] = _('There is no feasible plan to '
                                      'accommodate all nodes.')
            LOG.error(_LE('There is no feasible plan to accommodate all '
                          'nodes.'))
            return

        placement = action.data.get('placement', {})
        placement['count'] = count
        placement['placements'] = []

        for az, count in plan.items():
            if count > 0:
                entry = {'region_name': az}
                placement['placements'].extend([entry] * count)

        action.data.update({'placement': placement})

        return
