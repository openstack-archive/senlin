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

import jsonschema
import mock
import six
from webob import exc

from senlin.api.common import util
from senlin.api.common import wsgi
from senlin.common import context
from senlin.common import policy
from senlin.objects import base as obj_base
from senlin.tests.unit.common import base
from senlin.tests.unit.common import utils


class FakeRequest(obj_base.SenlinObject):

    VERSION = '2.0'
    VERSION_MAP = {
        '1.3': '2.0'
    }

    @classmethod
    def obj_from_primitive(cls, primitive):
        pass


class TestGetAllowedParams(base.SenlinTestCase):

    def setUp(self):
        super(TestGetAllowedParams, self).setUp()
        req = wsgi.Request({})
        self.params = req.params.copy()
        self.params.add('foo', 'foo value')
        self.whitelist = {'foo': 'single'}

    def test_returns_empty_dict(self):
        self.whitelist = {}

        result = util.get_allowed_params(self.params, self.whitelist)
        self.assertEqual({}, result)

    def test_only_adds_whitelisted_params_if_param_exists(self):
        self.whitelist = {'foo': 'single'}
        self.params.clear()

        result = util.get_allowed_params(self.params, self.whitelist)
        self.assertNotIn('foo', result)

    def test_returns_only_whitelisted_params(self):
        self.params.add('bar', 'bar value')

        result = util.get_allowed_params(self.params, self.whitelist)
        self.assertIn('foo', result)
        self.assertNotIn('bar', result)

    def test_handles_single_value_params(self):
        result = util.get_allowed_params(self.params, self.whitelist)
        self.assertEqual('foo value', result['foo'])

    def test_handles_multiple_value_params(self):
        self.whitelist = {'foo': 'multi'}
        self.params.add('foo', 'foo value 2')

        result = util.get_allowed_params(self.params, self.whitelist)
        self.assertEqual(2, len(result['foo']))
        self.assertIn('foo value', result['foo'])
        self.assertIn('foo value 2', result['foo'])

    def test_handles_mixed_value_param_with_multiple_entries(self):
        self.whitelist = {'foo': 'mixed'}
        self.params.add('foo', 'foo value 2')

        result = util.get_allowed_params(self.params, self.whitelist)
        self.assertEqual(2, len(result['foo']))
        self.assertIn('foo value', result['foo'])
        self.assertIn('foo value 2', result['foo'])

    def test_handles_mixed_value_param_with_single_entry(self):
        self.whitelist = {'foo': 'mixed'}

        result = util.get_allowed_params(self.params, self.whitelist)
        self.assertEqual(['foo value'], result['foo'])

    def test_ignores_bogus_whitelist_items(self):
        self.whitelist = {'foo': 'blah'}
        result = util.get_allowed_params(self.params, self.whitelist)
        self.assertNotIn('foo', result)


class TestPolicyEnforce(base.SenlinTestCase):

    def setUp(self):
        super(TestPolicyEnforce, self).setUp()
        self.req = wsgi.Request({})
        self.req.context = context.RequestContext(project='foo',
                                                  is_admin=False)

        class DummyController(object):
            REQUEST_SCOPE = 'test'

            @util.policy_enforce
            def an_action(self, req):
                return 'woot'

        self.controller = DummyController()

    @mock.patch.object(policy, 'enforce')
    def test_policy_enforce_policy_deny(self, mock_enforce):
        mock_enforce.return_value = False

        self.assertRaises(exc.HTTPForbidden,
                          self.controller.an_action,
                          self.req, tenant_id='foo')


class TestParseRequest(base.SenlinTestCase):

    def setUp(self):
        super(TestParseRequest, self).setUp()
        self.context = utils.dummy_context()

    def test_all_okay(self):
        name = 'ClusterListRequest'
        body = {'project_safe': True}
        req = mock.Mock(context=self.context)

        res = util.parse_request(name, req, body)

        self.assertIsNotNone(res)

    def test_bad_request_name(self):
        name = 'BadClusterListRequest'
        body = {'project_safe': True}
        req = mock.Mock(context=self.context)

        ex = self.assertRaises(exc.HTTPBadRequest,
                               util.parse_request,
                               name, req, body)

        self.assertEqual('Unsupported object type BadClusterListRequest',
                         six.text_type(ex))

    def test_bad_request_body(self):
        name = 'ClusterCreateRequest'
        body = {'bad_key': 'bad_value'}
        req = mock.Mock(context=self.context)

        ex = self.assertRaises(exc.HTTPBadRequest,
                               util.parse_request,
                               name, req, body, 'cluster')

        self.assertEqual("Request body missing 'cluster' key.",
                         six.text_type(ex))

    def test_bad_primitive(self):
        name = 'ClusterListRequest'
        body = {'limit': -1}
        req = mock.Mock(context=self.context)

        ex = self.assertRaises(exc.HTTPBadRequest,
                               util.parse_request,
                               name, req, body)

        self.assertEqual("Value must be >= 0 for field 'limit'.",
                         six.text_type(ex))

    def test_bad_schema(self):
        name = 'ClusterListRequest'
        body = {'bogus_key': 'bogus_value',
                'project_safe': True}
        req = mock.Mock(context=self.context)

        ex = self.assertRaises(exc.HTTPBadRequest,
                               util.parse_request,
                               name, req, body)

        self.assertEqual("Additional properties are not allowed ('bogus_key' "
                         "was unexpected)", six.text_type(ex))

    @mock.patch.object(jsonschema, 'validate')
    @mock.patch.object(FakeRequest, 'obj_from_primitive')
    @mock.patch.object(obj_base.SenlinObject, 'obj_class_from_name')
    def test_version_conversion(self, mock_cls, mock_construct, mock_validate):
        name = 'FakeReq'
        body = {}
        mock_cls.return_value = FakeRequest
        # The following context will force the request to be downgraded to
        # its base version (1.0)
        context = utils.dummy_context(api_version='1.2')
        req = mock.Mock(context=context)
        obj = mock.Mock()
        mock_construct.return_value = obj
        primitive = {
            'senlin_object.version': '2.0',
            'senlin_object.name': 'FakeReq',
            'senlin_object.data': {},
            'senlin_object.namespace': 'senlin'
        }

        res = util.parse_request(name, req, body)

        self.assertIsNotNone(res)
        mock_cls.assert_called_once_with('FakeReq')
        self.assertEqual(2, mock_construct.call_count)
        obj.obj_make_compatible.assert_called_once_with(primitive, '1.0')


class TestParseBool(base.SenlinTestCase):

    def test_parse_bool(self):
        name = 'param'
        for value in ('True', 'true', 'TRUE', True):
            self.assertTrue(util.parse_bool_param(name, value))
        for value in ('False', 'false', 'FALSE', False):
            self.assertFalse(util.parse_bool_param(name, value))
        for value in ('foo', 't', 'f', 'yes', 'no', 'y', 'n', '1', '0', None):
            self.assertRaises(exc.HTTPBadRequest,
                              util.parse_bool_param, name, value)
