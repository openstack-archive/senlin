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
Policy for placing nodes across availability zones.

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
          'zone': 'nova-1',
        },
        {
          'zone': 'nova-2',
        }
      ]
    }
  }
"""

import math
import operator
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


class ZonePlacementPolicy(base.Policy):
    """Policy for placing members of a cluster across availability zones."""

    VERSION = '1.0'

    TARGET = [
        # TODO(anyone): enable this to handle CLUSTER_RESIZE action
        ('BEFORE', consts.CLUSTER_SCALE_OUT),
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

        self._novaclient = None
        self.zones = dict((z[self.ZONE_NAME], z[self.ZONE_WEIGHT])
                          for z in self.properties.get(self.ZONES))

    def nova(self, obj):
        '''Construct nova client based on object.

        :param obj: Object for which the client is created. It is expected to
                    be None when retrieving an existing client. When creating
                    a client, it contains the user and project to be used.
        '''
        if self._novaclient is not None:
            return self._novaclient
        params = self._build_conn_params(obj)
        self._novaclient = driver_base.SenlinDriver().compute(params)
        return self._novaclient

    def _validate_zones(self, cluster):
        """check whether availability zones in spec are valid.

        :param cluster: the cluster object that policy attached to.
        :returns: A list of zones that are found available on Nova.
        """
        azs = self.nova(cluster).availability_zone_list()
        azs = [az['zoneName'] for az in azs if az['zoneState']['available']]

        avail = {}
        for name in self.zones:
            if name not in azs:
                LOG.warning(_LW('Availability zone %(az)s is not available.'),
                            {'az': name})
            else:
                avail[name] = self.zones[name]

        return avail

    def _get_current_dist(self, ctx, zones, cluster):
        """Calculate the availability zone distribution for exiting nodes.

        :param ctx: context used to access node details.
        :param zone_names: list of zone names to check.
        :param cluster: the cluster for which the distribution is checked.
        :returns: a dict containing zone-count pairs.
        """
        dist = dict.fromkeys(zones.keys(), 0)

        for node in cluster.nodes:
            details = node.get_details(ctx)
            zname = details.get('OS-EXT-AZ:availability_zone', None)
            if zname and zname in dist:
                dist[zname] += 1

        return dist

    def _create_plan(self, existing_dist, zones, count):
        """Compute a placement plan based on the weights of AZs.

        :param existing_dist: Distribution of existing nodes.
        :returns: A dict that contains a placement plan.
        """
        # sort candidate zones by distribution and covert it into a list
        candidates = sorted(zones.items(), key=operator.itemgetter(1))

        sum_weight = sum(zones.values())
        total = count + sum(existing_dist.values())
        remain = count
        plan = dict.fromkeys(zones.keys(), 0)

        for i in range(len(zones)):
            zone = candidates[i][0]
            weight = candidates[i][1]
            quota = int(math.ceil(round(total * weight / float(sum_weight))))
            headroom = quota - existing_dist[zone]

            if headroom <= 0:
                continue

            if headroom < remain:
                plan[zone] = headroom
                remain -= headroom
            else:
                plan[zone] = remain if remain > 0 else 0
                return plan

        # put the rest into the first bin
        if remain > 0:
            plan[candidates[0][0]] += remain

        return plan

    def pre_op(self, cluster_id, action):
        """Callback function when new nodes are to be created for a cluster.

        :param cluster_id: ID of the target cluster.
        :param action: The action that triggers this policy check.
        """
        pd = action.data.get('creation', {})
        if pd:
            count = pd.get('count', 1)
        else:
            # If no scaling policy is attached, use the input count directly
            count = action.inputs.get('count', 1)

        cluster = cluster_mod.Cluster.load(action.context, cluster_id)

        zones = self._validate_zones(cluster)
        if len(zones) == 0:
            action.data['status'] = base.CHECK_ERROR
            action.data['reason'] = _('No availability zone found available.')
            LOG.error(_LE('No availability zone found available.'))
            return

        # Calculate AZ distribution for exiting nodes
        current_dist = self._get_current_dist(action.context, zones, cluster)
        # Calculate placement plan for new nodes
        plan = self._create_plan(current_dist, zones, count)

        placement = action.data.get('placement', {})
        placement['count'] = count
        placement['placements'] = []

        for az, count in plan.items():
            if count > 0:
                entry = {'zone': az}
                placement['placements'].extend([entry] * count)

        action.data.update({'placement': placement})

        return
