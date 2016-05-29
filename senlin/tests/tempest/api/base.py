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

from senlin.tests.tempest.common import clustering_client

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
