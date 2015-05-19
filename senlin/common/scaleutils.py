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
    elif adj_type == consts.CHANGE_IN_PERCENTAGE:
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
            desired = rounded

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
