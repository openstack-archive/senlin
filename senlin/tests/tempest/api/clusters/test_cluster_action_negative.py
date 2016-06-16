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
from senlin.tests.tempest.api import utils


class TestClusterActionNegativeCommon(base.BaseSenlinTest):

    @decorators.idempotent_id('9c972d49-81bd-4448-9afc-b93053aa835d')
    def test_cluster_action_no_action_specified(self):
        # No action is specified
        params = {}

        # Verify badrequest exception(400) is raised.
        self.assertRaises(exceptions.BadRequest,
                          self.client.trigger_action,
                          'clusters', 'cluster_id', params)

    @decorators.idempotent_id('997d2e19-7914-4883-9b6a-86e907898d3b')
    def test_cluster_action_multiple_action_specified(self):
        # Multiple actions are specified
        params = {
            'resize': {},
            'check': {}
        }

        # Verify badrequest exception(400) is raised.
        self.assertRaises(exceptions.BadRequest,
                          self.client.trigger_action,
                          'clusters', 'cluster_id', params)

    @decorators.idempotent_id('43e142ac-9579-40d9-845a-b8190691b91a')
    def test_cluster_action_unrecognized_action(self):
        # Unrecoginized action is specified
        params = {
            'bogus': {}
        }

        # Verify badrequest exception(400) is raised.
        self.assertRaises(exceptions.BadRequest,
                          self.client.trigger_action,
                          'clusters', 'cluster_id', params)


class TestClusterResizeNegativeInvalidResizeParams(base.BaseSenlinTest):

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
        self.assertRaises(exceptions.BadRequest,
                          self.client.trigger_action,
                          'clusters', 'cluster_id', params)

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
        self.assertRaises(exceptions.BadRequest,
                          self.client.trigger_action,
                          'clusters', 'cluster_id', params)

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
        self.assertRaises(exceptions.BadRequest,
                          self.client.trigger_action,
                          'clusters', 'cluster_id', params)

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
        self.assertRaises(exceptions.BadRequest,
                          self.client.trigger_action,
                          'clusters', 'cluster_id', params)

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
        self.assertRaises(exceptions.BadRequest,
                          self.client.trigger_action,
                          'clusters', 'cluster_id', params)


class TestClusterResizeNegativeClusterNotFound(base.BaseSenlinTest):
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
        self.assertRaises(exceptions.NotFound,
                          self.client.trigger_action,
                          'clusters', '087ef694-55d2-4616-a58b-1073cacb2bcd',
                          params)


class TestClusterResizeNegativeSizeCheckFailed(base.BaseSenlinTest):

    def setUp(self):
        super(TestClusterResizeNegativeSizeCheckFailed, self).setUp()
        profile_id = utils.create_a_profile(self)
        self.addCleanup(utils.delete_a_profile, self, profile_id)
        self.cluster_id = utils.create_a_cluster(self, profile_id,
                                                 min_size=0, max_size=5,
                                                 desired_capacity=1)
        self.addCleanup(utils.delete_a_cluster, self, self.cluster_id)

    @decorators.idempotent_id('92e7d3c8-2d38-4766-86c3-41dc14bf89a1')
    def test_cluster_resize_cluster_size_check_failed(self):
        params = {
            "resize": {
                "adjustment_type": "CHANGE_IN_CAPACITY",
                "number": 5,
                "strict": True
            }
        }

        # Verify badrequest exception(400) is raised.
        self.assertRaises(exceptions.BadRequest,
                          self.client.trigger_action,
                          'clusters', self.cluster_id, params)
