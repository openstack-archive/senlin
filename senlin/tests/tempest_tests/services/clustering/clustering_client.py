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
from tempest.lib.common import rest_client
from tempest.lib.common.utils import data_utils
from tempest.lib import exceptions


class ClusteringClient(rest_client.RestClient):
    version = 'v1'

    def get_obj(self, obj_type, obj_id):
        uri = '{0}/{1}/{2}'.format(self.version, obj_type, obj_id)
        resp, body = self.get(uri)
        self.expected_success(200, resp.status)
        return self._parse_resp(body)

    def create_profile(self, spec, name=None, metadata=None):
        if name is None:
            name = data_utils.rand_name("tempest-created-profile")
        uri = '{0}/profiles'.format(self.version)
        params = {
            'profile': {
                'name': name,
                'spec': spec,
                'metadata': metadata,
            }
        }
        resp, body = self.post(uri, body=jsonutils.dumps(params))
        self.expected_success(201, resp.status)
        return self._parse_resp(body)

    def list_profile(self):
        uri = '{0}/profiles'.format(self.version)
        resp, body = self.get(uri)
        self.expected_success(200, resp.status)
        return self._parse_resp(body)

    def delete_profile(self, profile_id, ignore_missing=False):
        uri = '{0}/profiles/{1}'.format(self.version, profile_id)
        try:
            resp, body = self.delete(uri)
        except exceptions.NotFound as ex:
            if ignore_missing:
                return
            raise ex
        self.expected_success(204, resp.status)

    def show_profile(self, profile_id):
        uri = '{0}/profiles/{1}'.format(self.version, profile_id)
        resp, body = self.get(uri)
        self.expected_success(200, resp.status)
        return self._parse_resp(body)

    def update_profile(self, profile_id, name=None, metadata=None):
        uri = '{0}/profiles/{1}'.format(self.version, profile_id)
        params = {}
        if name:
            params['name'] = name
        if metadata:
            params['metadata'] = metadata
        data = {'profile': params}
        resp, body = self.patch(uri, body=jsonutils.dumps(data))
        self.expected_success(200, resp.status)
        return self._parse_resp(body)

    def create_cluster(self, profile_id, desired_capacity,
                       min_size=None, max_size=None, timeout=None,
                       metadata=None, name=None):
        if name is None:
            name = data_utils.rand_name("tempest-created-cluster")
        params = {
            'cluster': {
                'name': name,
                'profile_id': profile_id,
                'desired_capacity': desired_capacity,
                'min_size': min_size,
                'max_size': max_size,
                'timeout': timeout,
                'metadata': metadata,
            }
        }
        uri = '{0}/clusters'.format(self.version)
        resp, body = self.post(uri, body=jsonutils.dumps(params))
        self.expected_success(202, resp.status)
        action_id = resp['location'].split('/actions/')[1]
        return self._parse_resp(body), action_id

    def list_cluster(self):
        uri = '{0}/clusters'.format(self.version)
        resp, body = self.get(uri)
        self.expected_success(200, resp.status)
        return self._parse_resp(body)

    def delete_cluster(self, cluster_id, ignore_missing=False):
        uri = '{0}/clusters/{1}'.format(self.version, cluster_id)
        try:
            resp, body = self.delete(uri)
        except exceptions.NotFound as ex:
            if ignore_missing:
                return
            raise ex
        self.expected_success(202, resp.status)
        action_id = resp['location'].split('/actions/')[1]
        return action_id

    def show_cluster(self, cluster_id):
        uri = '{0}/clusters/{1}'.format(self.version, cluster_id)
        resp, body = self.get(uri)
        self.expected_success(200, resp.status)
        return self._parse_resp(body)

    def update_cluster(self, cluster_id, name=None, metadata=None,
                       timeout=None, profile_id=None):
        uri = '{0}/clusters/{1}'.format(self.version, cluster_id)
        params = {}
        if name:
            params['name'] = name
        if metadata:
            params['metadata'] = metadata
        if timeout:
            params['timeout'] = timeout
        if profile_id:
            params['profile_id'] = profile_id
        data = {'cluster': params}
        resp, body = self.patch(uri, body=jsonutils.dumps(data))
        self.expected_success(202, resp.status)
        action_id = resp['location'].split('/actions/')[1]
        return action_id

    def create_node(self, profile_id, cluster_id=None, metadata=None,
                    name=None):
        if name is None:
            name = data_utils.rand_name("tempest-created-node")
        params = {
            'node': {
                'name': name,
                'profile_id': profile_id,
                'cluster_id': cluster_id,
                'metadata': metadata,
            }
        }
        uri = '{0}/nodes'.format(self.version)
        resp, body = self.post(uri, body=jsonutils.dumps(params))
        self.expected_success(202, resp.status)
        action_id = resp['location'].split('/actions/')[1]
        return self._parse_resp(body), action_id

    def list_node(self):
        uri = '{0}/nodes'.format(self.version)
        resp, body = self.get(uri)
        self.expected_success(200, resp.status)
        return self._parse_resp(body)

    def delete_node(self, node_id, ignore_missing=False):
        uri = '{0}/nodes/{1}'.format(self.version, node_id)
        try:
            resp, body = self.delete(uri)
        except exceptions.NotFound as ex:
            if ignore_missing:
                return
            raise ex
        self.expected_success(202, resp.status)
        action_id = resp['location'].split('/actions/')[1]
        return action_id

    def show_node(self, node_id, show_details=False):
        uri = '{0}/nodes/{1}'.format(self.version, node_id)
        if show_details:
            uri += '?show_details=True'
        resp, body = self.get(uri)
        self.expected_success(200, resp.status)
        return self._parse_resp(body)

    def update_node(self, node_id, name=None, metadata=None,
                    profile_id=None):
        uri = '{0}/nodes/{1}'.format(self.version, node_id)
        params = {}
        if name:
            params['name'] = name
        if metadata:
            params['metadata'] = metadata
        if profile_id:
            params['profile_id'] = profile_id
        data = {'node': params}
        resp, body = self.patch(uri, body=jsonutils.dumps(data))
        self.expected_success(202, resp.status)
        action_id = resp['location'].split('/actions/')[1]
        return action_id
