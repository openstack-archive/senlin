#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from oslo_serialization import jsonutils
from oslo_utils import uuidutils
from tempest import config
from tempest.lib.common import rest_client

CONF = config.CONF


class V2MessagingClient(rest_client.RestClient):
    def __init__(self, auth_provider, service, region, **kwargs):
        super(V2MessagingClient, self).__init__(
            auth_provider, service, region, **kwargs)

        self.uri_prefix = 'v2'

        client_id = uuidutils.generate_uuid()
        self.headers = {'Client-ID': client_id}

    def get_resp(self, resp, body):
        # Parse status code and location
        res = {
            'status': int(resp.pop('status')),
            'location': resp.pop('location', None)
        }
        # Parse other keys included in resp
        res.update(resp)

        # Parse body
        res['body'] = self._parse_resp(body)
        return res

    def post_messages(self, queue_name, messages):
        uri = '{0}/queues/{1}/messages'.format(self.uri_prefix, queue_name)
        resp, body = self.post(uri, body=jsonutils.dumps(messages),
                               extra_headers=True,
                               headers=self.headers)

        return self.get_resp(resp, body)
