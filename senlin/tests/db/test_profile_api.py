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

from senlin.common import exception

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
        self.assertEqual(data['name'], profile.name)
        self.assertEqual(data['type'], profile.type)
        self.assertEqual(data['spec'], profile.spec)
        self.assertEqual(data['permission'], profile.permission)

    def test_profile_get(self):
        profile = shared.create_profile(self.ctx)
        retobj = db_api.profile_get(self.ctx, profile.id)
        self.assertEqual(profile.id, retobj.id)
        self.assertEqual(profile.spec, retobj.spec)

    def test_profile_get_not_found(self):
        profile = db_api.profile_get(self.ctx, 'BogusProfileID')
        self.assertIsNone(profile)

    def test_profile_get_show_deleted(self):
        profile_id = shared.create_profile(self.ctx).id

        # check created
        profile = db_api.profile_get(self.ctx, profile_id)
        self.assertIsNotNone(profile)

        # Now, delete it
        db_api.profile_delete(self.ctx, profile_id)

        # default equivalent to false
        profile = db_api.profile_get(self.ctx, profile_id)
        self.assertIsNone(profile)

        # explicit false
        profile = db_api.profile_get(self.ctx, profile_id, show_deleted=False)
        self.assertIsNone(profile)

        # explicit true
        profile = db_api.profile_get(self.ctx, profile_id, show_deleted=True)
        self.assertIsNotNone(profile)
        self.assertEqual(profile_id, profile.id)

    def test_profile_get_by_name(self):
        profile_name = 'my_best_profile'

        # before creation
        profile = db_api.profile_get_by_name(self.ctx, profile_name)
        self.assertIsNone(profile)

        profile = shared.create_profile(self.ctx, name=profile_name)

        # after creation
        retobj = db_api.profile_get_by_name(self.ctx, profile_name)
        self.assertIsNotNone(retobj)
        self.assertEqual(profile_name, retobj.name)

        # bad name
        retobj = db_api.profile_get_by_name(self.ctx, 'non-exist')
        self.assertIsNone(retobj)

    def test_profile_get_by_name_show_deleted(self):
        profile_name = 'my_best_profile'

        profile_id = shared.create_profile(self.ctx, name=profile_name).id

        db_api.profile_delete(self.ctx, profile_id)

        # default case
        profile = db_api.profile_get_by_name(self.ctx, profile_name)
        self.assertIsNone(profile)

        # explicit false
        profile = db_api.profile_get_by_name(self.ctx, profile_name,
                                             show_deleted=False)
        self.assertIsNone(profile)

        # explicit true
        profile = db_api.profile_get_by_name(self.ctx, profile_name,
                                             show_deleted=True)
        self.assertIsNotNone(profile)
        self.assertEqual(profile_id, profile.id)

    def test_profile_get_by_short_id(self):
        profile_ids = ['same-part-unique-part',
                       'same-part-part-unique']

        for pid in profile_ids:
            shared.create_profile(self.ctx, id=pid)

            # verify creation with set ID
            profile = db_api.profile_get(self.ctx, pid)
            self.assertIsNotNone(profile)
            self.assertEqual(pid, profile.id)

        # too short -> multiple choices
        for x in range(len('same-part-')):
            self.assertRaises(exception.MultipleChoices,
                              db_api.profile_get_by_short_id,
                              self.ctx, profile_ids[0][:x])

        # ids are unique
        profile = db_api.profile_get_by_short_id(self.ctx, profile_ids[0][:11])
        self.assertEqual(profile_ids[0], profile.id)
        profile = db_api.profile_get_by_short_id(self.ctx, profile_ids[1][:11])
        self.assertEqual(profile_ids[1], profile.id)

        # bad ids
        res = db_api.profile_get_by_short_id(self.ctx, 'non-existent')
        self.assertIsNone(res)

    def test_profile_get_all(self):
        ids = ['profile1', 'profile2']

        for pid in ids:
            shared.create_profile(self.ctx, id=pid)

        profiles = db_api.profile_get_all(self.ctx)
        self.assertEqual(2, len(profiles))
        profile_ids = [p.id for p in profiles]
        for pid in ids:
            self.assertIn(pid, profile_ids)

        # test show_deleted here
        db_api.profile_delete(self.ctx, profiles[1].id)

        # after delete one of them
        profiles = db_api.profile_get_all(self.ctx)
        self.assertEqual(1, len(profiles))

        profiles = db_api.profile_get_all(self.ctx, show_deleted=False)
        self.assertEqual(1, len(profiles))

        profiles = db_api.profile_get_all(self.ctx, show_deleted=True)
        self.assertEqual(2, len(profiles))

        # after delete both profiles
        db_api.profile_delete(self.ctx, profiles[0].id)

        profiles = db_api.profile_get_all(self.ctx)
        self.assertEqual(0, len(profiles))
        profiles = db_api.profile_get_all(self.ctx, show_deleted=True)
        self.assertEqual(2, len(profiles))

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

    def test_profile_delete(self):
        profile = shared.create_profile(self.ctx)
        self.assertIsNotNone(profile)
        profile_id = profile.id
        db_api.profile_delete(self.ctx, profile_id)

        profile = db_api.profile_get(self.ctx, profile_id)
        self.assertIsNone(profile)
