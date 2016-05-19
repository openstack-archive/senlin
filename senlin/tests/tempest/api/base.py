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

import time

from oslo_log import log
from tempest import config
from tempest.lib.common.utils import data_utils
from tempest.lib import exceptions
from tempest import test

from senlin.tests.tempest.common import clustering_client
from senlin.tests.tempest.common import constants

CONF = config.CONF
lOG = log.getLogger(__name__)


class BaseSenlinTest(test.BaseTestCase):

    credentials = ['primary']

    @classmethod
    def skip_checks(cls):
        super(BaseSenlinTest, cls).skip_checks()
        if not CONF.service_available.senlin:
            skip_msg = 'Senlin is disabled'
            raise cls.skipException(skip_msg)

    @classmethod
    def setup_clients(cls):
        super(BaseSenlinTest, cls).setup_clients()
        cls.client = clustering_client.ClusteringAPIClient(
            cls.os.auth_provider,
            CONF.clustering.catalog_type,
            CONF.identity.region,
            **cls.os.default_params_with_timeout_values
        )

    @classmethod
    def wait_for_status(cls, obj_type, obj_id, expected_status, timeout=None):
        if timeout is None:
            timeout = CONF.clustering.wait_timeout
        while timeout > 0:
            res = cls.client.get_obj(obj_type, obj_id)
            if res['body']['status'] == expected_status:
                return res
            time.sleep(5)
            timeout -= 5
        raise Exception('Timeout waiting for status.')

    @classmethod
    def wait_for_delete(cls, obj_type, obj_id, timeout=None):
        if timeout is None:
            timeout = CONF.clustering.wait_timeout
        while timeout > 0:
            try:
                cls.client.get_obj(obj_type, obj_id)
            except exceptions.NotFound:
                return
            time.sleep(5)
            timeout -= 5
        raise Exception('Timeout waiting for deletion.')

    @classmethod
    def create_test_cluster(cls, profile_id, desired_capacity,
                            min_size=None, max_size=None, timeout=None,
                            metadata=None, name=None, wait_timeout=None):
        """Utility function that generates a Senlin cluster.

        Create a Senlin cluster and return it after it is active. This
        function is for minimizing the code duplication that could
        happen in API test cases where a 'existing' Senlin cluster is needed.
        """
        if name is None:
            name = data_utils.rand_name("tempest-created-cluster")
        params = {
            'cluster': {
                'profile_id': profile_id,
                'desired_capacity': desired_capacity,
                'min_size': min_size,
                'max_size': max_size,
                'timeout': timeout,
                'metadata': metadata,
                'name': name
            }
        }
        res = cls.client.create_obj('clusters', params)
        cluster_id = res['body']['id']
        action_id = res['location'].split('/actions/')[1]
        cls.wait_for_status('actions', action_id, 'SUCCEEDED',
                            timeout=wait_timeout)
        res = cls.client.get_obj('clusters', cluster_id)
        return res['body']

    @classmethod
    def delete_test_cluster(cls, cluster_id, wait_timeout=None):
        """Utility function that deletes a Senlin cluster."""

        res = cls.client.delete_obj('clusters', cluster_id)
        action_id = res['location'].split('/actions/')[1]
        cls.wait_for_status('actions', action_id, 'SUCCEEDED',
                            timeout=wait_timeout)

    @classmethod
    def get_test_cluster(cls, cluster_id):
        """Utility function that get detail of a Senlin cluster."""

        res = cls.client.get_obj('clusters', cluster_id)
        return res['body']

    @classmethod
    def create_profile(cls, spec, name=None, metadata=None):
        """Utility function that generates a Senlin profile."""

        if name is None:
            name = data_utils.rand_name("tempest-created-profile")
        params = {
            'profile': {
                'name': name,
                'spec': spec,
                'metadata': metadata,
            }
        }
        res = cls.client.create_obj('profiles', params)
        return res['body']

    @classmethod
    def delete_profile(cls, profile_id, ignore_missing=False):
        """Utility function that deletes a Senlin profile."""
        res = cls.client.delete_obj('profiles', profile_id)
        if res['status'] == 404:
            if ignore_missing:
                return
            raise exceptions.NotFound()

    @classmethod
    def create_receiver(cls, cluster_id, action, r_type,
                        name=None, params=None):
        """Utility function that generates a Senlin receiver."""

        if name is None:
            name = data_utils.rand_name("tempest-created-receiver")
        body = {
            'receiver': {
                'name': name,
                'cluster_id': cluster_id,
                'type': r_type,
                'action': action,
                'params': params
            }
        }
        res = cls.client.create_obj('receivers', body)
        return res['body']

    @classmethod
    def delete_receiver(cls, receiver_id, ignore_missing=False):
        """Utility function that deletes a Senlin receiver."""
        res = cls.client.delete_obj('receivers', receiver_id)
        if res['status'] == 404:
            if ignore_missing:
                return
            raise exceptions.NotFound()

    @classmethod
    def create_test_node(cls, profile_id, cluster_id=None, metadata=None,
                         role=None, name=None, wait_timeout=None):
        """Utility function that generates a Senlin node.

        Create a Senlin node and return it after it is active. This
        function is for minimizing the code duplication that could
        happen in API test cases where a 'existing' Senlin node is needed.
        """
        if name is None:
            name = data_utils.rand_name("tempest-created-node")
        params = {
            'node': {
                'profile_id': profile_id,
                'cluster_id': cluster_id,
                'metadata': metadata,
                'role': role,
                'name': name
            }
        }
        res = cls.client.create_obj('nodes', params)
        node_id = res['body']['id']
        action_id = res['location'].split('/actions/')[1]
        cls.wait_for_status('actions', action_id, 'SUCCEEDED',
                            timeout=wait_timeout)
        res = cls.client.get_obj('nodes', node_id)
        return res['body']

    @classmethod
    def delete_test_node(cls, node_id, wait_timeout=None):
        """Utility function that deletes a Senlin node."""

        res = cls.client.delete_obj('nodes', node_id)
        action_id = res['location'].split('/actions/')[1]
        cls.wait_for_status('actions', action_id, 'SUCCEEDED',
                            timeout=wait_timeout)

    @classmethod
    def get_test_node(cls, node_id):
        """Utility function that get detail of a Senlin node."""

        res = cls.client.get_obj('nodes', node_id)
        return res['body']

    @classmethod
    def create_test_policy(cls, spec=None, name=None):
        """Utility function that generates a Senlin policy."""

        params = {
            'policy': {
                'name': name or data_utils.rand_name("tempest-created-policy"),
                'spec': spec or constants.spec_scaling_policy
            }
        }
        res = cls.client.create_obj('policies', params)
        return res['body']
