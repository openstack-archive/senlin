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

import copy
from tempest.lib import decorators
from tempest.lib import exceptions
from tempest import test

from senlin.tests.tempest.api import base
from senlin.tests.tempest.api import utils
from senlin.tests.tempest.common import constants


class TestClusterUpdateNegativeNotFound(base.BaseSenlinTest):

    @test.attr(type=['negative'])
    @decorators.idempotent_id('f7a97fce-f495-44a8-b41a-7408139adacf')
    def test_cluster_update_cluster_not_found(self):
        self.assertRaises(exceptions.NotFound,
                          self.client.update_obj,
                          'clusters', 'f7a97fce-f495-44a8-b41a-7408139adacf',
                          {'cluster': {'name': 'new-name'}})


class TestClusterUpdateNegativeProfileNotFound(base.BaseSenlinTest):

    def setUp(self):
        super(TestClusterUpdateNegativeProfileNotFound, self).setUp()
        # Create a profile
        profile_id = utils.create_a_profile(self)
        self.addCleanup(utils.delete_a_profile, self, profile_id)
        self.profile_id = profile_id
        # Create a cluster
        self.cluster_id = utils.create_a_cluster(self, profile_id)
        self.addCleanup(utils.delete_a_cluster, self, self.cluster_id)

    @test.attr(type=['negative'])
    @decorators.idempotent_id('fb68921d-1fe8-4c14-be9a-51fa43d4f705')
    def test_cluster_update_profile_not_found(self):
        # Provided profile can not be found
        params = {
            'cluster': {
                'profile_id': 'fb68921d-1fe8-4c14-be9a-51fa43d4f705',
            }
        }
        # Verify badrequest exception(400) is raised.
        self.assertRaises(exceptions.BadRequest,
                          self.client.update_obj,
                          'clusters', self.cluster_id, params)


class TestClusterUpdateNegativeProfileMultichoices(base.BaseSenlinTest):
    def setUp(self):
        super(TestClusterUpdateNegativeProfileMultichoices, self).setUp()
        # Create a profile
        profile_id = utils.create_a_profile(self)
        self.addCleanup(utils.delete_a_profile, self, profile_id)
        self.profile_id = profile_id
        # Create a cluster
        self.cluster_id = utils.create_a_cluster(self, profile_id)
        self.addCleanup(utils.delete_a_cluster, self, self.cluster_id)
        # Create two new profiles of the same type with the same name
        new_spec = copy.deepcopy(constants.spec_nova_server)
        new_spec['properties']['flavor'] = 'new_flavor'
        new_profile_id1 = utils.create_a_profile(self, new_spec, name='p-nova')
        new_profile_id2 = utils.create_a_profile(self, new_spec, name='p-nova')
        self.addCleanup(utils.delete_a_profile, self, new_profile_id1)
        self.addCleanup(utils.delete_a_profile, self, new_profile_id2)

    @test.attr(type=['negative'])
    @decorators.idempotent_id('6a3eb86c-4b5c-4cfc-891c-7b0be17715f2')
    def test_cluster_update_profile_multichoices(self):
        # Multiple profiles are found for given name
        params = {
            'cluster': {
                'profile_id': 'p-nova',
            }
        }

        # Verify badrequest exception(400) is raised.
        self.assertRaises(exceptions.BadRequest,
                          self.client.update_obj,
                          'clusters', self.cluster_id, params)


class TestClusterUpdateNegativeProfileTypeUnmatch(base.BaseSenlinTest):
    def setUp(self):
        super(TestClusterUpdateNegativeProfileTypeUnmatch, self).setUp()
        # Create a profile
        profile_id = utils.create_a_profile(self)
        self.addCleanup(utils.delete_a_profile, self, profile_id)
        self.profile_id = profile_id
        # Create a cluster
        self.cluster_id = utils.create_a_cluster(self, profile_id)
        self.addCleanup(utils.delete_a_cluster, self, self.cluster_id)
        # Create a new profile of different type
        self.new_profile_id = utils.create_a_profile(
            self, spec=constants.spec_heat_stack)
        self.addCleanup(utils.delete_a_profile, self, self.new_profile_id)

    @test.attr(type=['negative'])
    @decorators.idempotent_id('c28e1bc0-fadb-4394-b2d0-67ad8b87ac04')
    def test_cluster_update_profile_type_unmatch(self):
        # New profile type is different from original cone
        params = {
            'cluster': {
                'profile_id': self.new_profile_id,
            }
        }

        # Verify badrequest exception(400) is raised.
        self.assertRaises(exceptions.BadRequest,
                          self.client.update_obj,
                          'clusters', self.cluster_id, params)
