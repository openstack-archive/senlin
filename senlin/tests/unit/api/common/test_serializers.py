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

from oslo_config import cfg
from oslo_serialization import jsonutils
from oslo_utils import encodeutils
from oslo_utils import timeutils as tu
import six
import webob

from senlin.api.common import serializers
from senlin.api.common import wsgi
from senlin.common import exception
from senlin.tests.unit.common import base


class JSONRequestDeserializerTest(base.SenlinTestCase):

    def test_has_body_no_content_length(self):
        request = wsgi.Request.blank('/')
        request.method = 'POST'
        request.body = encodeutils.safe_encode('asdf')
        request.headers.pop('Content-Length')
        request.headers['Content-Type'] = 'application/json'
        obj = serializers.JSONRequestDeserializer()
        self.assertFalse(obj.has_body(request))

    def test_has_body_zero_content_length(self):
        request = wsgi.Request.blank('/')
        request.method = 'POST'
        request.body = encodeutils.safe_encode('asdf')
        request.headers['Content-Length'] = 0
        request.headers['Content-Type'] = 'application/json'
        obj = serializers.JSONRequestDeserializer()
        self.assertFalse(obj.has_body(request))

    def test_has_body_has_content_length_no_content_type(self):
        request = wsgi.Request.blank('/')
        request.method = 'POST'
        request.body = encodeutils.safe_encode('{"key": "value"}')
        self.assertIn('Content-Length', request.headers)
        obj = serializers.JSONRequestDeserializer()
        self.assertTrue(obj.has_body(request))

    def test_has_body_has_content_length_plain_content_type(self):
        request = wsgi.Request.blank('/')
        request.method = 'POST'
        request.body = encodeutils.safe_encode('{"key": "value"}')
        self.assertIn('Content-Length', request.headers)
        request.headers['Content-Type'] = 'text/plain'
        obj = serializers.JSONRequestDeserializer()
        self.assertTrue(obj.has_body(request))

    def test_has_body_has_content_type_malformed(self):
        request = wsgi.Request.blank('/')
        request.method = 'POST'
        request.body = encodeutils.safe_encode('asdf')
        self.assertIn('Content-Length', request.headers)
        request.headers['Content-Type'] = 'application/json'
        obj = serializers.JSONRequestDeserializer()
        self.assertFalse(obj.has_body(request))

    def test_has_body_has_content_type(self):
        request = wsgi.Request.blank('/')
        request.method = 'POST'
        request.body = encodeutils.safe_encode('{"key": "value"}')
        self.assertIn('Content-Length', request.headers)
        request.headers['Content-Type'] = 'application/json'
        obj = serializers.JSONRequestDeserializer()
        self.assertTrue(obj.has_body(request))

    def test_has_body_has_wrong_content_type(self):
        request = wsgi.Request.blank('/')
        request.method = 'POST'
        request.body = encodeutils.safe_encode('{"key": "value"}')
        self.assertIn('Content-Length', request.headers)
        request.headers['Content-Type'] = 'application/xml'
        obj = serializers.JSONRequestDeserializer()
        self.assertFalse(obj.has_body(request))

    def test_has_body_has_aws_content_type_only(self):
        request = wsgi.Request.blank('/?ContentType=JSON')
        request.method = 'GET'
        request.body = encodeutils.safe_encode('{"key": "value"}')
        self.assertIn('Content-Length', request.headers)
        obj = serializers.JSONRequestDeserializer()
        self.assertTrue(obj.has_body(request))

    def test_has_body_content_type_with_get(self):
        request = wsgi.Request.blank('/')
        request.method = 'GET'
        request.body = encodeutils.safe_encode('{"key": "value"}')
        self.assertIn('Content-Length', request.headers)
        obj = serializers.JSONRequestDeserializer()
        self.assertTrue(obj.has_body(request))

    def test_no_body_no_content_length(self):
        request = wsgi.Request.blank('/')
        obj = serializers.JSONRequestDeserializer()
        self.assertFalse(obj.has_body(request))

    def test_from_json(self):
        fixture = '{"key": "value"}'
        expected = {"key": "value"}
        actual = serializers.JSONRequestDeserializer().from_json(fixture)
        self.assertEqual(expected, actual)

    def test_from_json_malformed(self):
        fixture = 'kjasdklfjsklajf'
        self.assertRaises(webob.exc.HTTPBadRequest,
                          serializers.JSONRequestDeserializer().from_json,
                          fixture)

    def test_default_no_body(self):
        request = wsgi.Request.blank('/')
        actual = serializers.JSONRequestDeserializer().default(request)
        expected = {}
        self.assertEqual(expected, actual)

    def test_default_with_body(self):
        request = wsgi.Request.blank('/')
        request.method = 'POST'
        request.body = encodeutils.safe_encode('{"key": "value"}')
        actual = serializers.JSONRequestDeserializer().default(request)
        expected = {"body": {"key": "value"}}
        self.assertEqual(expected, actual)

    def test_default_with_get_with_body(self):
        request = wsgi.Request.blank('/')
        request.method = 'GET'
        request.body = encodeutils.safe_encode('{"key": "value"}')
        actual = serializers.JSONRequestDeserializer().default(request)
        expected = {"body": {"key": "value"}}
        self.assertEqual(expected, actual)

    def test_default_with_get_with_body_with_aws(self):
        request = wsgi.Request.blank('/?ContentType=JSON')
        request.method = 'GET'
        request.body = encodeutils.safe_encode('{"key": "value"}')
        actual = serializers.JSONRequestDeserializer().default(request)
        expected = {"body": {"key": "value"}}
        self.assertEqual(expected, actual)

    def test_from_json_exceeds_max_json_mb(self):
        cfg.CONF.set_override('max_json_body_size', 10, group='senlin_api')
        body = jsonutils.dumps(['a'] * cfg.CONF.senlin_api.max_json_body_size)
        self.assertGreater(len(body), cfg.CONF.senlin_api.max_json_body_size)
        obj = serializers.JSONRequestDeserializer()
        error = self.assertRaises(exception.RequestLimitExceeded,
                                  obj.from_json,
                                  body)
        msg = ('Request limit exceeded: JSON body size '
               '(%s bytes) exceeds maximum allowed size (%s bytes).'
               ) % (len(body), cfg.CONF.senlin_api.max_json_body_size)
        self.assertEqual(msg, six.text_type(error))


class JSONResponseSerializerTest(base.SenlinTestCase):

    def test_to_json(self):
        fixture = {"key": "value"}
        expected = '{"key": "value"}'
        actual = serializers.JSONResponseSerializer().to_json(fixture)
        self.assertEqual(expected, actual)

    def test_to_json_with_date_format_value(self):
        test_date = tu.parse_strtime("0001-03-08T02:00:00",
                                     '%Y-%m-%dT%H:%M:%S')
        fixture = {"date": test_date}
        expected = '{"date": "0001-03-08T02:00:00"}'
        actual = serializers.JSONResponseSerializer().to_json(fixture)
        self.assertEqual(expected, actual)

    def test_to_json_with_more_deep_format(self):
        val = complex(1, 2)
        fixture = {"is_public": True, "v": val}
        expected = '{"is_public": true, "v": "(1+2j)"}'
        actual = serializers.JSONResponseSerializer().to_json(fixture)
        self.assertEqual(expected, actual)

    def test_default(self):
        fixture = {"key": "value"}
        response = webob.Response()
        serializers.JSONResponseSerializer().default(response, fixture)
        self.assertEqual(200, response.status_int)
        content_types = [h for h in response.headerlist
                         if h[0] == 'Content-Type']
        # NOTE: filter returns a iterator in python 3.
        types = [t for t in content_types]
        self.assertEqual(1, len(types))
        self.assertEqual('application/json', response.content_type)
        self.assertEqual('{"key": "value"}',
                         encodeutils.safe_decode(response.body))
