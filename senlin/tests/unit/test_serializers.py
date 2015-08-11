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

import webob

from oslo_utils import encodeutils
from oslo_utils import timeutils as tu

from senlin.common import serializers
from senlin.tests.unit.common import base


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
        content_types = filter(lambda h: h[0] == 'Content-Type',
                               response.headerlist)
        # NOTE: filter returns a iterator in python 3.
        types = [t for t in content_types]
        self.assertEqual(1, len(types))
        self.assertEqual('application/json', response.content_type)
        self.assertEqual('{"key": "value"}',
                         encodeutils.safe_decode(response.body))
