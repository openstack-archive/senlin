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
import time

from oslo_serialization import jsonutils
from oslo_utils import timeutils
from tempest import config
from tempest.lib.common import rest_client
from tempest.lib import exceptions

CONF = config.CONF


class ClusteringAPIClient(rest_client.RestClient):
    version = 'v1'
    api_microversion = 'latest'

    def get_headers(self, accept_type=None, send_type=None):
        headers = super(ClusteringAPIClient, self).get_headers(
            accept_type=accept_type, send_type=send_type)
        headers['openstack-api-version'] = ('clustering %s' %
                                            self.api_microversion)
        return headers

    def get_resp(self, resp, body):
        # Parse status code and location
        res = {
            'status': int(resp.pop('status')),
            'location': resp.pop('location', None)
        }
        # Parse other keys included in resp
        res.update(resp)

        # Parse body
        if body and str(body) != 'null':
            res['body'] = self._parse_resp(body)
        else:
            res['body'] = None

        return res

    def get_obj(self, obj_type, obj_id, params=None):
        uri = '{0}/{1}/{2}'.format(self.version, obj_type, obj_id)
        if params:
            uri += '?{0}'.format(urllib.urlencode(params))
        resp, body = self.get(uri)

        return self.get_resp(resp, body)

    def create_obj(self, obj_type, attrs):
        uri = '{0}/{1}'.format(self.version, obj_type)
        resp, body = self.post(uri, body=jsonutils.dumps(attrs))

        return self.get_resp(resp, body)

    def list_objs(self, obj_type, params=None):
        uri = '{0}/{1}'.format(self.version, obj_type)
        if params:
            uri += '?{0}'.format(urllib.urlencode(params))
        resp, body = self.get(uri)

        return self.get_resp(resp, body)

    def update_obj(self, obj_type, obj_id, attrs):
        uri = '{0}/{1}/{2}'.format(self.version, obj_type, obj_id)
        resp, body = self.patch(uri, body=jsonutils.dumps(attrs))

        return self.get_resp(resp, body)

    def delete_obj(self, obj_type, obj_id):
        uri = '{0}/{1}/{2}'.format(self.version, obj_type, obj_id)
        resp, body = self.delete(uri)

        return self.get_resp(resp, body)

    def validate_obj(self, obj_type, attrs):
        uri = '{0}/{1}/validate'.format(self.version, obj_type)
        headers = {'openstack-api-version': 'clustering 1.2'}
        resp, body = self.post(uri, body=jsonutils.dumps(attrs),
                               headers=headers)

        return self.get_resp(resp, body)

    def trigger_webhook(self, webhook_url, params=None):
        if params is not None:
            params = jsonutils.dumps(params)
        resp, body = self.raw_request(webhook_url, 'POST', body=params)
        return self.get_resp(resp, body)

    def trigger_action(self, obj_type, obj_id, params=None):
        uri = '{0}/{1}/{2}/actions'.format(self.version, obj_type, obj_id)
        if params is not None:
            params = jsonutils.dumps(params)
        resp, body = self.post(uri, body=params)

        return self.get_resp(resp, body)

    def trigger_operation(self, obj_type, obj_id, params):
        uri = '{0}/{1}/{2}/ops'.format(self.version, obj_type, obj_id)
        data = jsonutils.dumps(params)
        resp, body = self.post(uri, body=data)
        return self.get_resp(resp, body)

    def cluster_replace_nodes(self, obj_type, obj_id, params=None):
        uri = '{0}/{1}/{2}/actions'.format(self.version, obj_type, obj_id)
        if params is not None:
            params = jsonutils.dumps(params)
        headers = self.get_headers()
        resp, body = self.post(uri, body=params, headers=headers)

        return self.get_resp(resp, body)

    def list_cluster_policies(self, cluster_id, params=None):
        uri = '{0}/clusters/{1}/policies'.format(self.version, cluster_id)
        if params:
            uri += '?{0}'.format(urllib.urlencode(params))

        resp, body = self.get(uri)

        return self.get_resp(resp, body)

    def get_cluster_policy(self, cluster_id, policy_id):
        uri = '{0}/clusters/{1}/policies/{2}'.format(self.version, cluster_id,
                                                     policy_id)
        resp, body = self.get(uri)

        return self.get_resp(resp, body)

    def cluster_collect(self, cluster, path):
        uri = '{0}/clusters/{1}/attrs/{2}'.format(self.version, cluster, path)
        resp, body = self.get(uri)

        return self.get_resp(resp, body)

    def wait_for_status(self, obj_type, obj_id, expected_status, timeout=None):
        if timeout is None:
            timeout = CONF.clustering.wait_timeout

        with timeutils.StopWatch(timeout) as timeout_watch:
            while timeout > 0:
                res = self.get_obj(obj_type, obj_id)
                if res['body']['status'] == expected_status:
                    return res
                time.sleep(5)
                timeout = timeout_watch.leftover(True)

        raise Exception('Timeout waiting for status.')

    def wait_for_delete(self, obj_type, obj_id, timeout=None):
        if timeout is None:
            timeout = CONF.clustering.wait_timeout

        with timeutils.StopWatch(timeout) as timeout_watch:
            while timeout > 0:
                try:
                    self.get_obj(obj_type, obj_id)
                except exceptions.NotFound:
                    return
                time.sleep(5)
                timeout = timeout_watch.leftover(True)

        raise Exception('Timeout waiting for deletion.')


class ClusteringFunctionalClient(ClusteringAPIClient):
    """This is the tempest client for Senlin functional test"""
    pass


class ClusteringIntegrationClient(ClusteringAPIClient):
    """This is the tempest client for Senlin integration test"""
    pass
