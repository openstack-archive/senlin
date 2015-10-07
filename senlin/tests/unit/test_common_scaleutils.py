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
from senlin.common.i18n import _
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

    def test_parse_resize_params(self):
        action = mock.Mock()
        cluster = mock.Mock()
        # delete nodes
        action.inputs = {
            consts.ADJUSTMENT_TYPE: consts.EXACT_CAPACITY,
            consts.ADJUSTMENT_NUMBER: 4,
            consts.ADJUSTMENT_MIN_SIZE: 3,
            consts.ADJUSTMENT_MAX_SIZE: 10,
            consts.ADJUSTMENT_MIN_STEP: None,
            consts.ADJUSTMENT_STRICT: True,
        }
        action.data = {}
        action.RES_OK = 'OK'
        cluster.desired_capacity = 6
        result, reason = su.parse_resize_params(action, cluster)
        self.assertEqual('OK', result)
        self.assertEqual('', reason)
        self.assertEqual({'deletion': {'count': 2}}, action.data)
        # create nodes
        action.inputs = {
            consts.ADJUSTMENT_TYPE: consts.EXACT_CAPACITY,
            consts.ADJUSTMENT_NUMBER: 9,
            consts.ADJUSTMENT_MIN_SIZE: 3,
            consts.ADJUSTMENT_MAX_SIZE: 10,
            consts.ADJUSTMENT_MIN_STEP: None,
            consts.ADJUSTMENT_STRICT: True,
        }
        action.data = {}
        result, reason = su.parse_resize_params(action, cluster)
        self.assertEqual('OK', result)
        self.assertEqual('', reason)
        self.assertEqual({'creation': {'count': 3}}, action.data)
        #  resize params are incorrect.
        action.inputs = {
            consts.ADJUSTMENT_TYPE: consts.EXACT_CAPACITY,
            consts.ADJUSTMENT_NUMBER: 11,
            consts.ADJUSTMENT_MIN_SIZE: 3,
            consts.ADJUSTMENT_MAX_SIZE: 10,
            consts.ADJUSTMENT_MIN_STEP: None,
            consts.ADJUSTMENT_STRICT: True,
        }
        action.data = {}
        action.RES_ERROR = 'ERROR'
        result, reason = su.parse_resize_params(action, cluster)
        self.assertEqual('ERROR', result)
        msg = _('The target capacity (11) is greater than '
                'the specified max_size (10).')
        self.assertEqual(msg, reason)


class CheckSizeParamsTest(base.SenlinTestCase):

    scenarios = [
        ('10_15_x_x', dict(
            desired=10, min_size=15, max_size=None, strict=True,
            result='The target capacity (10) is less than the specified '
                   'min_size (15).')),
        ('5_x10_x_x', dict(
            desired=5, min_size=None, max_size=None, strict=True,
            result='The target capacity (5) is less than the cluster\'s '
                   'min_size (10).')),
        ('30_x_25_x', dict(
            desired=30, min_size=None, max_size=25, strict=True,
            result='The target capacity (30) is greater than the specified '
                   'max_size (25).')),
        ('30_x_x20_x', dict(
            desired=30, min_size=None, max_size=None, strict=True,
            result='The target capacity (30) is greater than the cluster\'s '
                   'max_size (20).')),
        ('x_25_x20_x', dict(
            desired=None, min_size=25, max_size=None, strict=True,
            result='The specified min_size is greater than the current '
                   'max_size of the cluster.')),
        ('x_20_x_x', dict(
            desired=None, min_size=20, max_size=None, strict=True,
            result='The specified min_size is greater than the current '
                   'desired_capacity of the cluster.')),
        ('x_x_5_x', dict(
            desired=None, min_size=None, max_size=5, strict=True,
            result='The specified max_size is less than the current '
                   'min_size of the cluster.')),
        ('x_x_14_x', dict(
            desired=None, min_size=None, max_size=5, strict=True,
            result='The specified max_size is less than the current '
                   'min_size of the cluster.')),
        # The following are okay cases
        ('x_x_x_x', dict(
            desired=None, min_size=None, max_size=None, strict=True,
            result='')),
        ('18_x_x_x', dict(
            desired=18, min_size=None, max_size=None, strict=True,
            result='')),
        ('30_x_40_x', dict(
            desired=30, min_size=None, max_size=40, strict=True,
            result='')),
        ('x_x_40_x', dict(
            desired=None, min_size=None, max_size=40, strict=True,
            result='')),
        ('x_5_x_x', dict(
            desired=None, min_size=5, max_size=None, strict=True,
            result='')),
        ('x_15_x_x', dict(
            desired=None, min_size=15, max_size=None, strict=True,
            result='')),
        ('5_5_x_x', dict(
            desired=5, min_size=5, max_size=None, strict=True,
            result='')),
        ('20_x_x_x', dict(
            desired=20, min_size=None, max_size=None, strict=True,
            result='')),
        ('30_x_30_x', dict(
            desired=30, min_size=None, max_size=30, strict=True,
            result='')),
        ('30_x_-1_x', dict(
            desired=30, min_size=None, max_size=-1, strict=True,
            result='')),
        ('40_30_-1_x', dict(
            desired=40, min_size=30, max_size=-1, strict=True,
            result='')),
        ('x_x_-1_x', dict(
            desired=None, min_size=None, max_size=-1, strict=True,
            result='')),
    ]

    def test_check_size_params(self):
        cluster = mock.Mock()
        cluster.min_size = 10
        cluster.max_size = 20
        cluster.desired_capacity = 15

        actual = su.check_size_params(cluster, self.desired, self.min_size,
                                      self.max_size, self.strict)
        self.assertEqual(self.result, actual)
