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


# Default enforcement levels and level names.
#
#  - MUST: A policy of this enforcement level must be strictly checked. A
#          violation of such a policy will lead a cluster to ``CRITICAL``
#          status, which means that the cluster is in a problematic status
#          that cannot be recovered using Senlin APIs. A manual intervention
#          is needed. Such a cluster should not be treated as funtional any
#          more.
#
#  - SHOULD: A violation of a policy at this enforcement level will render a
#            cluster into an ``ERROR`` status. A manual intervention is needed
#            to recover the cluster. The cluster may and may not be providing
#            services in the ``ERROR`` status.
#
#  - WOULD: A policy of this enforcement level is usually about some
#           operations that would be done when the policy is enforced. A
#           violation of the policy will leave the cluster in a ``WARNING``
#           status, which means that the cluster is still operational, but
#           there are unsucessful operations attempted.
#
#  - MIGHT: A policy of this enforcement level is usually associated with
#           certain operations that may or may not be done. A violation of
#           this policy will not cause any negative impact to the cluster.
#

MUST = 50
SHOULD = 40
WOULD = 30
MIGHT = 20

_levelNames = {
    MUST: 'MUST',
    SHOULD: 'SHOULD',
    WOULD: 'WOULD',
    MIGHT: 'MIGHT',
    'MUST': MUST,
    'SHOULD': SHOULD,
    'WOULD': WOULD,
    'MIGHT': MIGHT,
}


def getLevelName(level):
    '''Get a level name or number.

    Return a level name if given a numeric value; or return a value if given
    a string.  If level is not predefined, "Level %s" will be returned.
    '''
    return _levelNames.get(level, ("Level %s" % level))
