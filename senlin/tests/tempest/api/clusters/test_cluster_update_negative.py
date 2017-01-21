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
from senlin.tests.tempest.common import constants
from senlin.tests.tempest.common import utils


class TestClusterUpdateNegativeInvalidParam(base.BaseSenlinAPITest):

    @test.attr(type=['negative'])
    @decorators.idempotent_id('7bddd411-b890-4a36-a523-3e49b87cb645')
    def test_cluster_update_cluster_invalid_param(self):
        params = {
            'cluster': {
                'bad': 'invalid'
            }
        }
        ex = self.assertRaises(exceptions.BadRequest,
                               self.client.update_obj, 'clusters',
                               'f7a97fce-f495-44a8-b41a-7408139adacf',
                               params)

        message = ex.resp_body['error']['message']
        self.assertEqual(
            "Additional properties are not allowed (u'bad' was "
            "unexpected)", str(message))

    @test.attr(type=['negative'])
    @decorators.idempotent_id('80cd0acd-772f-482f-8c6d-90843d986eb1')
    def test_cluster_update_cluster_empty_param(self):
        params = {}
        ex = self.assertRaises(exceptions.BadRequest,
                               self.client.update_obj, 'clusters',
                               '80cd0acd-772f-482f-8c6d-90843d986eb1',
                               params)

        message = ex.resp_body['error']['message']
        self.assertEqual(
            "Malformed request data, missing 'cluster' key in "
            "request body.", str(message))


class TestClusterUpdateNegativeNotFound(base.BaseSenlinAPITest):

    @test.attr(type=['negative'])
    @decorators.idempotent_id('f7a97fce-f495-44a8-b41a-7408139adacf')
    def test_cluster_update_cluster_not_found(self):
        ex = self.assertRaises(exceptions.NotFound,
                               self.client.update_obj, 'clusters',
                               'f7a97fce-f495-44a8-b41a-7408139adacf',
                               {'cluster': {'name': 'new-name'}})

        message = ex.resp_body['error']['message']
        self.assertEqual(
            "The cluster 'f7a97fce-f495-44a8-b41a-7408139adacf' could "
            "not be found.", str(message))


class TestClusterUpdateNegativeProfileNotFound(base.BaseSenlinAPITest):

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
        ex = self.assertRaises(exceptions.BadRequest,
                               self.client.update_obj,
                               'clusters', self.cluster_id, params)

        message = ex.resp_body['error']['message']
        self.assertEqual(
            "The specified profile 'fb68921d-1fe8-4c14-be9a-51fa43d4f705' "
            "could not be found.", str(message))


class TestClusterUpdateNegativeProfileMultichoices(base.BaseSenlinAPITest):
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
        ex = self.assertRaises(exceptions.BadRequest,
                               self.client.update_obj,
                               'clusters', self.cluster_id, params)

        message = ex.resp_body['error']['message']
        self.assertEqual(
            "Multiple results found matching the query criteria 'p-nova'. "
            "Please be more specific.", str(message))


class TestClusterUpdateNegativeProfileTypeUnmatch(base.BaseSenlinAPITest):
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
        ex = self.assertRaises(exceptions.BadRequest,
                               self.client.update_obj,
                               'clusters', self.cluster_id, params)

        message = ex.resp_body['error']['message']
        self.assertEqual(
            "Cannot update a cluster to a different profile type, "
            "operation aborted.", str(message))


class TestClusterUpdateNegativeNoPropertyUpdated(base.BaseSenlinAPITest):

    def setUp(self):
        super(TestClusterUpdateNegativeNoPropertyUpdated, self).setUp()
        # Create a profile
        profile_id = utils.create_a_profile(self)
        self.addCleanup(utils.delete_a_profile, self, profile_id)
        self.profile_id = profile_id
        # Create a cluster
        self.cluster_id = utils.create_a_cluster(self, profile_id)
        self.addCleanup(utils.delete_a_cluster, self, self.cluster_id)

    @test.attr(type=['negative'])
    @decorators.idempotent_id('0fbd8fd9-7789-47da-b806-d91631a28556')
    def test_cluster_update_no_property_updated(self):
        # No any property is updated
        params = {
            'cluster': {}
        }
        # Verify badrequest exception(400) is raised.
        ex = self.assertRaises(exceptions.BadRequest,
                               self.client.update_obj,
                               'clusters', self.cluster_id, params)

        message = ex.resp_body['error']['message']
        self.assertEqual("No property needs an update.", str(message))
