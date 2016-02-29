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


from senlin.db.sqlalchemy import api as db_api
from senlin.tests.unit.common import base
from senlin.tests.unit.common import utils


class DBAPIRegistryTest(base.SenlinTestCase):
    def setUp(self):
        super(DBAPIRegistryTest, self).setUp()
        self.ctx = utils.dummy_context()

        db_api.service_create(self.ctx, 'SERVICE_ID')

    def _create_registry(self, cluster_id, check_type, interval, params,
                         engine_id):
        return db_api.registry_create(self.ctx, cluster_id, check_type,
                                      interval, params, engine_id)

    def test_registry_create_get(self):
        registry = self._create_registry(cluster_id='CLUSTER_ID',
                                         check_type='NODE_STATUS_POLLING',
                                         interval=60,
                                         params={},
                                         engine_id='ENGINE_ID')
        ret_registries = db_api.registry_claim(self.ctx, registry.engine_id)
        self.assertEqual(1, len(ret_registries))
        ret_registry = ret_registries[0]
        self.assertEqual(registry.id, ret_registry.id)
        self.assertEqual(registry.cluster_id, ret_registry.cluster_id)
        self.assertEqual(registry.check_type, ret_registry.check_type)
        self.assertEqual(registry.interval, ret_registry.interval)
        self.assertEqual(registry.params, ret_registry.params)
        self.assertEqual(registry.engine_id, ret_registry.engine_id)

    def test_registry_claim(self):
        for i in range(2):
            cluster_id = 'cluster-%s' % i
            self._create_registry(cluster_id=cluster_id,
                                  check_type='NODE_STATUS_POLLING',
                                  interval=60,
                                  params={},
                                  engine_id='DEAD_ENGINE')

        registries = db_api.registry_claim(self.ctx, engine_id='ENGINE_ID')
        self.assertEqual(2, len(registries))
        self.assertEqual('ENGINE_ID', registries[0].engine_id)
        self.assertEqual('ENGINE_ID', registries[1].engine_id)

    def test_registry_delete(self):
        registry = self._create_registry('CLUSTER_ID',
                                         check_type='NODE_STATUS_POLLING',
                                         interval=60,
                                         params={},
                                         engine_id='ENGINE_ID')
        db_api.registry_delete(self.ctx, 'CLUSTER_ID')
        self.assertEqual([], db_api.registry_claim(self.ctx,
                                                   registry.engine_id))
