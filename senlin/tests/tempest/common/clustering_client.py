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

from six.moves.urllib import parse as urllib

from oslo_serialization import jsonutils
from tempest.lib.common import rest_client


class ClusteringAPIClient(rest_client.RestClient):
    version = 'v1'

    def _parsed_resp(self, resp, body):
        res = {
            'status': int(resp['status']),
            'location': resp.get('location', None),
        }
        if body and str(body) != 'null':
            res['body'] = self._parse_resp(body)
        else:
            res['body'] = None

        return res

    def get_obj(self, obj_type, obj_id):
        uri = '{0}/{1}/{2}'.format(self.version, obj_type, obj_id)
        resp, body = self.get(uri)

        return self._parsed_resp(resp, body)

    def create_obj(self, obj_type, attrs):
        uri = '{0}/{1}'.format(self.version, obj_type)
        resp, body = self.post(uri, body=jsonutils.dumps(attrs))

        return self._parsed_resp(resp, body)

    def list_objs(self, obj_type, params=None):
        uri = '{0}/{1}'.format(self.version, obj_type)
        if params:
            uri += '?{0}'.format(urllib.urlencode(params))
        resp, body = self.get(uri)

        return self._parsed_resp(resp, body)

    def update_obj(self, obj_type, obj_id, attrs):
        uri = '{0}/{1}/{2}'.format(self.version, obj_type, obj_id)
        resp, body = self.patch(uri, body=jsonutils.dumps(attrs))

        return self._parsed_resp(resp, body)

    def delete_obj(self, obj_type, obj_id):
        uri = '{0}/{1}/{2}'.format(self.version, obj_type, obj_id)
        resp, body = self.delete(uri)

        return self._parsed_resp(resp, body)

    def trigger_webhook(self, webhook_url, params=None):
        if params is not None:
            params = jsonutils.dumps(params)
        resp, body = self.raw_request(webhook_url, 'POST', body=params)
        return self._parsed_resp(resp, body)

    def trigger_action(self, obj_type, obj_id, params=None):
        uri = '{0}/{1}/{2}/actions'.format(self.version, obj_type, obj_id)
        if params is not None:
            params = jsonutils.dumps(params)
        resp, body = self.post(uri, body=params)

        return self._parsed_resp(resp, body)

    def list_cluster_policies(self, cluster_id, params=None):
        uri = '{0}/clusters/{1}/policies'.format(self.version, cluster_id)
        if params:
            uri += '?{0}'.format(urllib.urlencode(params))

        resp, body = self.get(uri)

        return self._parsed_resp(resp, body)

    def get_cluster_policy(self, cluster_id, policy_id):
        uri = '{0}/clusters/{1}/policies/{2}'.format(self.version, cluster_id,
                                                     policy_id)
        resp, body = self.get(uri)

        return self._parsed_resp(resp, body)
