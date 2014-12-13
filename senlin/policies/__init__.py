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
# These levels map directly to logging levels but have slightly different
# intentions and interpretations:
#
#  - CRITICAL: a cluster is in inconsistent state that cannot be recovered
#              using Senlin API calls, thus a manual intervention is needed.
#              Violating a policy at this level means the cluster should
#              not be treated functional any more.
#
#  - ERROR:    a cluster is in consistent state that can be recovered using
#              Senlin API calls, for example, the cluster can be destroyed.
#              Violating a policy at this level will render the cluster to an
#              'ERROR' status.
#
#  - WARNING:  the cluster as a whole is still functional, but the violation
#              of a policy at this level needs attention.
#
#  - INFO:     the cluster is functioning healthily, the violation of a policy
#              at this level will be logged as events generated above this
#              level.
#
#  - DEBUG:    a policy at this level is only used for debugging's purpose.
#              It cannot affect the normal operation of a cluster. A log
#              entry is generated only when the DEBUG mode is turned on.

CRITICAL = 50
ERROR = 40
WARNING = 30
INFO = 20
DEBUG = 10

_levelNames = {
    CRITICAL: 'CRITICAL',
    ERROR: 'ERROR',
    WARNING: 'WARNING',
    INFO: 'INFO',
    DEBUG: 'DEBUG',
    'CRITICAL': CRITICAL,
    'ERROR': ERROR,
    'WARNING': WARNING,
    'INFO': INFO,
    'DEBUG': DEBUG,
}


def getLevelName(level):
    '''
    Return a level name if given a numeric value; or return a value if given
    a string.  If level is not predefined, "Level %s" will be returned.
    '''
    return _levelNames.get(level, ("Level %s" % level))
