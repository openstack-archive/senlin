# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

from tempest.lib import decorators
from tempest.lib import exceptions

from senlin.tests.tempest.api import base
from senlin.tests.tempest.common import utils


class TestClusterActionResize(base.BaseSenlinAPITest):

    def setUp(self):
        super(TestClusterActionResize, self).setUp()
        profile_id = utils.create_a_profile(self)
        self.addCleanup(utils.delete_a_profile, self, profile_id)
        self.cluster_id = utils.create_a_cluster(self, profile_id)
        self.addCleanup(utils.delete_a_cluster, self, self.cluster_id)

    @decorators.idempotent_id('f5f75882-df3d-481f-bd05-019e4d08af65')
    def test_cluster_action_resize(self):
        params = {
            "resize": {
                "adjustment_type": "CHANGE_IN_CAPACITY",
                "max_size": 20,
                "min_step": 1,
                "min_size": 5,
                "number": 20,
            }
        }
        # Trigger cluster action
        res = self.client.trigger_action('clusters', self.cluster_id,
                                         params=params)

        # Verify resp code, body and location in headers
        self.assertEqual(202, res['status'])
        self.assertIn('actions', res['location'])

        action_id = res['location'].split('/actions/')[1]
        self.client.wait_for_status('actions', action_id, 'SUCCEEDED')


class TestClusterResizeNegativeInvalidResizeParams(base.BaseSenlinAPITest):

    @decorators.idempotent_id('57bc61a2-df38-4bf5-a26a-d23d2cc67ca3')
    def test_cluster_resize_invalid_adj_type(self):
        params = {
            "resize": {
                "adjustment_type": "bogus",
                "max_size": 20,
                "min_size": 5,
                "number": 5
            }
        }

        # Verify badrequest exception(400) is raised.
        ex = self.assertRaises(exceptions.BadRequest,
                               self.client.trigger_action,
                               'clusters', 'cluster_id', params)

        message = ex.resp_body['error']['message']
        self.assertEqual(
            "Value 'bogus' is not acceptable for field "
            "'adjustment_type'.", str(message))

    @decorators.idempotent_id('cef85ed4-9dd3-4f9f-91fe-4372d9aa8956')
    def test_cluster_resize_missing_adj_type(self):
        params = {
            "resize": {
                "max_size": 20,
                "min_size": 5,
                "number": 5
            }
        }

        # Verify badrequest exception(400) is raised.
        ex = self.assertRaises(exceptions.BadRequest,
                               self.client.trigger_action,
                               'clusters', 'cluster_id', params)

        message = ex.resp_body['error']['message']
        self.assertEqual(
            "Missing adjustment_type value for size adjustment.",
            str(message))

    @decorators.idempotent_id('e42dd7e1-aa36-4e46-8b5b-2571d00574c9')
    def test_cluster_resize_missing_adj_number(self):
        params = {
            "resize": {
                "adjustment_type": "CHANGE_IN_CAPACITY",
                "max_size": 20,
                "min_size": 5
            }
        }

        # Verify badrequest exception(400) is raised.
        ex = self.assertRaises(exceptions.BadRequest,
                               self.client.trigger_action,
                               'clusters', 'cluster_id', params)

        message = ex.resp_body['error']['message']
        self.assertEqual(
            "Missing number value for size adjustment.",
            str(message))

    @decorators.idempotent_id('7e669b3e-8fbd-4820-a281-7cc4b29c6020')
    def test_cluster_resize_invalid_adj_number(self):
        params = {
            "resize": {
                "adjustment_type": "EXACT_CAPACITY",
                "max_size": 20,
                "min_size": 5,
                "number": -1
            }
        }

        # Verify badrequest exception(400) is raised.
        ex = self.assertRaises(exceptions.BadRequest,
                               self.client.trigger_action,
                               'clusters', 'cluster_id', params)

        message = ex.resp_body['error']['message']
        self.assertEqual(
            "The 'number' must be positive integer for adjustment "
            "type 'EXACT_CAPACITY'.", str(message))

    @decorators.idempotent_id('5a069782-d6d8-4389-a68c-beb32375a39e')
    def test_cluster_resize_min_size_over_max_size(self):
        params = {
            "resize": {
                "adjustment_type": "CHANGE_IN_CAPACITY",
                "max_size": 10,
                "min_size": 20,
                "number": 5
            }
        }

        # Verify badrequest exception(400) is raised.
        ex = self.assertRaises(exceptions.BadRequest,
                               self.client.trigger_action,
                               'clusters', 'cluster_id', params)

        message = ex.resp_body['error']['message']
        self.assertEqual(
            "The specified min_size (20) is greater than the "
            "specified max_size (10).", str(message))


class TestClusterResizeNegativeClusterNotFound(base.BaseSenlinAPITest):
    @decorators.idempotent_id('087ef694-55d2-4616-a58b-1073cacb2bcd')
    def test_cluster_resize_cluster_not_found(self):
        params = {
            "resize": {
                "adjustment_type": "CHANGE_IN_CAPACITY",
                "max_size": 20,
                "min_size": 5,
                "number": 5
            }
        }

        # Verify notfound exception(404) is raised.
        ex = self.assertRaises(exceptions.NotFound,
                               self.client.trigger_action, 'clusters',
                               '087ef694-55d2-4616-a58b-1073cacb2bcd',
                               params)

        message = ex.resp_body['error']['message']
        self.assertEqual(
            "The cluster '087ef694-55d2-4616-a58b-1073cacb2bcd' could "
            "not be found.", str(message))


class TestClusterResizeNegativeSizeCheckFailed(base.BaseSenlinAPITest):

    def setUp(self):
        super(TestClusterResizeNegativeSizeCheckFailed, self).setUp()
        profile_id = utils.create_a_profile(self)
        self.addCleanup(utils.delete_a_profile, self, profile_id)
        self.cluster_id = utils.create_a_cluster(self, profile_id,
                                                 min_size=2, max_size=5,
                                                 desired_capacity=3)
        self.addCleanup(utils.delete_a_cluster, self, self.cluster_id)

    @decorators.idempotent_id('92e7d3c8-2d38-4766-86c3-41dc14bf89a1')
    def test_cluster_resize_break_upper_limit(self):
        # New desired_capacity will be greater than max_size
        params = {
            "resize": {
                "adjustment_type": "CHANGE_IN_CAPACITY",
                "number": 3,
                "strict": True
            }
        }

        # Verify badrequest exception(400) is raised.
        ex = self.assertRaises(exceptions.BadRequest,
                               self.client.trigger_action,
                               'clusters', self.cluster_id, params)

        message = ex.resp_body['error']['message']
        self.assertEqual(
            "The target capacity (6) is greater than the cluster's "
            "max_size (5).", str(message))

    @decorators.idempotent_id('9dcac577-d768-44d1-b119-02d27202ef08')
    def test_cluster_resize_break_lower_limit(self):
        # New desired_capacity will be less than min_size
        params = {
            "resize": {
                "adjustment_type": "CHANGE_IN_CAPACITY",
                "number": -2,
                "strict": True
            }
        }

        # Verify badrequest exception(400) is raised.
        ex = self.assertRaises(exceptions.BadRequest,
                               self.client.trigger_action,
                               'clusters', self.cluster_id, params)

        message = ex.resp_body['error']['message']
        self.assertEqual(
            "The target capacity (1) is less than the cluster's "
            "min_size (2).", str(message))

    @decorators.idempotent_id('d7a96d95-2944-4749-be34-cfe39a5dbcb4')
    def test_cluster_resize_max_size_under_current_desired_capacity(self):
        # New max_size is less than current desired_capacity of cluster
        params = {
            "resize": {
                "max_size": 2,
                "strict": True
            }
        }

        # Verify badrequest exception(400) is raised.
        ex = self.assertRaises(exceptions.BadRequest,
                               self.client.trigger_action,
                               'clusters', self.cluster_id, params)

        message = ex.resp_body['error']['message']
        self.assertEqual(
            "The specified max_size (2) is less than the current "
            "desired_capacity (3) of the cluster.", str(message))

    @decorators.idempotent_id('3b35938f-a73a-4096-bf13-af3709aed47f')
    def test_cluster_resize_max_size_under_current_min_size(self):
        # New max_size is less than current min_size of cluster
        # with strict set to False
        params = {
            "resize": {
                "max_size": 1,
                "strict": False
            }
        }

        # Verify badrequest exception(400) is raised.
        ex = self.assertRaises(exceptions.BadRequest,
                               self.client.trigger_action,
                               'clusters', self.cluster_id, params)

        message = ex.resp_body['error']['message']
        self.assertEqual(
            "The specified max_size (1) is less than the current "
            "min_size (2) of the cluster.", str(message))
        # New max_size is less than current min_size of cluster
        # with strict set to True
        params = {
            "resize": {
                "max_size": 1,
                "strict": True
            }
        }

        # Verify badrequest exception(400) is raised.
        ex = self.assertRaises(exceptions.BadRequest,
                               self.client.trigger_action,
                               'clusters', self.cluster_id, params)

        message = ex.resp_body['error']['message']
        self.assertEqual(
            "The specified max_size (1) is less than the current min_size "
            "(2) of the cluster.", str(message))

    @decorators.idempotent_id('1d7595a4-a7a8-42a4-9f90-7501a4bbb7e5')
    def test_cluster_resize_min_size_over_current_desired_capacity(self):
        # New min_size is greater than current desired_capacity of cluster
        params = {
            "resize": {
                "min_size": 4,
                "strict": True
            }
        }

        # Verify badrequest exception(400) is raised.
        ex = self.assertRaises(exceptions.BadRequest,
                               self.client.trigger_action,
                               'clusters', self.cluster_id, params)

        message = ex.resp_body['error']['message']
        self.assertEqual(
            "The specified min_size (4) is greater than the current "
            "desired_capacity (3) of the cluster.", str(message))

    @decorators.idempotent_id('606e5d3f-0857-4bfe-b52d-2ea1ad0cec16')
    def test_cluster_resize_min_size_over_current_max_size(self):
        # New min_size is greater than current max_size of cluster
        # with strict set to False
        params = {
            "resize": {
                "min_size": 6,
                "strict": False
            }
        }

        # Verify badrequest exception(400) is raised.
        ex = self.assertRaises(exceptions.BadRequest,
                               self.client.trigger_action,
                               'clusters', self.cluster_id, params)

        message = ex.resp_body['error']['message']
        self.assertEqual(
            "The specified min_size (6) is greater than the current "
            "max_size (5) of the cluster.", str(message))

        # New min_size is greater than current max_size of cluster
        # with strict set to True
        params = {
            "resize": {
                "min_size": 6,
                "strict": True
            }
        }

        # Verify badrequest exception(400) is raised.
        ex = self.assertRaises(exceptions.BadRequest,
                               self.client.trigger_action,
                               'clusters', self.cluster_id, params)

        message = ex.resp_body['error']['message']
        self.assertEqual(
            "The specified min_size (6) is greater than the current "
            "max_size (5) of the cluster.", str(message))
