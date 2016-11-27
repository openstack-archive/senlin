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

from oslo_utils import timeutils
from oslo_utils import uuidutils
import testtools

from senlin.common import exception as senlin_exc
from senlin.objects import action as action_obj
from senlin.objects import cluster as cluster_obj
from senlin.objects.notifications import cluster
from senlin.objects.notifications import exception as exc


class TestClusterPayload(testtools.TestCase):

    def setUp(self):
        super(TestClusterPayload, self).setUp()

        uuid = uuidutils.generate_uuid()
        prof_uuid = uuidutils.generate_uuid()
        parent_uuid = uuidutils.generate_uuid()
        dt = timeutils.utcnow(True)
        self.params = {
            'id': uuid,
            'name': 'fake_name',
            'profile_id': prof_uuid,
            'parent': parent_uuid,
            'init_at': dt,
            'created_at': dt,
            'updated_at': dt,
            'min_size': 1,
            'max_size': 10,
            'desired_capacity': 5,
            'timeout': 4,
            'status': 'ACTIVE',
            'status_reason': 'Good',
            'metadata': {'foo': 'bar'},
            'data': {'key': 'value'},
            'user': 'user1',
            'project': 'project1',
            'domain': 'domain1',
            'dependents': {'zoo': {'lion', 'deer'}}
        }

    def _verify_equality(self, obj, params):
        for k, v in params.items():
            self.assertTrue(obj.obj_attr_is_set(k))
            self.assertEqual(v, getattr(obj, k))

    def test_create(self):
        sot = cluster.ClusterPayload(**self.params)
        self._verify_equality(sot, self.params)

    def test_create_with_required_fields(self):
        params = {
            'id': uuidutils.generate_uuid(),
            'name': 'fake_name',
            'profile_id': uuidutils.generate_uuid(),
            'init_at': timeutils.utcnow(True),
            'min_size': 1,
            'max_size': 10,
            'desired_capacity': 5,
            'timeout': 4,
            'status': 'ACTIVE',
            'status_reason': 'Good',
            'user': 'user1',
            'project': 'project1',
        }

        sot = cluster.ClusterPayload(**params)

        self._verify_equality(sot, params)

    def test_create_with_obj(self):
        c1 = cluster_obj.Cluster(**self.params)

        sot = cluster.ClusterPayload.from_cluster(c1)

        self._verify_equality(sot, self.params)


class TestActionPayload(testtools.TestCase):

    def setUp(self):
        super(TestActionPayload, self).setUp()

        uuid = uuidutils.generate_uuid()
        target_uuid = uuidutils.generate_uuid()
        dt = timeutils.utcnow(True)
        self.params = {
            'id': uuid,
            'name': 'fake_name',
            'created_at': dt,
            'target': target_uuid,
            'action': 'CLUSTER_CREATE',
            'start_time': 1.23,
            'end_time': 4.56,
            'timeout': 78,
            'status': 'RUNNING',
            'status_reason': 'Clear',
            'inputs': {'key': 'value'},
            'outputs': {'foo': 'bar'},
            'data': {'zoo': 'nar'},
            'user': 'user1',
            'project': 'project1',
        }

    def _verify_equality(self, obj, params):
        for k, v in params.items():
            self.assertTrue(obj.obj_attr_is_set(k))
            self.assertEqual(v, getattr(obj, k))

    def test_create(self):
        sot = cluster.ActionPayload(**self.params)
        self._verify_equality(sot, self.params)

    def test_create_with_required_fields(self):
        params = {
            'id': uuidutils.generate_uuid(),
            'name': 'fake_name',
            'target': uuidutils.generate_uuid(),
            'action': 'CLUSTER_CREATE',
            'start_time': 1.23,
            'status': 'RUNNING',
            'status_reason': 'Good',
            'user': 'user1',
            'project': 'project1',
        }

        sot = cluster.ActionPayload(**params)

        self._verify_equality(sot, params)

    def test_create_with_obj(self):
        a1 = action_obj.Action(**self.params)

        sot = cluster.ActionPayload.from_action(a1)

        self._verify_equality(sot, self.params)


class TestClusterActionPayload(testtools.TestCase):

    def setUp(self):
        super(TestClusterActionPayload, self).setUp()

        cluster_params = {
            'id': uuidutils.generate_uuid(),
            'name': 'fake_name',
            'profile_id': uuidutils.generate_uuid(),
            'init_at': timeutils.utcnow(True),
            'min_size': 1,
            'max_size': 10,
            'desired_capacity': 5,
            'timeout': 4,
            'status': 'ACTIVE',
            'status_reason': 'Good',
            'user': 'user1',
            'project': 'project1',
        }
        self.cluster = cluster_obj.Cluster(**cluster_params)
        action_params = {
            'id': uuidutils.generate_uuid(),
            'name': 'fake_name',
            'target': uuidutils.generate_uuid(),
            'action': 'CLUSTER_CREATE',
            'start_time': 1.23,
            'status': 'RUNNING',
            'status_reason': 'Good',
            'user': 'user1',
            'project': 'project1',
        }
        self.action = action_obj.Action(**action_params)

    def test_create(self):
        exobj = None
        try:
            {}['key']
        except Exception:
            ex = senlin_exc.InvalidSpec(message='boom')
            exobj = exc.ExceptionPayload.from_exception(ex)

        sot = cluster.ClusterActionPayload(cluster=self.cluster,
                                           action=self.action,
                                           exception=exobj)

        self.assertTrue(sot.obj_attr_is_set('cluster'))
        self.assertTrue(sot.obj_attr_is_set('action'))
        self.assertTrue(sot.obj_attr_is_set('exception'))
        self.assertIsNotNone(sot.exception)

    def test_create_with_no_exc(self):
        ex = None
        sot = cluster.ClusterActionPayload(cluster=self.cluster,
                                           action=self.action,
                                           exception=ex)

        self.assertTrue(sot.obj_attr_is_set('cluster'))
        self.assertTrue(sot.obj_attr_is_set('action'))
        self.assertTrue(sot.obj_attr_is_set('exception'))
        self.assertIsNone(sot.exception)


class TestClusterActionNotification(testtools.TestCase):

    def setUp(self):
        super(TestClusterActionNotification, self).setUp()

        cluster_params = {
            'id': uuidutils.generate_uuid(),
            'name': 'fake_name',
            'profile_id': uuidutils.generate_uuid(),
            'init_at': timeutils.utcnow(True),
            'min_size': 1,
            'max_size': 10,
            'desired_capacity': 5,
            'timeout': 4,
            'status': 'ACTIVE',
            'status_reason': 'Good',
            'user': 'user1',
            'project': 'project1',
        }
        self.cluster = cluster_obj.Cluster(**cluster_params)
        action_params = {
            'id': uuidutils.generate_uuid(),
            'name': 'fake_name',
            'target': uuidutils.generate_uuid(),
            'action': 'CLUSTER_CREATE',
            'start_time': 1.23,
            'status': 'RUNNING',
            'status_reason': 'Good',
            'user': 'user1',
            'project': 'project1',
        }
        self.action = action_obj.Action(**action_params)

    def test_create(self):
        payload = cluster.ClusterActionPayload(cluster=self.cluster,
                                               action=self.action)

        sot = cluster.ClusterActionNotification(payload=payload)

        self.assertTrue(sot.obj_attr_is_set('payload'))
