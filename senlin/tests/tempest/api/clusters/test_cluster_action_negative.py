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


class TestClusterActionNegativeCommon(base.BaseSenlinAPITest):

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
