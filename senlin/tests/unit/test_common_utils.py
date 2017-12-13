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

import datetime
import mock
from oslo_log import log as logging
from oslo_utils import timeutils
import requests
import six

from oslo_config import cfg

from senlin.common import exception
from senlin.common import utils
from senlin.objects import service as service_obj
from senlin.tests.unit.common import base


class TestGetPositiveInt(base.SenlinTestCase):

    def test_get_positive_int(self):
        cases = {1: 1, 2: 2, '1': 1, '2': 2}
        for value, expected in cases.items():
            res, actual = utils.get_positive_int(value)
            self.assertTrue(res)
            self.assertEqual(expected, actual)

        bad_values = ['foo', {}, [], -1, 1.5, 0.2, None]
        for value in bad_values:
            res, actual = utils.get_positive_int(value)
            self.assertFalse(res)
            self.assertEqual(0, actual)


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
        cfg.CONF.set_override('max_response_size', 500)
        self.patchobject(requests, 'get', return_value=Response(data))
        utils.url_fetch(url)

    def test_max_fetch_size_error(self):
        url = 'http://example.com/somedata'
        data = '{ "foo": "bar" }'
        cfg.CONF.set_override('max_response_size', 5)
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


class TestFormatNodeName(base.SenlinTestCase):

    def test_empty(self):
        res = utils.format_node_name(None, None, 0)
        self.assertIsNotNone(res)
        self.assertEqual(13, len(res))

        res = utils.format_node_name("", None, 0)
        self.assertIsNotNone(res)
        self.assertEqual(13, len(res))

    def test_has_random(self):
        res = utils.format_node_name("prefix-$R", None, 0)
        self.assertEqual(15, len(res))

        res = utils.format_node_name("prefix-$5R", None, 0)
        self.assertEqual(12, len(res))

    def test_has_index(self):
        res = utils.format_node_name("prefix-$I", None, 12)
        self.assertEqual(9, len(res))

        res = utils.format_node_name("prefix-$5I", None, 12)
        self.assertEqual(12, len(res))

    def test_has_both(self):
        res = utils.format_node_name("prefix-$3R-$I", None, 12)
        self.assertEqual(13, len(res))

        res = utils.format_node_name("$3R-prefix-$5I", None, 12)
        self.assertEqual(16, len(res))


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
        res = utils.parse_level_values(['WARN', 'ERROR'])
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
        self.assertEqual("Invalid attribute path - Unexpected "
                         "character: ^.", six.text_type(err))


class EngineDeathTest(base.SenlinTestCase):

    def setUp(self):
        super(EngineDeathTest, self).setUp()
        self.ctx = mock.Mock()

    @mock.patch.object(service_obj.Service, 'get')
    def test_engine_is_none(self, mock_service):
        mock_service.return_value = None
        self.assertTrue(utils.is_engine_dead(self.ctx, 'fake_engine_id'))
        mock_service.assert_called_once_with(self.ctx, 'fake_engine_id')

    @mock.patch.object(service_obj.Service, 'get')
    def test_engine_is_dead(self, mock_service):
        delta = datetime.timedelta(seconds=3 * cfg.CONF.periodic_interval)
        update_time = timeutils.utcnow(True) - delta
        mock_service.return_value = mock.Mock(updated_at=update_time)

        res = utils.is_engine_dead(self.ctx, 'fake_engine_id')

        self.assertTrue(res)
        mock_service.assert_called_once_with(self.ctx, 'fake_engine_id')

    @mock.patch.object(service_obj.Service, 'get')
    def test_engine_is_alive(self, mock_svc):
        mock_svc.return_value = mock.Mock(updated_at=timeutils.utcnow(True))

        res = utils.is_engine_dead(self.ctx, 'fake_engine_id')

        self.assertFalse(res)
        mock_svc.assert_called_once_with(self.ctx, 'fake_engine_id')

    @mock.patch.object(service_obj.Service, 'get')
    def test_use_specified_duration(self, mock_svc):
        mock_svc.return_value = mock.Mock(updated_at=timeutils.utcnow(True))

        res = utils.is_engine_dead(self.ctx, 'fake_engine_id', 10000)

        self.assertFalse(res)
        mock_svc.assert_called_once_with(self.ctx, 'fake_engine_id')
