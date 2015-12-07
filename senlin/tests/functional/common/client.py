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
from oslo_serialization import jsonutils
import requests

from senlin.common.i18n import _

LOG = logging.getLogger(__name__)


class APIResponse(object):
    content = ""
    body = {}
    headers = {}

    def __init__(self, response):
        super(APIResponse, self).__init__()
        self.status = response.status_code
        self.content = response.content
        if self.content:
            self.body = jsonutils.loads(self.content)
        self.headers = response.headers

    def __str__(self):
        return "<Response body:%r, status_code:%s>" % (self.body, self.status)


class SenlinApiException(Exception):
    def __init__(self, message=None, response=None):
        self.response = response
        if not message:
            message = 'Unspecified error'

        if response is not None:
            message = _('%(msg)s\nStatus Code: %(status)s\nBody: %(body)s'
                        ) % {'msg': message, 'status': response.status_code,
                             'body': response.content}

        super(SenlinApiException, self).__init__(message)


class TestSenlinAPIClient(object):
    """Simple Senlin API Client"""

    def __init__(self, auth_user, auth_key, auth_project, auth_user_domain,
                 auth_project_domain, region, auth_url):

        super(TestSenlinAPIClient, self).__init__()
        self.auth_result = None
        self.auth_user = auth_user
        self.auth_key = auth_key
        self.auth_project = auth_project
        self.auth_user_domain = auth_user_domain
        self.auth_project_domain = auth_project_domain
        self.region = region
        # We use keystone v3 API to do the functional test
        self.auth_url = auth_url.replace('v2.0', 'v3')
        self.catalogs = None

    def request(self, url, method='GET', body=None, headers=None):
        _headers = {
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        }

        if headers:
            _headers.update(headers)

        response = requests.request(method, url, data=body, headers=_headers)
        return response

    def _authenticate(self):
        if self.auth_result:
            return self.auth_result

        # We use password as the method and specify the scope when
        # performing authentication
        body = {
            'auth': {
                'identity': {
                    'methods': ['password'],
                    'password': {
                        'user': {
                            'domain': {
                                'name': self.auth_user_domain,
                            },
                            'name': self.auth_user,
                            'password': self.auth_key,
                        }
                    }
                },
                'scope': {
                    'project': {
                        'domain': {
                            'name': self.auth_project_domain
                        },
                        "name": self.auth_project,
                    }
                }
            }
        }
        auth_url = self.auth_url + '/auth/tokens'
        response = self.request(auth_url, method='POST',
                                body=jsonutils.dumps(body))

        http_status = response.status_code
        LOG.debug(_('Doing authentication: auth_url %(auth_url)s, status '
                    '%(http_status)s.'), {'auth_url': auth_url,
                                          'http_status': http_status})

        if http_status == 401:
            raise Exception(_('Authentication failed: %s'), response._content)

        self.auth_token = response.headers['X-Subject-Token']
        self.catalogs = jsonutils.loads(response._content)['token']['catalog']
        self.auth_result = self.auth_token

        return self.auth_token

    def api_request(self, http_method, relative_url, body=None,
                    resp_status=None, **kwargs):
        token = self._authenticate()

        endpoints = None
        for c in self.catalogs:
            if c['type'] == 'clustering':
                endpoints = c['endpoints']
                break
        if endpoints is None:
            raise Exception('Endpoints of clustering service was not found')

        endpoint = None
        for e in endpoints:
            if e['interface'] == 'admin' and e['region'] == self.region:
                endpoint = e['url']
                break
        if endpoint is None:
            raise Exception(_('Admin endpoint of clustering service in '
                              '%(region)s was not found.'
                              ), {'region': self.region})

        full_url = '%s/v1/%s' % (endpoint, relative_url)

        headers = kwargs.setdefault('headers', {})
        headers['X-Auth-Token'] = token
        headers['Content-Type'] = 'application/json'
        kwargs['method'] = http_method

        response = self.request(full_url, body=body, **kwargs)
        http_status = response.status_code
        LOG.debug(_('request url %(url)s, status_code %(status)s, response '
                    'body %(body)s'
                    ), {'url': relative_url, 'status': http_status,
                        'body': response._content})

        if resp_status:
            if http_status not in resp_status:
                raise SenlinApiException(message="Unexpected status code",
                                         response=response)

        return APIResponse(response)
