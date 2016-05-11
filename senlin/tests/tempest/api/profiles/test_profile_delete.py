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

from senlin.tests.tempest.api import base
from senlin.tests.tempest.common import constants


class TestProfileDelete(base.BaseSenlinTest):

    @classmethod
    def resource_setup(cls):
        super(TestProfileDelete, cls).resource_setup()
        # Create profile
        cls.profile = cls.create_profile(constants.spec_nova_server)

    @decorators.idempotent_id('ea3c1b9e-5ed7-4d63-84ce-2032c3bc6d27')
    def test_delete_policy(self):
        # Verify resp of policy delete API
        res = self.client.delete_obj('profiles', self.profile['id'])
        self.assertEqual(204, res['status'])
        self.assertIsNone(res['body'])
