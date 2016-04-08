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
from tempest.lib import exceptions
from tempest import test
# from tempest_lib.common.utils import data_utils

from senlin.tests.tempest_tests.services.clustering import clustering_client

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
        cls.client = clustering_client.ClusteringClient(
            cls.os.auth_provider,
            CONF.clustering.catalog_type,
            CONF.identity.region,
            **cls.os.default_params_with_timeout_values
        )

    def wait_for_status(self, obj_type, obj_id, expected_status, timeout=None):
        if timeout is None:
            timeout = CONF.clustering.wait_timeout
        while timeout > 0:
            res = self.client.get_obj(obj_type, obj_id)
            if res['status'] == expected_status:
                return res
            time.sleep(5)
            timeout -= 5
        raise Exception('Timeout waiting for status.')

    def wait_for_delete(self, obj_type, obj_id, timeout=None):
        if timeout is None:
            timeout = CONF.clustering.wait_timeout
        while timeout > 0:
            try:
                self.client.get_obj(obj_type, obj_id)
            except exceptions.NotFound:
                return
            time.sleep(5)
            timeout -= 5
        raise Exception('Timeout waiting for deletion.')

    def _create_cluster(self, profile_id, desired_capacity,
                        min_size=None, max_size=None, timeout=None,
                        metadata=None, name=None, wait_timeout=None):
        cluster, action_id = self.client.create_cluster(
            profile_id, desired_capacity, min_size=min_size,
            max_size=max_size, timeout=timeout, metadata=metadata, name=name)
        self.wait_for_status('actions', action_id, 'SUCCEEDED',
                             timeout=wait_timeout)
        cluster = self.client.show_cluster(cluster['id'])
        if name is None:
            self.assertIn("tempest-created-cluster", cluster['name'])
        else:
            self.assertIn(name, cluster['name'])
        self.assertEqual(desired_capacity, cluster['desired_capacity'])
        self.assertEqual(desired_capacity, len(cluster['nodes']))
        if min_size is not None:
            self.assertEqual(min_size, cluster['min_size'])
        if max_size is not None:
            self.assertEqual(max_size, cluster['max_size'])
        if metadata is not None:
            self.assertEqual(metadata, cluster['metadata'])
        if timeout is not None:
            self.assertEqual(timeout, cluster['timeout'])
        return cluster

    def _delete_cluster(self, cluster, wait_timeout=None):
        action_id = self.client.delete_cluster(cluster)
        self.wait_for_status('actions', action_id, 'SUCCEEDED',
                             timeout=wait_timeout)
