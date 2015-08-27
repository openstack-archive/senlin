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

from cryptography import fernet
import requests
from requests import exceptions
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


class TestEncrypt(base.SenlinTestCase):
    def test_encrypt(self):
        msg = 'test-string'
        msg_encrypted, key = utils.encrypt(msg)

        self.assertIsInstance(msg_encrypted, six.string_types)
        self.assertIsInstance(key, six.string_types)

    def test_decrypt(self):
        msg = 'test-string'
        msg_encrypted, key = utils.encrypt(msg)

        msg_decrypted = utils.decrypt(msg_encrypted, key)
        self.assertEqual(msg, msg_decrypted)

    def test_decrypt_invalid_key_msg(self):
        msg = 'test-string'
        msg_encrypted, key = utils.encrypt(msg)

        invalid_key = 'fake-key'
        self.assertRaises(fernet.InvalidToken, utils.decrypt,
                          msg_encrypted, invalid_key)

        invalid_msg = 'fake-msg'
        self.assertRaises(ValueError, utils.decrypt,
                          invalid_msg, key)

        invalid_msg = fernet.Fernet.generate_key()
        self.assertRaises(fernet.InvalidToken, utils.decrypt,
                          invalid_msg, key)


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
