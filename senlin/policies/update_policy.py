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
Policy for updating a cluster.
'''

'''
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
'''

from senlin.common import consts
from senlin.common.i18n import _
from senlin.common import schema
from senlin.policies import base


class UpdatePolicy(base.Policy):
    '''Policy for updating a cluster's node profile.

    Note that we differentiate the updates to the size(scale) of a cluster from
    the updates to the node profile.  The former is handled by CreatePolicy,
    DeletePolicy.
    '''

    __type_name__ = 'UpdatePolicy'

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

    spec_schema = {
        MIN_IN_SERVICE: schema.Integer(
            _('Minimum number of nodes in service when performing updates.'),
            default=1,
        ),
        MAX_BATCH_SIZE: schema.Integer(
            _('Maximum number of nodes that can be updated at the same '
              'time.'),
        ),
        PAUSE_TIME: schema.Integer(
            _('Number of seconds between update batches if any.'),
        )
    }

    def __init__(self, type_name, name, **kwargs):
        super(UpdatePolicy, self).__init__(type_name, name, **kwargs)

        self.min_in_service = self.spec.get('min_in_service')
        self.max_batch_size = self.spec.get('max_batch_size')
        self.pause_time = self.spec.get('pause_time')

    def pre_op(self, cluster_id, action):
        # TODO(anyone): compute batches
        action.data['candidates'] = []
        action.store(action.context)

        return True

    def post_op(self, cluster_id, action):
        # TODO(anyone): handle pause_time here
        return True
