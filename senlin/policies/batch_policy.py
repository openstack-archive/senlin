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
Policy for batching operations on a cluster.

NOTE: How update policy works
Input:
  cluster: the cluste whose nodes are to be updated.
Output:
  stored in action.data: A dictionary containing a detailed update schedule.
  {
    'status': 'OK',
    'update': {
      'pause_time': 2,
      'plan': [{
          'node-id-1',
          'node-id-2',
        }, {
          'node-id-3',
          'node-id-4',
        }, {
          'node-id-5',
        }
      ]
    }
  }
"""

from senlin.common import consts
from senlin.common.i18n import _
from senlin.common import schema
from senlin.policies import base


class BatchPolicy(base.Policy):
    """Policy for batching the operations on a cluster's nodes."""

    VERSION = '1.0'

    TARGET = [
        ('BEFORE', consts.CLUSTER_UPDATE),
    ]

    PROFILE_TYPE = [
        'ANY'
    ]

    KEYS = (
        MIN_IN_SERVICE, MAX_BATCH_SIZE, PAUSE_TIME,
    ) = (
        'min_in_service', 'max_batch_size', 'pause_time',
    )

    properties_schema = {
        MIN_IN_SERVICE: schema.Integer(
            _('Minimum number of nodes in service when performing updates.'),
            default=1,
        ),
        MAX_BATCH_SIZE: schema.Integer(
            _('Maximum number of nodes that can be updated at the same '
              'time.'),
            default=-1,
        ),
        PAUSE_TIME: schema.Integer(
            _('Number of seconds between update batches if any.'),
            default=60,
        )
    }

    def __init__(self, name, spec, **kwargs):
        super(BatchPolicy, self).__init__(name, spec, **kwargs)

        self.min_in_service = self.properties[self.MIN_IN_SERVICE]
        self.max_batch_size = self.properties[self.MAX_BATCH_SIZE]
        self.pause_time = self.properties[self.PAUSE_TIME]

    def pre_op(self, cluster_id, action):
        # TODO(anyone): compute batches
        action.data['candidates'] = []
        action.store(action.context)

        return True

    def post_op(self, cluster_id, action):
        # TODO(anyone): handle pause_time here
        return True
