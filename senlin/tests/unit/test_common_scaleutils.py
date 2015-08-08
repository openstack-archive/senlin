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

from senlin.common import consts
from senlin.common import scaleutils as su
from senlin.tests.unit.common import base


class ScaleUtilsTest(base.SenlinTestCase):

    def test_calculate_desired_exact(self):
        # EXACT_CAPACITY
        for i in range(10):
            desired = self.getUniqueInteger()
            res = su.calculate_desired(0, consts.EXACT_CAPACITY, desired, None)
            self.assertEqual(desired, res)

    def test_calculate_desired_capacity(self):
        # CHANGE_IN_CAPACITY
        for i in range(10):
            current = self.getUniqueInteger()
            for j in range(10):
                number = self.getUniqueInteger()
                res = su.calculate_desired(current, consts.CHANGE_IN_CAPACITY,
                                           number, None)
                self.assertEqual(current+number, res)

    def test_calculate_desired_percentage_positive(self):
        # CHANGE_IN_PERCENTAGE, positive
        res = su.calculate_desired(10, consts.CHANGE_IN_PERCENTAGE, 10, None)
        self.assertEqual(11, res)

        res = su.calculate_desired(10, consts.CHANGE_IN_PERCENTAGE, 15, None)
        self.assertEqual(11, res)

        res = su.calculate_desired(10, consts.CHANGE_IN_PERCENTAGE, 22, None)
        self.assertEqual(12, res)

        res = su.calculate_desired(10, consts.CHANGE_IN_PERCENTAGE, 1, None)
        self.assertEqual(11, res)

    def test_calculate_desired_percentage_negative(self):
        # CHANGE_IN_PERCENTAGE, negative
        res = su.calculate_desired(10, consts.CHANGE_IN_PERCENTAGE, -10, None)
        self.assertEqual(9, res)

        res = su.calculate_desired(10, consts.CHANGE_IN_PERCENTAGE, -15, None)
        self.assertEqual(9, res)

        res = su.calculate_desired(10, consts.CHANGE_IN_PERCENTAGE, -22, None)
        self.assertEqual(8, res)

        res = su.calculate_desired(10, consts.CHANGE_IN_PERCENTAGE, -1, None)
        self.assertEqual(9, res)

    def test_calculate_desired_percentage_with_min_step(self):
        # CHANGE_IN_PERCENTAGE, with min_step 0
        res = su.calculate_desired(10, consts.CHANGE_IN_PERCENTAGE, 10, 0)
        self.assertEqual(11, res)
        res = su.calculate_desired(10, consts.CHANGE_IN_PERCENTAGE, -10, 0)
        self.assertEqual(9, res)
        res = su.calculate_desired(10, consts.CHANGE_IN_PERCENTAGE, 1, 0)
        self.assertEqual(11, res)
        res = su.calculate_desired(10, consts.CHANGE_IN_PERCENTAGE, -1, 0)
        self.assertEqual(9, res)

        # CHANGE_IN_PERCENTAGE, with min_step 1
        res = su.calculate_desired(10, consts.CHANGE_IN_PERCENTAGE, 10, 1)
        self.assertEqual(11, res)
        res = su.calculate_desired(10, consts.CHANGE_IN_PERCENTAGE, -10, 1)
        self.assertEqual(9, res)
        res = su.calculate_desired(10, consts.CHANGE_IN_PERCENTAGE, 1, 1)
        self.assertEqual(11, res)
        res = su.calculate_desired(10, consts.CHANGE_IN_PERCENTAGE, -1, 1)
        self.assertEqual(9, res)

        # CHANGE_IN_PERCENTAGE, with min_step 2
        res = su.calculate_desired(10, consts.CHANGE_IN_PERCENTAGE, 10, 2)
        self.assertEqual(12, res)
        res = su.calculate_desired(10, consts.CHANGE_IN_PERCENTAGE, -10, 2)
        self.assertEqual(8, res)
        res = su.calculate_desired(10, consts.CHANGE_IN_PERCENTAGE, 1, 2)
        self.assertEqual(12, res)
        res = su.calculate_desired(10, consts.CHANGE_IN_PERCENTAGE, -1, 2)
        self.assertEqual(8, res)

    def test_truncate_desired(self):
        cluster = mock.Mock()
        cluster.min_size = 10
        cluster.max_size = 50

        # No constraints
        for desired in [10, 11, 12, 49, 50]:
            actual = su.truncate_desired(cluster, desired, None, None)
            self.assertEqual(desired, actual)

        # min_size specified
        actual = su.truncate_desired(cluster, 10, 20, None)
        self.assertEqual(20, actual)

        # min_size None
        actual = su.truncate_desired(cluster, 5, None, None)
        self.assertEqual(10, actual)

        # max_size specified
        actual = su.truncate_desired(cluster, 20, None, -1)
        self.assertEqual(20, actual)

        actual = su.truncate_desired(cluster, 15, None, 30)
        self.assertEqual(15, actual)

        actual = su.truncate_desired(cluster, 40, None, 30)
        self.assertEqual(30, actual)

        # max_size not specified
        actual = su.truncate_desired(cluster, 40, None, None)
        self.assertEqual(40, actual)

        actual = su.truncate_desired(cluster, 60, None, None)
        self.assertEqual(50, actual)
