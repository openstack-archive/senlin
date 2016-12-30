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

import mock

from senlin.engine.actions import base as ab
from senlin.engine.actions import cluster_action as ca
from senlin.engine import cluster as cm
from senlin.engine import scheduler
from senlin.tests.unit.common import base
from senlin.tests.unit.common import utils


class ClusterActionWaitTest(base.SenlinTestCase):
    scenarios = [
        ('wait_ready', dict(
            statuses=[
                ab.Action.WAITING,
                ab.Action.READY
            ],
            cancelled=[False, False],
            timeout=[False, False],
            failed=[False, False],
            code=ab.Action.RES_OK,
            rescheduled_times=1,
            message='All dependents ended with success')
         ),
        ('wait_fail', dict(
            statuses=[
                ab.Action.WAITING,
                ab.Action.FAILED
            ],
            cancelled=[False, False],
            timeout=[False, False],
            code=ab.Action.RES_ERROR,
            rescheduled_times=1,
            message='ACTION [FAKE_ID] failed')
         ),
        ('wait_wait_cancel', dict(
            statuses=[
                ab.Action.WAITING,
                ab.Action.WAITING,
                ab.Action.WAITING,
            ],
            cancelled=[False, False, True],
            timeout=[False, False, False],
            code=ab.Action.RES_CANCEL,
            rescheduled_times=2,
            message='ACTION [FAKE_ID] cancelled')
         ),
        ('wait_wait_timeout', dict(
            statuses=[
                ab.Action.WAITING,
                ab.Action.WAITING,
                ab.Action.WAITING,
            ],
            cancelled=[False, False, False],
            timeout=[False, False, True],
            code=ab.Action.RES_TIMEOUT,
            rescheduled_times=2,
            message='ACTION [FAKE_ID] timeout')
         ),

    ]

    def setUp(self):
        super(ClusterActionWaitTest, self).setUp()
        self.ctx = utils.dummy_context()

    @mock.patch.object(cm.Cluster, 'load')
    @mock.patch.object(scheduler, 'reschedule')
    def test_wait_dependents(self, mock_reschedule, mock_load):
        action = ca.ClusterAction('ID', 'ACTION', self.ctx)
        action.id = 'FAKE_ID'
        self.patchobject(action, 'get_status', side_effect=self.statuses)
        self.patchobject(action, 'is_cancelled', side_effect=self.cancelled)
        self.patchobject(action, 'is_timeout', side_effect=self.timeout)

        res_code, res_msg = action._wait_for_dependents()
        self.assertEqual(self.code, res_code)
        self.assertEqual(self.message, res_msg)
        self.assertEqual(self.rescheduled_times, mock_reschedule.call_count)
