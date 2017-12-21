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

from senlin.common import consts
from senlin.common import exception
from senlin.db.sqlalchemy import api as db_api
from senlin.tests.unit.common import base
from senlin.tests.unit.common import utils


class DBAPIReceiverTest(base.SenlinTestCase):
    def setUp(self):
        super(DBAPIReceiverTest, self).setUp()
        self.ctx = utils.dummy_context()
        self.type = 'webhook'
        self.cluster_id = 'FAKE_ID'
        self.action = 'test_action'

    def _create_receiver(self, ctx, type=None, cluster_id=None, action=None,
                         **kwargs):
        values = {
            'name': 'test_receiver',
            'type': type or self.type,
            'user': ctx.user_id,
            'project': ctx.project_id,
            'domain': ctx.domain_id,
            'created_at': None,
            'updated_at': None,
            'cluster_id': cluster_id or self.cluster_id,
            'action': action or self.action,
            'actor': {'username': 'john', 'password': 'secrete1'},
            'params': {'key1': 'value1'},
            'channel': {'alarm_url': 'http://url1'}
        }
        values.update(kwargs)
        return db_api.receiver_create(ctx, values)

    def test_receiver_create_and_get(self):
        res = self._create_receiver(self.ctx)
        r = db_api.receiver_get(self.ctx, res.id)
        self.assertIsNotNone(r)
        self.assertEqual(self.cluster_id, r.cluster_id)
        self.assertEqual('test_receiver', r.name)
        self.assertEqual(self.type, r.type)
        self.assertEqual(self.ctx.user_id, r.user)
        self.assertEqual(self.ctx.project_id, r.project)
        self.assertEqual(self.ctx.domain_id, r.domain)
        self.assertIsNone(r.created_at)
        self.assertIsNone(r.updated_at)
        self.assertEqual(self.action, r.action)
        self.assertEqual({'username': 'john', 'password': 'secrete1'}, r.actor)
        self.assertEqual({'key1': 'value1'}, r.params)
        self.assertEqual({'alarm_url': 'http://url1'}, r.channel)

    def test_receiver_get_diff_project(self):
        new_ctx = utils.dummy_context(project='a-different-project')
        r = self._create_receiver(self.ctx)

        res = db_api.receiver_get(new_ctx, r.id)
        self.assertIsNone(res)

        res = db_api.receiver_get(new_ctx, r.id, project_safe=False)
        self.assertIsNotNone(res)
        self.assertEqual(r.id, res.id)

        res = db_api.receiver_get(self.ctx, r.id)
        self.assertEqual(r.id, res.id)

    def test_receiver_get_admin_context(self):
        admin_ctx = utils.dummy_context(project='a-different-project',
                                        is_admin=True)
        r = self._create_receiver(self.ctx)

        res = db_api.receiver_get(admin_ctx, r.id, project_safe=True)
        self.assertIsNone(res)
        res = db_api.receiver_get(admin_ctx, r.id, project_safe=False)
        self.assertIsNotNone(res)

    def test_receiver_get_by_short_id(self):
        receiver_id1 = 'same-part-unique-part'
        receiver_id2 = 'same-part-part-unique'
        self._create_receiver(self.ctx, id=receiver_id1, name='receiver-1')
        self._create_receiver(self.ctx, id=receiver_id2, name='receiver-2')

        for x in range(len('same-part-')):
            self.assertRaises(exception.MultipleChoices,
                              db_api.receiver_get_by_short_id,
                              self.ctx, receiver_id1[:x])

        res = db_api.receiver_get_by_short_id(self.ctx, receiver_id1[:11])
        self.assertEqual(receiver_id1, res.id)
        res = db_api.receiver_get_by_short_id(self.ctx, receiver_id2[:11])
        self.assertEqual(receiver_id2, res.id)
        res = db_api.receiver_get_by_short_id(self.ctx, 'non-existent')
        self.assertIsNone(res)

    def test_receiver_get_by_short_id_diff_project(self):
        rid = 'same-part-unique-part'
        self._create_receiver(self.ctx, id=rid, name='receiver-1')

        new_ctx = utils.dummy_context(project='a-different-project')
        res = db_api.receiver_get_by_short_id(new_ctx, rid[:11])
        self.assertIsNone(res)

        res = db_api.receiver_get_by_short_id(new_ctx, rid[:11],
                                              project_safe=False)
        self.assertIsNotNone(res)
        self.assertEqual(rid, res.id)

    def test_receiver_get_by_name(self):
        rname = 'fake_receiver_name'
        self._create_receiver(self.ctx, name=rname)
        receiver = db_api.receiver_get_by_name(self.ctx, rname)
        self.assertIsNotNone(receiver)
        self.assertEqual(rname, receiver.name)

        # bad name
        res = db_api.receiver_get_by_name(self.ctx, 'BogusName')
        self.assertIsNone(res)

        # duplicated name
        self._create_receiver(self.ctx, name=rname)
        self.assertRaises(exception.MultipleChoices,
                          db_api.receiver_get_by_name,
                          self.ctx, rname)

    def test_receiver_get_by_name_diff_project(self):
        rname = 'fake_receiver_name'
        self._create_receiver(self.ctx, name=rname)

        new_ctx = utils.dummy_context(project='a-different-project')
        res = db_api.receiver_get_by_name(new_ctx, rname)
        self.assertIsNone(res)

        res = db_api.receiver_get_by_name(new_ctx, rname, project_safe=False)
        self.assertIsNotNone(res)
        self.assertEqual(rname, res.name)

    def test_receiver_get_all(self):
        values = [{'name': 'receiver1'},
                  {'name': 'receiver2'},
                  {'name': 'receiver3'}]
        [self._create_receiver(self.ctx, **v) for v in values]

        receivers = db_api.receiver_get_all(self.ctx)
        self.assertEqual(3, len(receivers))

        names = [receiver.name for receiver in receivers]
        for val in values:
            self.assertIn(val['name'], names)

    def test_receiver_get_all_with_limit_marker(self):
        receiver_ids = ['receiver1', 'receiver2', 'receiver3']
        for v in receiver_ids:
            self._create_receiver(self.ctx, id=v,
                                  created_at=tu.utcnow(True))

        receivers = db_api.receiver_get_all(self.ctx, limit=1)
        self.assertEqual(1, len(receivers))

        receivers = db_api.receiver_get_all(self.ctx, limit=2)
        self.assertEqual(2, len(receivers))

        receivers = db_api.receiver_get_all(self.ctx, limit=5)
        self.assertEqual(3, len(receivers))

        receivers = db_api.receiver_get_all(self.ctx, marker='receiver1')
        self.assertEqual(2, len(receivers))

        receivers = db_api.receiver_get_all(self.ctx, marker='receiver2')
        self.assertEqual(1, len(receivers))

        receivers = db_api.receiver_get_all(self.ctx, marker='receiver3')
        self.assertEqual(0, len(receivers))

        receivers = db_api.receiver_get_all(self.ctx, limit=1,
                                            marker='receiver1')
        self.assertEqual(1, len(receivers))

    @mock.patch.object(sa_utils, 'paginate_query')
    def test_receiver_get_all_used_sort_keys(self, mock_paginate):
        receiver_ids = ['receiver1', 'receiver2', 'receiver3']
        for v in receiver_ids:
            self._create_receiver(self.ctx, id=v)

        sort_keys = consts.RECEIVER_SORT_KEYS

        db_api.receiver_get_all(self.ctx, sort=','.join(sort_keys))
        args = mock_paginate.call_args[0]
        sort_keys.append('id')
        self.assertEqual(set(sort_keys), set(args[3]))

    def test_receiver_get_all_sorting(self):
        values = [{'id': '001', 'name': 'receiver1'},
                  {'id': '002', 'name': 'receiver3'},
                  {'id': '003', 'name': 'receiver2'}]
        obj_ids = {'receiver1': 'id3',
                   'receiver2': 'id2',
                   'receiver3': 'id1'}
        for v in values:
            self._create_receiver(self.ctx, cluster_id=obj_ids[v['name']], **v)

        receivers = db_api.receiver_get_all(self.ctx, sort='name,cluster_id')
        self.assertEqual(3, len(receivers))
        # Sorted by name (ascending)
        self.assertEqual('001', receivers[0].id)
        self.assertEqual('003', receivers[1].id)
        self.assertEqual('002', receivers[2].id)

        receivers = db_api.receiver_get_all(self.ctx, sort='cluster_id,name')
        self.assertEqual(3, len(receivers))
        # Sorted by obj_id (ascending)
        self.assertEqual('002', receivers[0].id)
        self.assertEqual('003', receivers[1].id)
        self.assertEqual('001', receivers[2].id)

        receivers = db_api.receiver_get_all(self.ctx,
                                            sort='cluster_id:desc,name:desc')
        self.assertEqual(3, len(receivers))
        # Sorted by obj_id (descending)
        self.assertEqual('001', receivers[0].id)
        self.assertEqual('003', receivers[1].id)
        self.assertEqual('002', receivers[2].id)

    def test_receiver_get_all_sorting_default(self):
        values = [{'id': '001', 'name': 'receiver1'},
                  {'id': '002', 'name': 'receiver2'},
                  {'id': '003', 'name': 'receiver3'}]
        obj_ids = {'receiver1': 'id3',
                   'receiver2': 'id2',
                   'receiver3': 'id1'}
        for v in values:
            self._create_receiver(self.ctx, cluster_id=obj_ids[v['name']], **v)

        receivers = db_api.receiver_get_all(self.ctx)
        self.assertEqual(3, len(receivers))
        self.assertEqual(values[0]['id'], receivers[0].id)
        self.assertEqual(values[1]['id'], receivers[1].id)
        self.assertEqual(values[2]['id'], receivers[2].id)

    def test_receiver_get_all_with_filters(self):
        self._create_receiver(self.ctx, name='receiver1')
        self._create_receiver(self.ctx, name='receiver2')

        filters = {'name': ['receiver1', 'receiverx']}
        results = db_api.receiver_get_all(self.ctx, filters=filters)
        self.assertEqual(1, len(results))
        self.assertEqual('receiver1', results[0]['name'])

        filters = {'name': 'receiver1'}
        results = db_api.receiver_get_all(self.ctx, filters=filters)
        self.assertEqual(1, len(results))
        self.assertEqual('receiver1', results[0]['name'])

    def test_receiver_get_all_with_empty_filters(self):
        self._create_receiver(self.ctx, name='receiver1')
        self._create_receiver(self.ctx, name='receiver2')

        filters = None
        results = db_api.receiver_get_all(self.ctx, filters=filters)
        self.assertEqual(2, len(results))

    def test_receiver_get_all_with_project_safe(self):
        self._create_receiver(self.ctx, name='receiver1')
        self._create_receiver(self.ctx, name='receiver2')

        self.ctx.project_id = 'a-different-project'
        results = db_api.receiver_get_all(self.ctx, project_safe=False)
        self.assertEqual(2, len(results))

        self.ctx.project_id = 'a-different-project'
        results = db_api.receiver_get_all(self.ctx)
        self.assertEqual(0, len(results))

        results = db_api.receiver_get_all(self.ctx, project_safe=True)
        self.assertEqual(0, len(results))

    def test_receiver_get_all_with_admin_context(self):
        self._create_receiver(self.ctx, name='receiver1')
        self._create_receiver(self.ctx, name='receiver2')

        admin_ctx = utils.dummy_context(project='a-different-project',
                                        is_admin=True)
        results = db_api.receiver_get_all(admin_ctx, project_safe=True)
        self.assertEqual(0, len(results))
        results = db_api.receiver_get_all(admin_ctx, project_safe=False)
        self.assertEqual(2, len(results))

    def test_receiver_delete(self):
        res = self._create_receiver(self.ctx)
        receiver_id = res.id
        receiver = db_api.receiver_get(self.ctx, receiver_id)
        self.assertIsNotNone(receiver)

        db_api.receiver_delete(self.ctx, receiver_id)
        res = db_api.receiver_get(self.ctx, receiver_id)
        self.assertIsNone(res)

    def test_receiver_delete_not_found(self):
        receiver_id = 'BogusWebhookID'
        res = db_api.receiver_delete(self.ctx, receiver_id)
        self.assertIsNone(res)

        res = db_api.receiver_get(self.ctx, receiver_id)
        self.assertIsNone(res)

    def test_receiver_update(self):
        new_values = {
            'name': 'test_receiver2',
            'params': {'key2': 'value2'},
        }

        old_receiver = self._create_receiver(self.ctx)
        new_receiver = db_api.receiver_update(self.ctx, old_receiver.id,
                                              new_values)

        self.assertEqual(old_receiver.id, new_receiver.id)
        self.assertEqual(new_values['name'], new_receiver.name)
        self.assertEqual('test_receiver2', new_receiver.name)
        self.assertEqual('value2', new_receiver.params['key2'])

    def test_receiver_update_not_found(self):
        new_values = {
            'name': 'test_receiver2',
            'params': {'key2': 'value2'},
        }
        self.assertRaises(exception.ResourceNotFound,
                          db_api.receiver_update,
                          self.ctx, 'BogusID', new_values)
