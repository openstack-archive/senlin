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

'''
Utilities for scaling actions and related policies.
'''

import math
import random

from oslo_log import log as logging

from senlin.common import consts
from senlin.common.i18n import _

LOG = logging.getLogger(__name__)


def calculate_desired(current, adj_type, number, min_step):
    '''Calculate desired capacity based on the type and number values.'''

    if adj_type == consts.EXACT_CAPACITY:
        desired = number
    elif adj_type == consts.CHANGE_IN_CAPACITY:
        desired = current + number
    else:   # consts.CHANGE_IN_PERCENTAGE:
        delta = (number * current) / 100.0
        if delta > 0.0:
            rounded = int(math.ceil(delta) if math.fabs(delta) < 1.0
                          else math.floor(delta))
        else:
            rounded = int(math.floor(delta) if math.fabs(delta) < 1.0
                          else math.ceil(delta))

        if min_step is not None and min_step > abs(rounded):
            adjust = min_step if rounded > 0 else -min_step
            desired = current + adjust
        else:
            desired = current + rounded

    return desired


def truncate_desired(cluster, desired, min_size, max_size):
    '''Do truncation of desired capacity for non-strict cases.'''

    if min_size is not None and desired < min_size:
        desired = min_size
        LOG.debug(_("Truncating shrinkage to specified min_size (%s).")
                  % desired)

    if min_size is None and desired < cluster.min_size:
        desired = cluster.min_size
        LOG.debug(_("Truncating shrinkage to cluster's min_size (%s).")
                  % desired)

    if max_size is not None and max_size > 0 and desired > max_size:
        desired = max_size
        LOG.debug(_("Truncating growth to specified max_size (%s).")
                  % desired)

    if (max_size is None and desired > cluster.max_size and
            cluster.max_size > 0):
        desired = cluster.max_size
        LOG.debug(_("Truncating growth to cluster's max_size (%s).")
                  % desired)

    return desired


def check_size_params(cluster=None, desired=None, min_size=None, max_size=None,
                      strict=False):
    """Validate provided arguments against cluster properties.

    Sanity Checking 1: the desired, min_size, max_size parameters must
                       form a reasonable relationship among themselves,
                       if specified.
    Sanity Checking 2: the desired_capacity must be within the existing
                       range of the cluster, if new range is not provided.

    :param cluster: The cluster object if provided.
    :param desired: The desired capacity for an operation if provided.
    :param min_size: The new min_size property for the cluster, if provided.
    :param max_size: The new max_size property for the cluster, if provided.
    :param strict: Whether we are doing a strict checking.

    :return: A string of error message if failed checking or None if passed
        the checking.
    """

    if desired is not None:
        # recalculate/validate desired based on strict setting
        if (min_size is not None and desired < min_size):
            v = {'d': desired, 'm': min_size}
            return _("The target capacity (%(d)s) is less than "
                     "the specified min_size (%(m)s).") % v

        if (min_size is None and cluster is not None and
                desired < cluster.min_size and strict):
            v = {'d': desired, 'm': cluster.min_size}
            return _("The target capacity (%(d)s) is less than "
                     "the cluster's min_size (%(m)s).") % v

        if (max_size is not None and desired > max_size and
                max_size >= 0):
            v = {'d': desired, 'm': max_size}
            return _("The target capacity (%(d)s) is greater "
                     "than the specified max_size (%(m)s).") % v

        if (max_size is None and cluster is not None and
                desired > cluster.max_size and
                cluster.max_size >= 0 and strict):
            v = {'d': desired, 'm': cluster.max_size}
            return _("The target capacity (%(d)s) is greater "
                     "than the cluster's max_size (%(m)s).") % v

    if min_size is not None:
        if max_size is not None and max_size >= 0 and min_size > max_size:
            v = {'n': min_size, 'm': max_size}
            return _("The specified min_size (%(n)s) is greater than the "
                     "specified max_size (%(m)s).") % v

        if (max_size is None and cluster is not None and
                cluster.max_size >= 0 and min_size > cluster.max_size):
            v = {'n': min_size, 'm': cluster.max_size}
            return _("The specified min_size (%(n)s) is greater than the "
                     "current max_size (%(m)s) of the cluster.") % v

        if (desired is None and cluster is not None and
                min_size > cluster.desired_capacity and strict):
            v = {'n': min_size, 'd': cluster.desired_capacity}
            return _("The specified min_size (%(n)s) is greater than the "
                     "current desired_capacity (%(d)s) of the cluster.") % v

    if max_size is not None:
        if (min_size is None and cluster is not None and
                max_size >= 0 and max_size < cluster.min_size):
            v = {'m': max_size, 'n': cluster.min_size}
            return _("The specified max_size (%(m)s) is less than the "
                     "current min_size (%(n)s) of the cluster.") % v

        if (desired is None and cluster is not None and
                max_size >= 0 and max_size < cluster.desired_capacity and
                strict):
            v = {'m': max_size, 'd': cluster.desired_capacity}
            return _("The specified max_size (%(m)s) is less than the "
                     "current desired_capacity (%(d)s) of the cluster.") % v

    return None


def parse_resize_params(action, cluster):
    '''Parse the parameters of CLUSTER_RESIZE action.'''

    adj_type = action.inputs.get(consts.ADJUSTMENT_TYPE, None)
    number = action.inputs.get(consts.ADJUSTMENT_NUMBER, None)
    min_size = action.inputs.get(consts.ADJUSTMENT_MIN_SIZE, None)
    max_size = action.inputs.get(consts.ADJUSTMENT_MAX_SIZE, None)
    min_step = action.inputs.get(consts.ADJUSTMENT_MIN_STEP, None)
    strict = action.inputs.get(consts.ADJUSTMENT_STRICT, False)

    desired = cluster.desired_capacity
    if adj_type is not None:
        # number must be not None according to previous tests
        desired = calculate_desired(desired, adj_type, number, min_step)

    # truncate adjustment if permitted (strict==False)
    if strict is False:
        desired = truncate_desired(cluster, desired, min_size, max_size)

    # check provided params against current properties
    # desired is checked when strict is True
    result = check_size_params(cluster, desired, min_size, max_size, strict)
    if result:
        return action.RES_ERROR, result

    # save sanitized properties
    current_size = cluster.desired_capacity
    count = current_size - desired
    if count > 0:
        action.data.update({
            'deletion': {
                'count': count,
            }
        })
    else:
        action.data.update({
            'creation': {
                'count': abs(count),
            }
        })

    return action.RES_OK, ''


def filter_error_nodes(nodes):
    """Filter out ERROR nodes from the given node list.

    :param nodes: candidate nodes for filter.
    :param count: maximum number of nodes for selection.
    :return: a tuple containing the chosen nodes' IDs and the undecided
             (good) nodes.
    """
    good = []
    bad = []
    for n in nodes:
        if n.status == 'ERROR':
            bad.append(n.id)
        else:
            good.append(n)

    return bad, good


def nodes_by_random(nodes, count):
    """Select nodes based on random number.

    :param nodes: list of candidate nodes.
    :param count: maximum number of nodes for selection.
    :return: a list of IDs for victim nodes.
    """
    selected, candidates = filter_error_nodes(nodes)
    if count <= len(selected):
        return selected[:count]

    count -= len(selected)
    random.seed()

    i = count
    while i > 0:
        rand = random.randrange(len(candidates))
        selected.append(candidates[rand].id)
        candidates.remove(candidates[rand])
        i = i - 1

    return selected


def nodes_by_age(nodes, count, old_first):
    """Select nodes based on node creation time.

    :param nodes: list of candidate nodes.
    :param count: maximum number of nodes for selection.
    :param old_first: whether old nodes should appear before young ones.
    :return: a list of IDs for victim nodes.
    """
    selected, candidates = filter_error_nodes(nodes)
    if count <= len(selected):
        return selected[:count]

    count -= len(selected)
    sorted_list = sorted(candidates, key=lambda r: r.created_at)
    for i in range(count):
        if old_first:
            selected.append(sorted_list[i].id)
        else:  # YOUNGEST_FIRST
            selected.append(sorted_list[-1 - i].id)
    return selected


def nodes_by_profile_age(nodes, count):
    """Select nodes based on node profile creation time.

    Note that old nodes will come before young ones.

    :param nodes: list of candidate nodes.
    :param count: maximum number of nodes for selection.
    :return: a list of IDs for victim nodes.
    """
    selected, nodes = filter_error_nodes(nodes)
    if count <= len(selected):
        return selected[:count]

    count -= len(selected)
    node_map = []
    for node in nodes:
        entry = {
            'id': node.id,
            'created_at': node.rt['profile'].created_at
        }
        node_map.append(entry)

    sorted_map = sorted(node_map, key=lambda m: m['created_at'])
    for i in range(count):
        selected.append(sorted_map[i]['id'])

    return selected
