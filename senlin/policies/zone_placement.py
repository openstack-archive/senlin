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

NOTE: How this policy works
Input:
  cluster: cluster whose nodes are to be manipulated.
  action.data['creation']:
    - count: number of nodes to create. It can be decision from a scaling
             policy. If no scaling policy is in effect, the count will be
             assumed to be 1.
  action.data['deleteion']:
    - count: number of nodes to delete. It can be decision from a scaling
             policy. If no scaling policy is in effect, the count will be
             assumed to be 1.
Output:
  action.data: A dictionary containing scheduling decisions made.

  For actions that increase the size of a cluster, the output looks like::

  {
    'status': 'OK',
    'creation': {
      'count': 2,
      'zones': {'nova-1': 1, 'nova-2': 1}
     }
  }

  For actions that decrease the size of a cluster, the output looks like::

  {
    'status': 'OK',
    'deletion': {
      'count': 3,
      'zones': {'nova-1': 2, 'nova-2': 1}
     }
  }

"""

import math
import operator
from oslo_log import log as logging

from senlin.common import consts
from senlin.common.i18n import _
from senlin.common.i18n import _LE
from senlin.common import schema

from senlin.drivers import base as driver_base
from senlin.engine import cluster as cluster_mod

from senlin.policies import base

LOG = logging.getLogger(__name__)


class ZonePlacementPolicy(base.Policy):
    """Policy for placing members of a cluster across availability zones."""

    VERSION = '1.0'

    PRIORITY = 300

    TARGET = [
        # TODO(anyone): enable this to handle CLUSTER_RESIZE action
        ('BEFORE', consts.CLUSTER_SCALE_OUT),
        ('BEFORE', consts.CLUSTER_SCALE_IN),
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

    def _nova(self, obj):
        """Construct nova client based on object.

        :param obj: Object for which the client is created. It is expected to
                    be None when retrieving an existing client. When creating
                    a client, it contains the user and project to be used.
        """
        if self._novaclient is not None:
            return self._novaclient

        params = self._build_conn_params(obj)
        self._novaclient = driver_base.SenlinDriver().compute(params)
        return self._novaclient

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

    def pre_op(self, cluster_id, action):
        """Callback function when cluster membership is about to change.

        :param cluster_id: ID of the target cluster.
        :param action: The action that triggers this policy check.
        """

        count = action.inputs.get('count', None)
        if action.action == consts.CLUSTER_SCALE_IN:
            expand = False
            if not count:
                pd = action.data.get('deletion', None)
                count = pd.get('count', 1) if pd else 1
        else:
            expand = True
            if not count:
                pd = action.data.get('creation', None)
                count = pd.get('count', 1) if pd else 1

        cluster = cluster_mod.Cluster.load(action.context, cluster_id)

        nc = self._nova(cluster)
        zones_good = nc.validate_azs(self.zones.keys())
        if len(zones_good) == 0:
            action.data['status'] = base.CHECK_ERROR
            action.data['reason'] = _('No availability zone found available.')
            LOG.error(_LE('No availability zone found available.'))
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
            LOG.error(_LE('There is no feasible plan to handle all nodes.'))
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
