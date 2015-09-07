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

from senlin.engine.actions import cluster_action
from senlin.tests.unit.common import base


class ClusterActionSizeCheckTest(base.SenlinTestCase):

    scenarios = [
        ('10_15_x_x', dict(
            desired=10, min_size=15, max_size=None, strict=True,
            result='ERROR',
            reason='The target capacity (10) is less than the specified '
                   'min_size (15).')),
        ('5_x10_x_x', dict(
            desired=5, min_size=None, max_size=None, strict=True,
            result='ERROR',
            reason='The target capacity (5) is less than the cluster\'s '
                   'min_size (10).')),
        ('30_x_25_x', dict(
            desired=30, min_size=None, max_size=25, strict=True,
            result='ERROR',
            reason='The target capacity (30) is greater than the specified '
                   'max_size (25).')),
        ('30_x_x20_x', dict(
            desired=30, min_size=None, max_size=None, strict=True,
            result='ERROR',
            reason='The target capacity (30) is greater than the cluster\'s '
                   'max_size (20).')),
        ('x_25_x20_x', dict(
            desired=None, min_size=25, max_size=None, strict=True,
            result='ERROR',
            reason='The specified min_size is greater than the current '
                   'max_size of the cluster.')),
        ('x_20_x_x', dict(
            desired=None, min_size=20, max_size=None, strict=True,
            result='ERROR',
            reason='The specified min_size is greater than the current '
                   'desired_capacity of the cluster.')),
        ('x_x_5_x', dict(
            desired=None, min_size=None, max_size=5, strict=True,
            result='ERROR',
            reason='The specified max_size is less than the current '
                   'min_size of the cluster.')),
        ('x_x_14_x', dict(
            desired=None, min_size=None, max_size=5, strict=True,
            result='ERROR',
            reason='The specified max_size is less than the current '
                   'min_size of the cluster.')),
        # The following are okay cases
        ('x_x_x_x', dict(
            desired=None, min_size=None, max_size=None, strict=True,
            result='OK',
            reason='')),
        ('18_x_x_x', dict(
            desired=18, min_size=None, max_size=None, strict=True,
            result='OK',
            reason='')),
        ('30_x_40_x', dict(
            desired=30, min_size=None, max_size=40, strict=True,
            result='OK',
            reason='')),
        ('x_x_40_x', dict(
            desired=None, min_size=None, max_size=40, strict=True,
            result='OK',
            reason='')),
        ('x_5_x_x', dict(
            desired=None, min_size=5, max_size=None, strict=True,
            result='OK',
            reason='')),
        ('x_15_x_x', dict(
            desired=None, min_size=15, max_size=None, strict=True,
            result='OK',
            reason='')),
        ('5_5_x_x', dict(
            desired=5, min_size=5, max_size=None, strict=True,
            result='OK',
            reason='')),
        ('20_x_x_x', dict(
            desired=20, min_size=None, max_size=None, strict=True,
            result='OK',
            reason='')),
        ('30_x_30_x', dict(
            desired=30, min_size=None, max_size=30, strict=True,
            result='OK',
            reason='')),
        ('30_x_-1_x', dict(
            desired=30, min_size=None, max_size=-1, strict=True,
            result='OK',
            reason='')),
        ('40_30_-1_x', dict(
            desired=40, min_size=30, max_size=-1, strict=True,
            result='OK',
            reason='')),
        ('x_x_-1_x', dict(
            desired=None, min_size=None, max_size=-1, strict=True,
            result='OK',
            reason='')),
    ]

    def test_check_size_params(self):
        cluster = mock.Mock()
        cluster.min_size = 10
        cluster.max_size = 20
        cluster.desired_capacity = 15
        cls = cluster_action.ClusterAction

        res, msg = cls.check_size_params(
            cluster, self.desired, self.min_size, self.max_size, self.strict)

        self.assertEqual(self.reason, msg)
        self.assertEqual(self.result, res)
