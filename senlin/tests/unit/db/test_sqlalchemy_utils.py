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
from oslo_utils import timeutils

from senlin.db.sqlalchemy import utils
from senlin.tests.unit.common import base


class ExactFilterTest(base.SenlinTestCase):

    def setUp(self):
        super(ExactFilterTest, self).setUp()
        self.query = mock.Mock()
        self.model = mock.Mock()

    def test_returns_same_query_for_empty_filters(self):
        filters = {}
        utils.exact_filter(self.query, self.model, filters)
        self.assertEqual(0, self.query.call_count)

    def test_add_exact_match_clause_for_single_values(self):
        filters = {'cat': 'foo'}
        utils.exact_filter(self.query, self.model, filters)

        self.query.filter_by.assert_called_once_with(cat='foo')

    def test_adds_an_in_clause_for_multiple_values(self):
        self.model.cat.in_.return_value = 'fake in clause'
        filters = {'cat': ['foo', 'quux']}
        utils.exact_filter(self.query, self.model, filters)

        self.query.filter.assert_called_once_with('fake in clause')
        self.model.cat.in_.assert_called_once_with(['foo', 'quux'])


class SortParamTest(base.SenlinTestCase):

    def test_value_none(self):
        keys, dirs = utils.get_sort_params(None)
        self.assertEqual(['id'], keys)
        self.assertEqual(['asc'], dirs)

    def test_value_none_with_default_key(self):
        keys, dirs = utils.get_sort_params(None, 'foo')
        self.assertEqual(2, len(keys))
        self.assertEqual(2, len(dirs))
        self.assertEqual(['foo', 'id'], keys)
        self.assertEqual(['asc-nullsfirst', 'asc'], dirs)

    def test_value_single(self):
        keys, dirs = utils.get_sort_params('foo')
        self.assertEqual(2, len(keys))
        self.assertEqual(2, len(dirs))
        self.assertEqual(['foo', 'id'], keys)
        self.assertEqual(['asc-nullsfirst', 'asc'], dirs)

    def test_value_multiple(self):
        keys, dirs = utils.get_sort_params('foo,bar,zoo')
        self.assertEqual(4, len(keys))
        self.assertEqual(4, len(dirs))
        self.assertEqual(['foo', 'bar', 'zoo', 'id'], keys)
        self.assertEqual(['asc-nullsfirst', 'asc-nullsfirst', 'asc-nullsfirst',
                          'asc'], dirs)

    def test_value_multiple_with_dirs(self):
        keys, dirs = utils.get_sort_params('foo:asc,bar,zoo:desc')
        self.assertEqual(4, len(keys))
        self.assertEqual(4, len(dirs))
        self.assertEqual(['foo', 'bar', 'zoo', 'id'], keys)
        self.assertEqual(['asc-nullsfirst', 'asc-nullsfirst',
                          'desc-nullslast', 'asc'], dirs)

    def test_value_multiple_with_dirs_and_default_key(self):
        keys, dirs = utils.get_sort_params('foo:asc,bar,zoo:desc', 'notused')
        self.assertEqual(4, len(keys))
        self.assertEqual(4, len(dirs))
        self.assertEqual(['foo', 'bar', 'zoo', 'id'], keys)
        self.assertEqual(['asc-nullsfirst', 'asc-nullsfirst',
                          'desc-nullslast', 'asc'], dirs)

    def test_value_multiple_including_id(self):
        keys, dirs = utils.get_sort_params('foo,bar,id')
        self.assertEqual(3, len(keys))
        self.assertEqual(3, len(dirs))
        self.assertEqual(['foo', 'bar', 'id'], keys)
        self.assertEqual(['asc-nullsfirst', 'asc-nullsfirst',
                          'asc-nullsfirst'], dirs)


class ServiceAliveTest(base.SenlinTestCase):

    def test_alive(self):
        cfg.CONF.set_override('periodic_interval', 100)
        service = mock.Mock(updated_at=timeutils.utcnow())

        res = utils.is_service_dead(service)

        self.assertFalse(res)

    def test_dead(self):
        cfg.CONF.set_override('periodic_interval', 0)
        service = mock.Mock(updated_at=timeutils.utcnow())

        res = utils.is_service_dead(service)

        self.assertTrue(res)
