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

from oslo_log import log as logging
import requests
import six

from oslo_config import cfg

from senlin.common import exception
from senlin.common import utils
from senlin.tests.unit.common import base


class TestParameterParsing(base.SenlinTestCase):
    def test_parse_bool(self):
        name = 'param'
        for value in ('True', 'true', 'TRUE', True):
            self.assertTrue(utils.parse_bool_param(name, value))
        for value in ('False', 'false', 'FALSE', False):
            self.assertFalse(utils.parse_bool_param(name, value))
        for value in ('foo', 't', 'f', 'yes', 'no', 'y', 'n', '1', '0', None):
            self.assertRaises(exception.InvalidParameter,
                              utils.parse_bool_param, name, value)

    def test_parse_int(self):
        name = 'param'
        cases = {0: 0, 2: 2, '0': 0, '2': 2}
        for value, expected in cases.items():
            actual = utils.parse_int_param(name, value)
            self.assertEqual(expected, actual)

        # A None should be returned directly
        actual = utils.parse_int_param(name, None)
        self.assertIsNone(actual)

        for value in (2, '2'):
            self.assertTrue(utils.parse_int_param(name, value,
                                                  allow_zero=False))
        for value in (0, '0'):
            self.assertRaises(exception.InvalidParameter,
                              utils.parse_int_param, name, value,
                              allow_zero=False)
        for value in (-1, '-2'):
            self.assertTrue(utils.parse_int_param(name, value,
                                                  allow_negative=True))
        for value in (-1, '-2'):
            self.assertRaises(exception.InvalidParameter,
                              utils.parse_int_param, name, value)

        for value in (1, 6):
            self.assertRaises(exception.InvalidParameter,
                              utils.parse_int_param, name, value,
                              lower_limit=2, upper_limit=5)

    def test_validate_sort_param(self):
        whitelist = ['foo', 'bar', 'zoo']
        # None case
        actual = utils.validate_sort_param(None, whitelist)
        self.assertIsNone(actual)

        # single good key
        actual = utils.validate_sort_param('foo', whitelist)
        self.assertIsNone(actual)

        # multiple keys
        actual = utils.validate_sort_param('foo,bar', whitelist)
        self.assertIsNone(actual)

        # with dirs
        value = 'foo:asc,bar,zoo:desc'
        actual = utils.validate_sort_param(value, whitelist)
        self.assertIsNone(actual)

    def test_validate_sort_param_key_missing(self):
        whitelist = ['foo', 'bar', 'zoo']
        ex = self.assertRaises(exception.InvalidParameter,
                               utils.validate_sort_param,
                               ':asc', whitelist)
        self.assertEqual("Invalid value '' specified for 'sort key'",
                         six.text_type(ex))

    def test_validate_sort_param_invalid_key(self):
        whitelist = ['foo', 'bar', 'zoo']
        ex = self.assertRaises(exception.InvalidParameter,
                               utils.validate_sort_param,
                               'cool', whitelist)
        self.assertEqual("Invalid value 'cool' specified for 'sort key'",
                         six.text_type(ex))

    def test_validate_sort_param_invalid_dir(self):
        whitelist = ['foo', 'bar', 'zoo']
        ex = self.assertRaises(exception.InvalidParameter,
                               utils.validate_sort_param,
                               'bar:inc', whitelist)
        self.assertEqual("Invalid value 'inc' specified for 'sort dir'",
                         six.text_type(ex))


class Response(object):
    def __init__(self, buf=''):
        self.buf = buf

    def iter_content(self, chunk_size=1):
        while self.buf:
            yield self.buf[:chunk_size]
            self.buf = self.buf[chunk_size:]

    def raise_for_status(self):
        pass


class UrlFetchTest(base.SenlinTestCase):
    def setUp(self):
        super(UrlFetchTest, self).setUp()

    def test_file_scheme_default_behaviour(self):
        self.assertRaises(utils.URLFetchError,
                          utils.url_fetch, 'file:///etc/profile')

    def test_file_scheme_supported(self):
        data = '{ "foo": "bar" }'
        url = 'file:///etc/profile'

        self.patchobject(six.moves.urllib.request, 'urlopen',
                         return_value=six.moves.cStringIO(data))
        actual = utils.url_fetch(url, allowed_schemes=['file'])
        self.assertEqual(data, actual)

    def test_file_scheme_failure(self):
        url = 'file:///etc/profile'
        self.patchobject(six.moves.urllib.request, 'urlopen',
                         side_effect=six.moves.urllib.error.URLError('oops'))

        self.assertRaises(utils.URLFetchError,
                          utils.url_fetch, url, allowed_schemes=['file'])

    def test_http_scheme(self):
        url = 'http://example.com/somedata'
        data = '{ "foo": "bar" }'
        response = Response(data)
        self.patchobject(requests, 'get', return_value=response)
        self.assertEqual(data, utils.url_fetch(url))

    def test_https_scheme(self):
        url = 'https://example.com/somedata'
        data = '{ "foo": "bar" }'
        self.patchobject(requests, 'get', return_value=Response(data))
        self.assertEqual(data, utils.url_fetch(url))

    def test_http_error(self):
        url = 'http://example.com/somedata'

        self.patchobject(requests, 'get',
                         side_effect=requests.exceptions.HTTPError())
        self.assertRaises(utils.URLFetchError, utils.url_fetch, url)

    def test_non_exist_url(self):
        url = 'http://non-exist.com/somedata'

        self.patchobject(requests, 'get',
                         side_effect=requests.exceptions.Timeout())
        self.assertRaises(utils.URLFetchError, utils.url_fetch, url)

    def test_garbage(self):
        self.assertRaises(utils.URLFetchError, utils.url_fetch, 'wibble')

    def test_max_fetch_size_okay(self):
        url = 'http://example.com/somedata'
        data = '{ "foo": "bar" }'
        cfg.CONF.set_override('max_response_size', 500, enforce_type=True)
        self.patchobject(requests, 'get', return_value=Response(data))
        utils.url_fetch(url)

    def test_max_fetch_size_error(self):
        url = 'http://example.com/somedata'
        data = '{ "foo": "bar" }'
        cfg.CONF.set_override('max_response_size', 5, enforce_type=True)
        self.patchobject(requests, 'get', return_value=Response(data))
        exception = self.assertRaises(utils.URLFetchError,
                                      utils.url_fetch, url)
        self.assertIn("Data exceeds", six.text_type(exception))


class TestRandomName(base.SenlinTestCase):

    def test_default(self):
        result = utils.random_name()
        self.assertIsNotNone(result)
        self.assertEqual(8, len(result))

        result1 = utils.random_name()
        self.assertIsNotNone(result1)
        self.assertEqual(8, len(result1))

        self.assertNotEqual(result, result1)

    def test_with_length(self):
        result = utils.random_name(12)
        self.assertIsNotNone(result)
        self.assertEqual(12, len(result))

        result1 = utils.random_name(12)
        self.assertIsNotNone(result1)
        self.assertEqual(12, len(result1))

        self.assertNotEqual(result, result1)

    def test_with_bad_length(self):
        result = utils.random_name(0)
        self.assertEqual('', result)

        result = utils.random_name(-9)
        self.assertEqual('', result)


class TestParseLevelValues(base.SenlinTestCase):

    def test_none(self):
        res = utils.parse_level_values(None)
        self.assertIsNone(res)

    def test_empty_list(self):
        res = utils.parse_level_values([])
        self.assertIsNone(res)

    def test_single_value(self):
        res = utils.parse_level_values('ERROR')
        self.assertEqual([logging.ERROR], res)

    def test_multi_values(self):
        res = utils.parse_level_values(['WARNING', 'ERROR'])
        self.assertEqual([logging.WARNING, logging.ERROR], res)

    def test_with_invalid_values(self):
        res = utils.parse_level_values(['warn', 'ERROR'])
        self.assertEqual([logging.ERROR], res)

    def test_with_integers(self):
        res = utils.parse_level_values(40)
        self.assertEqual([40], res)

    def test_with_only_invalid_values(self):
        res = utils.parse_level_values(['warn'])
        self.assertIsNone(res)


class TestGetPathParser(base.SenlinTestCase):

    def test_normal(self):
        res = utils.get_path_parser('foo.bar')
        self.assertIsNotNone(res)

    def test_bad_path(self):
        err = self.assertRaises(exception.BadRequest,
                                utils.get_path_parser,
                                '^foo.bar')
        self.assertEqual("The request is malformed: Invalid attribute path - "
                         "Unexpected character: ^",
                         six.text_type(err))
