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
from senlin.engine import parser
from senlin.tests.common import base
from senlin.tests.common import utils
from senlin.tests.db import shared


class DBAPIProfileTest(base.SenlinTestCase):
    def setUp(self):
        super(DBAPIProfileTest, self).setUp()
        self.ctx = utils.dummy_context()

    def test_profile_create(self):
        data = parser.parse_profile(shared.sample_profile)
        profile = shared.create_profile(self.ctx)
        self.assertIsNotNone(profile.id)
        self.assertEqual(data['spec'], profile.spec)
        self.assertEqual('xxxyyy', profile.spec['permission'])

    def test_profile_get(self):
        data = parser.parse_profile(shared.sample_profile)
        profile = shared.create_profile(self.ctx,
                                        profile=shared.sample_profile)
        retobj = db_api.profile_get(self.ctx, profile.id)
        self.assertEqual(profile.id, retobj.id)
        self.assertEqual(profile.spec, retobj.spec)

    def test_profile_get_all(self):
        values = [
            {'name': 'test_profile1'},
            {'name': 'test_proflie2'},
        ]
        profiles = [shared.create_profile(
                        self.ctx, profile=shared.sample_profile, **v)
                        for v in values]

        retobjs = db_api.profile_get_all(self.ctx)
        names = [obj.name for obj in retobjs]
        self.assertEqual(2, len(retobjs))
        for val in values:
            self.assertIn(val['name'], names)

    def test_profile_update(self):
        another_profile = '''
          name: test_profile_name_2
          type: my_test_profile_type
          spec:
            template:
              heat_template_version: "2013-05-23"
              resources:
                myrandom: OS::Heat::RandomString
              files:
                myfile: new contents
            permission: yyyyxxxx 
        '''

        new_data = parser.parse_profile(another_profile)
        old_profile = shared.create_profile(self.ctx)
        new_profile = db_api.profile_update(self.ctx, old_profile.id, new_data)

        self.assertEqual(old_profile.id, new_profile.id)
        self.assertEqual(new_data['name'], new_profile.name)
        self.assertEqual('test_profile_name_2', new_profile.name)
