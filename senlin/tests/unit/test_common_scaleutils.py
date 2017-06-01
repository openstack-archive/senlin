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

from oslo_config import cfg

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
                self.assertEqual(current + number, res)

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

    def test_parse_resize_params_deletion(self):
        action = mock.Mock()
        cluster = mock.Mock()
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

        result, reason = su.parse_resize_params(action, cluster, 6)

        self.assertEqual('OK', result)
        self.assertEqual('', reason)
        self.assertEqual({'deletion': {'count': 2}}, action.data)

    def test_parse_resize_params_creation(self):
        action = mock.Mock(RES_OK='OK')
        cluster = mock.Mock()
        action.inputs = {
            consts.ADJUSTMENT_TYPE: consts.EXACT_CAPACITY,
            consts.ADJUSTMENT_NUMBER: 9,
            consts.ADJUSTMENT_MIN_SIZE: 3,
            consts.ADJUSTMENT_MAX_SIZE: 10,
            consts.ADJUSTMENT_MIN_STEP: None,
            consts.ADJUSTMENT_STRICT: True,
        }
        action.data = {}

        result, reason = su.parse_resize_params(action, cluster, 6)

        self.assertEqual('OK', result)
        self.assertEqual('', reason)
        self.assertEqual({'creation': {'count': 3}}, action.data)

    def test_parse_resize_params_invalid(self):
        action = mock.Mock()
        cluster = mock.Mock()
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

        result, reason = su.parse_resize_params(action, cluster, 6)

        self.assertEqual('ERROR', result)
        msg = _('The target capacity (11) is greater than '
                'the specified max_size (10).')
        self.assertEqual(msg, reason)

    def test_filter_error_nodes(self):
        nodes = [
            mock.Mock(id='N1', status='ACTIVE'),
            mock.Mock(id='N2', status='ACTIVE'),
            mock.Mock(id='N3', status='ERROR'),
            mock.Mock(id='N4', status='ACTIVE'),
            mock.Mock(id='N5', status='WARNING'),
            mock.Mock(id='N6', status='ERROR'),
            mock.Mock(id='N7', created_at=None)
        ]
        res = su.filter_error_nodes(nodes)
        self.assertIn('N3', res[0])
        self.assertIn('N5', res[0])
        self.assertIn('N6', res[0])
        self.assertIn('N7', res[0])
        self.assertEqual(3, len(res[1]))

    @mock.patch.object(su, 'filter_error_nodes')
    def test_nodes_by_random(self, mock_filter):
        good_nodes = [
            mock.Mock(id='N11', created_at=110),
            mock.Mock(id='N15', created_at=150),
            mock.Mock(id='N12', created_at=120),
            mock.Mock(id='N13', created_at=130),
            mock.Mock(id='N14', created_at=None),
        ]
        mock_filter.return_value = (['N1', 'N2'], good_nodes)

        nodes = mock.Mock()

        res = su.nodes_by_random(nodes, 1)
        self.assertEqual(['N1'], res)

        res = su.nodes_by_random(nodes, 2)
        self.assertEqual(['N1', 'N2'], res)

        res = su.nodes_by_random(nodes, 5)
        self.assertIn('N1', res)
        self.assertIn('N2', res)
        self.assertEqual(5, len(res))

    @mock.patch.object(su, 'filter_error_nodes')
    def test_nodes_by_age_oldest(self, mock_filter):
        good_nodes = [
            mock.Mock(id='N11', created_at=110),
            mock.Mock(id='N15', created_at=150),
            mock.Mock(id='N12', created_at=120),
            mock.Mock(id='N13', created_at=130),
            mock.Mock(id='N14', created_at=100),
        ]
        mock_filter.return_value = (['N1', 'N2'], good_nodes)

        nodes = mock.Mock()

        res = su.nodes_by_age(nodes, 1, True)
        self.assertEqual(['N1'], res)

        res = su.nodes_by_age(nodes, 2, True)
        self.assertEqual(['N1', 'N2'], res)

        res = su.nodes_by_age(nodes, 5, True)
        self.assertEqual(['N1', 'N2', 'N14', 'N11', 'N12'], res)

    @mock.patch.object(su, 'filter_error_nodes')
    def test_nodes_by_age_youngest(self, mock_filter):
        good_nodes = [
            mock.Mock(id='N11', created_at=110),
            mock.Mock(id='N15', created_at=150),
            mock.Mock(id='N12', created_at=120),
            mock.Mock(id='N13', created_at=130),
            mock.Mock(id='N14', created_at=100),
        ]
        mock_filter.return_value = (['N1', 'N2'], good_nodes)

        nodes = mock.Mock()

        res = su.nodes_by_age(nodes, 1, False)
        self.assertEqual(['N1'], res)

        res = su.nodes_by_age(nodes, 2, False)
        self.assertEqual(['N1', 'N2'], res)

        res = su.nodes_by_age(nodes, 5, False)
        self.assertEqual(['N1', 'N2', 'N15', 'N13', 'N12'], res)

    @mock.patch.object(su, 'filter_error_nodes')
    def test__victims_by_profile_age_oldest(self, mock_filter):
        good_nodes = [
            mock.Mock(id='N11', profile_created_at=110),
            mock.Mock(id='N15', profile_created_at=150),
            mock.Mock(id='N12', profile_created_at=120),
            mock.Mock(id='N13', profile_created_at=130),
            mock.Mock(id='N14', profile_created_at=140),
        ]
        mock_filter.return_value = (['N1', 'N2'], good_nodes)

        nodes = mock.Mock()

        res = su.nodes_by_profile_age(nodes, 1)
        self.assertEqual(['N1'], res)

        res = su.nodes_by_profile_age(nodes, 2)
        self.assertEqual(['N1', 'N2'], res)

        res = su.nodes_by_profile_age(nodes, 5)
        self.assertEqual(['N1', 'N2', 'N11', 'N12', 'N13'], res)


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
            result='The specified min_size (25) is greater than the current '
                   'max_size (20) of the cluster.')),
        ('x_20_x_x', dict(
            desired=None, min_size=20, max_size=None, strict=True,
            result='The specified min_size (20) is greater than the current '
                   'desired_capacity (15) of the cluster.')),
        ('x_x_5_x', dict(
            desired=None, min_size=None, max_size=5, strict=True,
            result='The specified max_size (5) is less than the current '
                   'min_size (10) of the cluster.')),
        ('x_x_14_x', dict(
            desired=None, min_size=None, max_size=14, strict=True,
            result='The specified max_size (14) is less than the current '
                   'desired_capacity (15) of the cluster.')),
        ('101_x_x_x', dict(
            desired=101, min_size=None, max_size=None, strict=True,
            result='The target capacity (101) is greater than the '
                   'maximum number of nodes allowed per cluster (100).')),
        ('x_x_101_x', dict(
            desired=None, min_size=None, max_size=101, strict=True,
            result='The specified max_size (101) is greater than the '
                   'maximum number of nodes allowed per cluster (100).')),
        # The following are okay cases
        ('5_x10_x_x', dict(
            desired=5, min_size=None, max_size=None, strict=False,
            result=None)),
        ('30_x_x20_x', dict(
            desired=30, min_size=None, max_size=None, strict=False,
            result=None)),
        ('x_20_x_x', dict(
            desired=None, min_size=20, max_size=None, strict=False,
            result=None)),
        ('x_x_14_x', dict(
            desired=None, min_size=None, max_size=14, strict=False,
            result=None)),
        ('x_x_x_x', dict(
            desired=None, min_size=None, max_size=None, strict=True,
            result=None)),
        ('18_x_x_x', dict(
            desired=18, min_size=None, max_size=None, strict=True,
            result=None)),
        ('30_x_40_x', dict(
            desired=30, min_size=None, max_size=40, strict=True,
            result=None)),
        ('x_x_40_x', dict(
            desired=None, min_size=None, max_size=40, strict=True,
            result=None)),
        ('x_5_x_x', dict(
            desired=None, min_size=5, max_size=None, strict=True,
            result=None)),
        ('x_15_x_x', dict(
            desired=None, min_size=15, max_size=None, strict=True,
            result=None)),
        ('5_5_x_x', dict(
            desired=5, min_size=5, max_size=None, strict=True,
            result=None)),
        ('20_x_x_x', dict(
            desired=20, min_size=None, max_size=None, strict=True,
            result=None)),
        ('30_x_30_x', dict(
            desired=30, min_size=None, max_size=30, strict=True,
            result=None)),
        ('30_x_-1_x', dict(
            desired=30, min_size=None, max_size=-1, strict=True,
            result=None)),
        ('40_30_-1_x', dict(
            desired=40, min_size=30, max_size=-1, strict=True,
            result=None)),
        ('x_x_-1_x', dict(
            desired=None, min_size=None, max_size=-1, strict=True,
            result=None)),
    ]

    def setUp(self):
        super(CheckSizeParamsTest, self).setUp()
        cfg.CONF.set_override('max_nodes_per_cluster', 100)

    def test_check_size_params(self):
        cluster = mock.Mock()
        cluster.min_size = 10
        cluster.max_size = 20
        cluster.desired_capacity = 15

        actual = su.check_size_params(cluster, self.desired, self.min_size,
                                      self.max_size, self.strict)
        self.assertEqual(self.result, actual)

    def test_check_size_params_default_strict(self):
        cluster = mock.Mock()
        cluster.min_size = 10
        cluster.max_size = 20
        cluster.desired_capacity = 15
        desired = 5
        min_size = None
        max_size = None

        actual = su.check_size_params(cluster, desired, min_size, max_size)
        self.assertIsNone(actual)
