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
import datetime

from oslo_utils import timeutils
from oslo_utils import uuidutils

from senlin.db.sqlalchemy import api as db_api
from senlin.db.sqlalchemy import models
from senlin.tests.unit.common import base
from senlin.tests.unit.common import utils


class DBAPIServiceTest(base.SenlinTestCase):
    def setUp(self):
        super(DBAPIServiceTest, self).setUp()
        self.ctx = utils.dummy_context()

    def _create_service(self, service_id=None, **kwargs):
        service_id = service_id or 'f9aff81e-bc1f-4119-941d-ad1ea7f31d19'
        values = {
            'host': 'host1.devstack.org',
            'binary': 'senlin-engine',
            'topic': 'engine',
        }
        values.update(kwargs)

        with db_api.session_for_write() as session:
            time_now = timeutils.utcnow(True)
            svc = models.Service(
                id=service_id,
                host=values.get('host'),
                binary=values.get('binary'),
                topic=values.get('topic'),
                created_at=values.get('created_at') or time_now,
                updated_at=values.get('updated_at') or time_now,
            )
            session.add(svc)

        return svc

    def test_service_create_get(self):
        service = self._create_service()

        ret_service = db_api.service_get(service.id)

        self.assertIsNotNone(ret_service)
        self.assertEqual(service.id, ret_service.id)
        self.assertEqual(service.binary, ret_service.binary)
        self.assertEqual(service.host, ret_service.host)
        self.assertEqual(service.topic, ret_service.topic)
        self.assertEqual(service.disabled, ret_service.disabled)
        self.assertEqual(service.disabled_reason, ret_service.disabled_reason)
        self.assertIsNotNone(service.created_at)
        self.assertIsNotNone(service.updated_at)

    def test_service_get_all(self):
        for i in range(4):
            service_id = uuidutils.generate_uuid()
            values = {'host': 'host-%s' % i}
            self._create_service(service_id, **values)

        services = db_api.service_get_all()

        self.assertEqual(4, len(services))

    def test_service_get_all_expired(self):
        for index in range(6):
            dt = timeutils.utcnow() - datetime.timedelta(seconds=60 * index)
            values = {
                'binary': 'senlin-health-manager',
                'host': 'host-%s' % index,
                'updated_at': dt
            }
            self._create_service(uuidutils.generate_uuid(), **values)

        for index in range(8):
            dt = timeutils.utcnow() - datetime.timedelta(seconds=60 * index)
            values = {
                'binary': 'senlin-engine',
                'host': 'host-%s' % index,
                'updated_at': dt
            }
            self._create_service(uuidutils.generate_uuid(), **values)

        services = db_api.service_get_all_expired('senlin-health-manager')
        self.assertEqual(3, len(services.all()))

        services = db_api.service_get_all_expired('senlin-engine')
        self.assertEqual(5, len(services.all()))

    def test_service_update(self):
        old_service = self._create_service()
        old_updated_time = old_service.updated_at
        values = {'host': 'host-updated'}

        new_service = db_api.service_update(old_service.id, values)

        self.assertEqual('host-updated', new_service.host)
        self.assertGreater(new_service.updated_at, old_updated_time)

    def test_service_update_values_none(self):
        old_service = self._create_service()
        old_updated_time = old_service.updated_at
        new_service = db_api.service_update(old_service.id)
        self.assertGreater(new_service.updated_at, old_updated_time)

    def test_service_delete(self):
        service = self._create_service()

        db_api.service_delete(service.id)

        res = db_api.service_get(service.id)
        self.assertIsNone(res)
