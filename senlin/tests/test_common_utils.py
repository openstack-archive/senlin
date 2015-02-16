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

import requests
from requests import exceptions
import six
import uuid

from oslo_config import cfg

from senlin.common import exception
from senlin.common import utils
from senlin.tests.common import base


class ShortIdTest(base.SenlinTestCase):

    def test_byte_string_8(self):
        self.assertEqual('\xab', utils._to_byte_string(0xab, 8))
        self.assertEqual('\x05', utils._to_byte_string(0x05, 8))

    def test_byte_string_16(self):
        self.assertEqual('\xab\xcd', utils._to_byte_string(0xabcd, 16))
        self.assertEqual('\x0a\xbc', utils._to_byte_string(0xabc, 16))

    def test_byte_string_12(self):
        self.assertEqual('\xab\xc0', utils._to_byte_string(0xabc, 12))
        self.assertEqual('\x0a\xb0', utils._to_byte_string(0x0ab, 12))

    def test_byte_string_60(self):
        val = 0x111111111111111
        byte_string = utils._to_byte_string(val, 60)
        self.assertEqual('\x11\x11\x11\x11\x11\x11\x11\x10', byte_string)

    def test_get_id_string(self):
        id = utils.get_id('11111111-1111-4111-bfff-ffffffffffff')
        self.assertEqual('ceirceirceir', id)

    def test_get_id_uuid_1(self):
        source = uuid.UUID('11111111-1111-4111-bfff-ffffffffffff')
        self.assertEqual(0x111111111111111, source.time)
        self.assertEqual('ceirceirceir', utils.get_id(source))

    def test_get_id_uuid_f(self):
        source = uuid.UUID('ffffffff-ffff-4fff-8000-000000000000')
        self.assertEqual('777777777777', utils.get_id(source))

    def test_get_id_uuid_0(self):
        source = uuid.UUID('00000000-0000-4000-bfff-ffffffffffff')
        self.assertEqual('aaaaaaaaaaaa', utils.get_id(source))

    def test_get_id_uuid_endianness(self):
        source = uuid.UUID('ffffffff-00ff-4000-aaaa-aaaaaaaaaaaa')
        self.assertEqual('aaaa77777777', utils.get_id(source))

    def test_get_id_uuid1(self):
        source = uuid.uuid1()
        self.assertRaises(ValueError, utils.get_id, source)

    def test_generate_ids(self):
        allowed_chars = 'abcdefghijklmnopqrstuvwxyz234567'
        ids = [utils.generate_id() for i in range(25)]

        for id in ids:
            self.assertEqual(12, len(id))
            self.assertFalse(id.translate(None, allowed_chars))
            self.assertEqual(1, ids.count(id))


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

        self.patchobject(requests, 'get', side_effect=exceptions.HTTPError())
        self.assertRaises(utils.URLFetchError, utils.url_fetch, url)

    def test_non_exist_url(self):
        url = 'http://non-exist.com/somedata'

        self.patchobject(requests, 'get', side_effect=exceptions.Timeout())
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
