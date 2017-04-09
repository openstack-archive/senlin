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

import mock
from oslo_db.sqlalchemy import utils as sa_utils
from oslo_utils import timeutils as tu
import six

from senlin.common import consts
from senlin.common import exception
from senlin.db.sqlalchemy import api as db_api
from senlin.engine import parser
from senlin.tests.unit.common import base
from senlin.tests.unit.common import utils
from senlin.tests.unit.db import shared


class DBAPIProfileTest(base.SenlinTestCase):
    def setUp(self):
        super(DBAPIProfileTest, self).setUp()
        self.ctx = utils.dummy_context()

    def test_profile_create(self):
        data = parser.simple_parse(shared.sample_profile)
        profile = shared.create_profile(self.ctx)
        self.assertIsNotNone(profile.id)
        self.assertEqual(data['name'], profile.name)
        self.assertEqual(data['type'], profile.type)
        self.assertEqual(data['spec'], profile.spec)

    def test_profile_get(self):
        profile = shared.create_profile(self.ctx)
        retobj = db_api.profile_get(self.ctx, profile.id)
        self.assertEqual(profile.id, retobj.id)
        self.assertEqual(profile.spec, retobj.spec)

    def test_profile_get_diff_project(self):
        profile = shared.create_profile(self.ctx)
        new_ctx = utils.dummy_context(project='a-different-project')
        res = db_api.profile_get(new_ctx, profile.id)
        self.assertIsNone(res)

        res = db_api.profile_get(new_ctx, profile.id, project_safe=False)
        self.assertIsNotNone(res)
        self.assertEqual(profile.id, res.id)

    def test_profile_get_admin_context(self):
        profile = shared.create_profile(self.ctx)
        admin_ctx = utils.dummy_context(project='a-different-project',
                                        is_admin=True)
        res = db_api.profile_get(admin_ctx, profile.id, project_safe=True)
        self.assertIsNone(res)
        res = db_api.profile_get(admin_ctx, profile.id, project_safe=False)
        self.assertIsNotNone(res)

    def test_profile_get_not_found(self):
        profile = db_api.profile_get(self.ctx, 'BogusProfileID')
        self.assertIsNone(profile)

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

        # duplicated name
        shared.create_profile(self.ctx, name=profile_name)
        self.assertRaises(exception.MultipleChoices,
                          db_api.profile_get_by_name,
                          self.ctx, profile_name)

    def test_profile_get_by_name_diff_project(self):
        profile_name = 'my_best_profile'
        shared.create_profile(self.ctx, name=profile_name)

        new_ctx = utils.dummy_context(project='a-different-project')
        res = db_api.profile_get_by_name(new_ctx, profile_name)
        self.assertIsNone(res)

        res = db_api.profile_get_by_name(new_ctx, profile_name,
                                         project_safe=False)
        self.assertIsNotNone(res)
        self.assertEqual(profile_name, res.name)

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

    def test_profile_get_by_short_id_diff_project(self):
        profile_id = 'same-part-unique-part'
        shared.create_profile(self.ctx, id=profile_id)

        new_ctx = utils.dummy_context(project='a-different-project')
        res = db_api.profile_get_by_short_id(new_ctx, profile_id)
        self.assertIsNone(res)

        res = db_api.profile_get_by_short_id(new_ctx, profile_id,
                                             project_safe=False)
        self.assertIsNotNone(res)
        self.assertEqual(profile_id, res.id)

    def test_profile_get_all(self):
        ids = ['profile1', 'profile2']

        for pid in ids:
            shared.create_profile(self.ctx, id=pid)

        profiles = db_api.profile_get_all(self.ctx)
        self.assertEqual(2, len(profiles))
        profile_ids = [p.id for p in profiles]
        for pid in ids:
            self.assertIn(pid, profile_ids)

        db_api.profile_delete(self.ctx, profiles[1].id)

        # after delete one of them
        profiles = db_api.profile_get_all(self.ctx)
        self.assertEqual(1, len(profiles))

        # after delete both profiles
        db_api.profile_delete(self.ctx, profiles[0].id)

        profiles = db_api.profile_get_all(self.ctx)
        self.assertEqual(0, len(profiles))

    def test_profile_get_all_diff_project(self):
        ids = ['profile1', 'profile2']
        for pid in ids:
            shared.create_profile(self.ctx, id=pid)

        new_ctx = utils.dummy_context(project='a-different-project')
        profiles = db_api.profile_get_all(new_ctx)
        self.assertEqual(0, len(profiles))
        profiles = db_api.profile_get_all(new_ctx, project_safe=False)
        self.assertEqual(2, len(profiles))

    def test_profile_get_all_admin_context(self):
        ids = ['profile1', 'profile2']
        for pid in ids:
            shared.create_profile(self.ctx, id=pid)

        admin_ctx = utils.dummy_context(project='a-different-project',
                                        is_admin=True)
        profiles = db_api.profile_get_all(admin_ctx, project_safe=True)
        self.assertEqual(0, len(profiles))
        profiles = db_api.profile_get_all(admin_ctx, project_safe=False)
        self.assertEqual(2, len(profiles))

    def test_profile_get_all_with_limit_marker(self):
        ids = ['profile1', 'profile2', 'profile3']
        for pid in ids:
            timestamp = tu.utcnow(True)
            shared.create_profile(self.ctx, id=pid, created_at=timestamp)

        # different limit settings
        profiles = db_api.profile_get_all(self.ctx, limit=1)
        self.assertEqual(1, len(profiles))

        profiles = db_api.profile_get_all(self.ctx, limit=2)
        self.assertEqual(2, len(profiles))

        # a large limit
        profiles = db_api.profile_get_all(self.ctx, limit=5)
        self.assertEqual(3, len(profiles))

        # use marker here
        profiles = db_api.profile_get_all(self.ctx, marker='profile1')
        self.assertEqual(2, len(profiles))

        profiles = db_api.profile_get_all(self.ctx, marker='profile2')
        self.assertEqual(1, len(profiles))

        profiles = db_api.profile_get_all(self.ctx, marker='profile3')
        self.assertEqual(0, len(profiles))

        profiles = db_api.profile_get_all(self.ctx, limit=1, marker='profile1')
        self.assertEqual(1, len(profiles))

    @mock.patch.object(sa_utils, 'paginate_query')
    def test_profile_get_all_used_sort_keys(self, mock_paginate):
        ids = ['profile1', 'profile2', 'profile3']
        for pid in ids:
            shared.create_profile(self.ctx, id=pid)

        sort_keys = consts.PROFILE_SORT_KEYS
        db_api.profile_get_all(self.ctx, sort=','.join(sort_keys))

        args = mock_paginate.call_args[0]
        sort_keys.append('id')
        self.assertEqual(set(sort_keys), set(args[3]))

    def test_profile_get_all_sorting(self):
        values = [{'id': '001', 'name': 'profile1', 'type': 'C'},
                  {'id': '002', 'name': 'profile3', 'type': 'B'},
                  {'id': '003', 'name': 'profile2', 'type': 'A'}]

        for v in values:
            shared.create_profile(self.ctx, **v)

        # Sorted by name,type
        profiles = db_api.profile_get_all(self.ctx, sort='name,type')
        self.assertEqual(3, len(profiles))
        self.assertEqual('001', profiles[0].id)
        self.assertEqual('003', profiles[1].id)
        self.assertEqual('002', profiles[2].id)

        # Sorted by type,name (ascending)
        profiles = db_api.profile_get_all(self.ctx, sort='type,name')
        self.assertEqual(3, len(profiles))
        self.assertEqual('003', profiles[0].id)
        self.assertEqual('002', profiles[1].id)
        self.assertEqual('001', profiles[2].id)

        # Sorted by type,name (descending)
        profiles = db_api.profile_get_all(self.ctx, sort='type:desc,name:desc')
        self.assertEqual(3, len(profiles))
        self.assertEqual('001', profiles[0].id)
        self.assertEqual('002', profiles[1].id)
        self.assertEqual('003', profiles[2].id)

    def test_profile_get_all_default_sorting(self):
        profiles = []
        for x in range(3):
            profile = shared.create_profile(self.ctx,
                                            created_at=tu.utcnow(True))
            profiles.append(profile)

        results = db_api.profile_get_all(self.ctx)
        self.assertEqual(3, len(results))
        self.assertEqual(profiles[0].id, results[0].id)
        self.assertEqual(profiles[1].id, results[1].id)
        self.assertEqual(profiles[2].id, results[2].id)

    def test_profile_get_all_with_filters(self):
        for name in ['profile1', 'profile2']:
            shared.create_profile(self.ctx, name=name)

        filters = {'name': ['profile1', 'profilex']}
        results = db_api.profile_get_all(self.ctx, filters=filters)
        self.assertEqual(1, len(results))
        self.assertEqual('profile1', results[0]['name'])

        filters = {'name': 'profile1'}
        results = db_api.profile_get_all(self.ctx, filters=filters)
        self.assertEqual(1, len(results))
        self.assertEqual('profile1', results[0]['name'])

    def test_profile_get_all_with_empty_filters(self):
        for name in ['profile1', 'profile2']:
            shared.create_profile(self.ctx, name=name)

        filters = None
        results = db_api.profile_get_all(self.ctx, filters=filters)
        self.assertEqual(2, len(results))

    def test_profile_update(self):
        new_fields = {
            'name': 'test_profile_name_2',
            'type': 'my_test_profile_type',
            'spec': {
                'template': {
                    'heat_template_version': '2013-05-23',
                    'resources': {
                        'myrandom': 'OS::Heat::RandomString',
                    },
                },
                'files': {
                    'myfile': 'new contents',
                },
            },
        }

        old_profile = shared.create_profile(self.ctx)
        new_profile = db_api.profile_update(self.ctx, old_profile.id,
                                            new_fields)

        self.assertEqual(old_profile.id, new_profile.id)
        self.assertEqual(new_fields['name'], new_profile.name)
        self.assertEqual('test_profile_name_2', new_profile.name)

    def test_profile_update_not_found(self):
        self.assertRaises(exception.ResourceNotFound,
                          db_api.profile_update,
                          self.ctx, 'BogusID', {})

    def test_profile_delete(self):
        profile = shared.create_profile(self.ctx)
        self.assertIsNotNone(profile)
        profile_id = profile.id
        db_api.profile_delete(self.ctx, profile_id)

        profile = db_api.profile_get(self.ctx, profile_id)
        self.assertIsNone(profile)

        # not found in delete is okay
        res = db_api.profile_delete(self.ctx, profile_id)
        self.assertIsNone(res)

    def test_profile_delete_profile_used_by_cluster(self):
        profile = shared.create_profile(self.ctx)
        cluster = shared.create_cluster(self.ctx, profile)

        profile_id = profile.id
        ex = self.assertRaises(exception.EResourceBusy,
                               db_api.profile_delete, self.ctx, profile_id)
        self.assertEqual("The profile '%s' is busy now." % profile_id,
                         six.text_type(ex))

        db_api.cluster_delete(self.ctx, cluster.id)
        db_api.profile_delete(self.ctx, profile_id)

    def test_profile_delete_profile_used_by_node(self):
        profile = shared.create_profile(self.ctx)
        node = shared.create_node(self.ctx, None, profile)

        profile_id = profile.id
        ex = self.assertRaises(exception.EResourceBusy,
                               db_api.profile_delete, self.ctx, profile_id)
        self.assertEqual("The profile '%s' is busy now." % profile_id,
                         six.text_type(ex))

        db_api.node_delete(self.ctx, node.id)
        db_api.profile_delete(self.ctx, profile_id)
