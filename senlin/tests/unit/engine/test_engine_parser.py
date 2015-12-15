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
import os
import six

from senlin.engine import parser
from senlin.tests.unit.common import base


class ParserTest(base.SenlinTestCase):

    json_template = """
    {
      "type": "os.heat.stack",
      "version": 1.0,
      "properties": {
        "name": "random_string_stack",
        "template": "random_string_stack.yaml"
      }
    }
    """

    yaml_template = """
    type: os.heat.stack
    version: 1.0
    properties:
      name: random_string_stack
      template: random_string_stack.yaml
    """

    expect_result = {
        "type": "os.heat.stack",
        "version": 1,
        "properties": {
            "name": "random_string_stack",
            "template": "random_string_stack.yaml"
        }
    }

    def test_parse_json_success(self):
        result = parser.simple_parse(self.json_template)
        self.assertEqual(self.expect_result, result)

    def test_parse_yaml_success(self):
        result = parser.simple_parse(self.yaml_template)
        self.assertEqual(self.expect_result, result)

    def test_parse_string(self):
        tmpl_str = 'json string'
        ex = self.assertRaises(ValueError,
                               parser.simple_parse,
                               tmpl_str)
        self.assertEqual('The input is not a JSON object or YAML mapping.',
                         six.text_type(ex))

    def test_parse_list(self):
        tmpl_str = '["foo" , "bar"]'
        ex = self.assertRaises(ValueError,
                               parser.simple_parse,
                               tmpl_str)
        self.assertEqual('The input is not a JSON object or YAML mapping.',
                         six.text_type(ex))

    def test_parse_invalid_yaml_and_json_template(self):
        tmpl_str = '{test'
        ex = self.assertRaises(ValueError,
                               parser.simple_parse,
                               tmpl_str)
        self.assertIn('Error parsing input:',
                      six.text_type(ex))


class ParseTemplateIncludeFiles(base.SenlinTestCase):
    scenarios = [
        ('include_from_file_without_path', dict(
            tmpl_str='foo: !include a.file',
            url_path='file:///tmp/a.file',
        )),
        ('include_from_file_with_path', dict(
            tmpl_str='foo: !include file:///tmp/a.file',
            url_path='file:///tmp/a.file',
        )),
        ('include_from_http', dict(
            tmpl_str='foo: !include http://tmp/a.file',
            url_path='http://tmp/a.file',
        )),
        ('include_from_https', dict(
            tmpl_str='foo: !include https://tmp/a.file',
            url_path='https://tmp/a.file',
        ))

    ]

    @mock.patch.object(six.moves.urllib.request, 'urlopen')
    @mock.patch.object(os.path, 'abspath')
    def test_parse_template(self, mock_abspath, mock_urlopen):
        fetch_data = 'bar'
        expect_result = {
            'foo': 'bar'
        }

        mock_abspath.return_value = '/tmp/a.file'
        mock_urlopen.side_effect = [
            six.moves.urllib.error.URLError('oops'),
            six.moves.cStringIO(fetch_data)
        ]

        ex = self.assertRaises(IOError,
                               parser.simple_parse,
                               self.tmpl_str)
        self.assertIn('Failed retrieving file %s:' % self.url_path,
                      six.text_type(ex))
        result = parser.simple_parse(self.tmpl_str)
        self.assertEqual(expect_result,
                         result)
        mock_urlopen.assert_has_calls([
            mock.call(self.url_path),
            mock.call(self.url_path)
        ])
