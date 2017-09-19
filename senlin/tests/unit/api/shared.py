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

from oslo_config import cfg
from oslo_messaging._drivers import common as rpc_common
from oslo_utils import encodeutils

from senlin.api.common import version_request as vr
from senlin.api.common import wsgi
from senlin.common import consts
from senlin.tests.unit.common import utils


def request_with_middleware(middleware, func, req, *args, **kwargs):

    @webob.dec.wsgify
    def _app(req):
        return func(req, *args, **kwargs)

    resp = middleware(_app).process_request(req)
    return resp


def to_remote_error(error):
    '''Prepend the given exception with the _Remote suffix.'''

    exc_info = (type(error), error, None)
    serialized = rpc_common.serialize_remote_exception(exc_info)
    remote_error = rpc_common.deserialize_remote_exception(
        serialized, ["senlin.common.exception"])
    return remote_error


class ControllerTest(object):
    '''Common utilities for testing API Controllers.'''

    def __init__(self, *args, **kwargs):
        super(ControllerTest, self).__init__(*args, **kwargs)

        cfg.CONF.set_default('host', 'server.test')
        self.topic = consts.ENGINE_TOPIC
        self.api_version = '1.0'
        self.project = 'PROJ'
        self.mock_enforce = None

    def _environ(self, path):
        return {
            'SERVER_NAME': 'server.test',
            'SERVER_PORT': 8004,
            'SCRIPT_NAME': '/v1',
            'PATH_INFO': '/%s' % self.project + path,
            'wsgi.url_scheme': 'http',
        }

    def _simple_request(self, path, params=None, method='GET', version=None):
        environ = self._environ(path)
        environ['REQUEST_METHOD'] = method

        if params:
            qs = "&".join(["=".join([k, str(params[k])]) for k in params])
            environ['QUERY_STRING'] = qs

        req = wsgi.Request(environ)
        req.context = utils.dummy_context('api_test_user', self.project)
        self.context = req.context
        ver = version if version else wsgi.DEFAULT_API_VERSION
        req.version_request = vr.APIVersionRequest(ver)
        return req

    def _get(self, path, params=None, version=None):
        return self._simple_request(path, params=params, version=version)

    def _delete(self, path, params=None, version=None):
        return self._simple_request(path, params=params, method='DELETE')

    def _data_request(self, path, data, content_type='application/json',
                      method='POST', version=None):
        environ = self._environ(path)
        environ['REQUEST_METHOD'] = method

        req = wsgi.Request(environ)
        req.context = utils.dummy_context('api_test_user', self.project)
        self.context = req.context
        ver = version if version else wsgi.DEFAULT_API_VERSION
        req.version_request = vr.APIVersionRequest(ver)
        req.body = encodeutils.safe_encode(data) if data else None
        return req

    def _post(self, path, data, content_type='application/json', version=None):
        return self._data_request(path, data, content_type, version=version)

    def _put(self, path, data, content_type='application/json', version=None):
        return self._data_request(path, data, content_type, method='PUT',
                                  version=version)

    def _patch(self, path, data, content_type='application/json',
               version=None):
        return self._data_request(path, data, content_type, method='PATCH',
                                  version=version)

    def tearDown(self):
        # Common tearDown to assert that policy enforcement happens for all
        # controller actions
        if self.mock_enforce:
            rule = "%s:%s" % (self.controller.REQUEST_SCOPE, self.action)
            self.mock_enforce.assert_called_with(
                context=self.context,
                target={}, rule=rule)
            self.assertEqual(self.expected_request_count,
                             len(self.mock_enforce.call_args_list))
        super(ControllerTest, self).tearDown()

    def _mock_enforce_setup(self, mocker, action, allowed=True,
                            expected_request_count=1):
        self.mock_enforce = mocker
        self.action = action
        self.mock_enforce.return_value = allowed
        self.expected_request_count = expected_request_count
