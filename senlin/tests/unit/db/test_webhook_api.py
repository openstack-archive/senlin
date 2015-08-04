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

from oslo_utils import timeutils as tu

from senlin.common import exception
from senlin.db.sqlalchemy import api as db_api
from senlin.tests.unit.common import base
from senlin.tests.unit.common import utils
from senlin.tests.unit.db import shared

UUID1 = shared.UUID1
UUID2 = shared.UUID2
UUID3 = shared.UUID3


class DBAPIWebhookTest(base.SenlinTestCase):
    def setUp(self):
        super(DBAPIWebhookTest, self).setUp()
        self.ctx = utils.dummy_context()
        self.obj_id = UUID1
        self.obj_type = 'test_obj_type'
        self.action = 'test_action'

    def test_webhook_create(self):
        res = shared.create_webhook(self.ctx, self.obj_id,
                                    self.obj_type, self.action)
        webhook = db_api.webhook_get(self.ctx, res.id)
        self.assertIsNotNone(webhook)
        self.assertEqual(UUID1, webhook.obj_id)
        self.assertEqual('test_webhook_name', webhook.name)
        self.assertEqual(self.ctx.user, webhook.user)
        self.assertEqual(self.ctx.domain, webhook.domain)
        self.assertEqual(self.ctx.project, webhook.project)
        self.assertIsNone(webhook.created_time)
        self.assertIsNone(webhook.deleted_time)
        self.assertEqual('test_obj_type', webhook.obj_type)
        self.assertEqual('test_action', webhook.action)

    def test_webhook_get(self):
        res = shared.create_webhook(self.ctx, self.obj_id,
                                    self.obj_type, self.action)
        webhook = db_api.webhook_get(self.ctx, res.id)
        self.assertIsNotNone(webhook)

    def test_webhook_get_show_deleted(self):
        res = shared.create_webhook(self.ctx, self.obj_id,
                                    self.obj_type, self.action)
        webhook_id = res.id
        webhook = db_api.webhook_get(self.ctx, webhook_id)
        self.assertIsNotNone(webhook)

        db_api.webhook_delete(self.ctx, webhook_id)

        webhook = db_api.webhook_get(self.ctx, webhook_id)
        self.assertIsNone(webhook)

        webhook = db_api.webhook_get(self.ctx, webhook_id, show_deleted=False)
        self.assertIsNone(webhook)

        webhook = db_api.webhook_get(self.ctx, webhook_id, show_deleted=True)
        self.assertEqual(webhook_id, webhook.id)

    def test_webhook_get_by_short_id(self):
        webhook_id1 = 'same-part-unique-part'
        webhook_id2 = 'same-part-part-unique'
        shared.create_webhook(self.ctx, self.obj_id, self.obj_type,
                              self.action, id=webhook_id1, name='webhook-1')
        shared.create_webhook(self.ctx, self.obj_id, self.obj_type,
                              self.action, id=webhook_id2, name='webhook-2')

        for x in range(len('same-part-')):
            self.assertRaises(exception.MultipleChoices,
                              db_api.webhook_get_by_short_id,
                              self.ctx, webhook_id1[:x])

        res = db_api.webhook_get_by_short_id(self.ctx, webhook_id1[:11])
        self.assertEqual(webhook_id1, res.id)
        res = db_api.webhook_get_by_short_id(self.ctx, webhook_id2[:11])
        self.assertEqual(webhook_id2, res.id)
        res = db_api.webhook_get_by_short_id(self.ctx, 'non-existent')
        self.assertIsNone(res)

    def test_webhook_get_by_short_id_show_deleted(self):
        webhook_id = 'this-is-a-unique-id'
        shared.create_webhook(self.ctx, self.obj_id, self.obj_type,
                              self.action, id=webhook_id)

        res = db_api.webhook_get_by_short_id(self.ctx, webhook_id[:5])
        self.assertEqual(webhook_id, res.id)
        res = db_api.webhook_get_by_short_id(self.ctx, webhook_id[:7])
        self.assertEqual(webhook_id, res.id)

        db_api.webhook_delete(self.ctx, webhook_id)

        res = db_api.webhook_get_by_short_id(self.ctx, webhook_id[:5])
        self.assertIsNone(res)
        res = db_api.webhook_get_by_short_id(self.ctx, webhook_id[:5],
                                             show_deleted=False)
        self.assertIsNone(res)
        res = db_api.webhook_get_by_short_id(self.ctx, webhook_id[:5],
                                             show_deleted=True)
        self.assertEqual(webhook_id, res.id)

    def test_webhook_get_by_name(self):
        webhook_name = 'fake_webhook_name'
        shared.create_webhook(self.ctx, self.obj_id, self.obj_type,
                              self.action, name=webhook_name)
        webhook = db_api.webhook_get_by_name(self.ctx, webhook_name)
        self.assertIsNotNone(webhook)
        self.assertEqual(webhook_name, webhook.name)

        res = db_api.webhook_get_by_name(self.ctx, 'BogusName')
        self.assertIsNone(res)

    def test_webhook_get_by_name_show_deleted(self):
        webhook_name = 'fake_webhook_name'
        shared.create_webhook(self.ctx, self.obj_id, self.obj_type,
                              self.action, name=webhook_name)
        webhook = db_api.webhook_get_by_name(self.ctx, webhook_name)
        self.assertIsNotNone(webhook)
        self.assertEqual(webhook_name, webhook.name)

        webhook_id = webhook.id
        db_api.webhook_delete(self.ctx, webhook_id)

        res = db_api.webhook_get_by_name(self.ctx, webhook_name)
        self.assertIsNone(res)

        res = db_api.webhook_get_by_name(self.ctx, webhook_name,
                                         show_deleted=False)
        self.assertIsNone(res)

        res = db_api.webhook_get_by_name(self.ctx, webhook_name,
                                         show_deleted=True)
        self.assertEqual(webhook_id, res.id)

    def test_webhook_get_all(self):
        values = [{'name': 'webhook1'},
                  {'name': 'webhook2'},
                  {'name': 'webhook3'}]
        [shared.create_webhook(
            self.ctx, self.obj_id, self.obj_type,
            self.action, **v) for v in values]

        webhooks = db_api.webhook_get_all(self.ctx)
        self.assertEqual(3, len(webhooks))

        names = [webhook.name for webhook in webhooks]
        [self.assertIn(val['name'], names) for val in values]

    def test_webhook_get_all_show_deleted(self):
        values = [{'id': 'webhook1'}, {'id': 'webhook2'}, {'id': 'webhook3'}]
        for v in values:
            shared.create_webhook(self.ctx, self.obj_id, self.obj_type,
                                  self.action, **v)

        db_api.webhook_delete(self.ctx, 'webhook2')

        webhooks = db_api.webhook_get_all(self.ctx)
        self.assertEqual(2, len(webhooks))

        webhooks = db_api.webhook_get_all(self.ctx, show_deleted=False)
        self.assertEqual(2, len(webhooks))

        webhooks = db_api.webhook_get_all(self.ctx, show_deleted=True)
        self.assertEqual(3, len(webhooks))

    def test_webhook_get_all_with_limit_marker(self):
        webhook_ids = ['webhook1', 'webhook2', 'webhook3']
        for v in webhook_ids:
            shared.create_webhook(self.ctx, self.obj_id, self.obj_type,
                                  self.action, id=v,
                                  created_time=tu.utcnow())

        webhooks = db_api.webhook_get_all(self.ctx, limit=1)
        self.assertEqual(1, len(webhooks))

        webhooks = db_api.webhook_get_all(self.ctx, limit=2)
        self.assertEqual(2, len(webhooks))

        webhooks = db_api.webhook_get_all(self.ctx, limit=5)
        self.assertEqual(3, len(webhooks))

        webhooks = db_api.webhook_get_all(self.ctx, marker='webhook1')
        self.assertEqual(2, len(webhooks))

        webhooks = db_api.webhook_get_all(self.ctx, marker='webhook2')
        self.assertEqual(1, len(webhooks))

        webhooks = db_api.webhook_get_all(self.ctx, marker='webhook3')
        self.assertEqual(0, len(webhooks))

        webhooks = db_api.webhook_get_all(self.ctx, limit=1, marker='webhook1')
        self.assertEqual(1, len(webhooks))

    def test_webhook_get_all_used_sort_keys(self):
        webhook_ids = ['webhook1', 'webhook2', 'webhook3']
        for v in webhook_ids:
            shared.create_webhook(self.ctx, self.obj_id, self.obj_type,
                                  self.action, id=v)

        mock_paginate = self.patchobject(db_api.utils, 'paginate_query')
        sort_keys = ['name', 'created_time', 'deleted_time',
                     'obj_id', 'obj_type']

        db_api.webhook_get_all(self.ctx, sort_keys=sort_keys)
        args = mock_paginate.call_args[0]
        used_sort_keys = set(args[3])
        expected_keys = set(['name', 'created_time', 'deleted_time',
                             'obj_id', 'obj_type', 'id'])
        self.assertEqual(expected_keys, used_sort_keys)

    def test_webhook_get_all_sort_keys_wont_change(self):
        sort_keys = ['id']
        db_api.webhook_get_all(self.ctx, sort_keys=sort_keys)
        self.assertEqual(['id'], sort_keys)

    def test_webhook_get_all_sort_keys_and_dir(self):
        values = [{'id': '001', 'name': 'webhook1'},
                  {'id': '002', 'name': 'webhook3'},
                  {'id': '003', 'name': 'webhook2'}]
        obj_ids = {'webhook1': 'id3',
                   'webhook2': 'id2',
                   'webhook3': 'id1'}
        for v in values:
            shared.create_webhook(self.ctx, obj_ids[v['name']],
                                  self.obj_type,
                                  self.action, **v)

        webhooks = db_api.webhook_get_all(self.ctx,
                                          sort_keys=['name', 'obj_id'],
                                          sort_dir='asc')
        self.assertEqual(3, len(webhooks))
        # Sorted by name (ascending)
        self.assertEqual('001', webhooks[0].id)
        self.assertEqual('003', webhooks[1].id)
        self.assertEqual('002', webhooks[2].id)

        webhooks = db_api.webhook_get_all(self.ctx,
                                          sort_keys=['obj_id', 'name'],
                                          sort_dir='asc')
        self.assertEqual(3, len(webhooks))
        # Sorted by obj_id (ascending)
        self.assertEqual('002', webhooks[0].id)
        self.assertEqual('003', webhooks[1].id)
        self.assertEqual('001', webhooks[2].id)

        webhooks = db_api.webhook_get_all(self.ctx,
                                          sort_keys=['obj_id', 'name'],
                                          sort_dir='desc')
        self.assertEqual(3, len(webhooks))
        # Sorted by obj_id (descending)
        self.assertEqual('001', webhooks[0].id)
        self.assertEqual('003', webhooks[1].id)
        self.assertEqual('002', webhooks[2].id)

    def test_webhook_get_all_default_sort_dir(self):
        values = [{'id': '001', 'name': 'webhook1'},
                  {'id': '002', 'name': 'webhook2'},
                  {'id': '003', 'name': 'webhook3'}]
        obj_ids = {'webhook1': 'id3',
                   'webhook2': 'id2',
                   'webhook3': 'id1'}
        for v in values:
            shared.create_webhook(self.ctx, obj_ids[v['name']],
                                  self.obj_type,
                                  self.action, **v)

        webhooks = db_api.webhook_get_all(self.ctx, sort_dir='asc')
        self.assertEqual(3, len(webhooks))
        self.assertEqual(values[2]['id'], webhooks[0].id)
        self.assertEqual(values[1]['id'], webhooks[1].id)
        self.assertEqual(values[0]['id'], webhooks[2].id)

    def test_webhook_get_all_with_filters(self):
        shared.create_webhook(self.ctx, self.obj_id,
                              self.obj_type, self.action, name='webhook1')
        shared.create_webhook(self.ctx, self.obj_id,
                              self.obj_type, self.action, name='webhook2')

        filters = {'name': ['webhook1', 'webhookx']}
        results = db_api.webhook_get_all(self.ctx, filters=filters)
        self.assertEqual(1, len(results))
        self.assertEqual('webhook1', results[0]['name'])

        filters = {'name': 'webhook1'}
        results = db_api.webhook_get_all(self.ctx, filters=filters)
        self.assertEqual(1, len(results))
        self.assertEqual('webhook1', results[0]['name'])

    def test_webhook_get_all_with_empty_filters(self):
        shared.create_webhook(self.ctx, self.obj_id,
                              self.obj_type, self.action, name='webhook1')
        shared.create_webhook(self.ctx, self.obj_id,
                              self.obj_type, self.action, name='webhook2')

        filters = None
        results = db_api.webhook_get_all(self.ctx, filters=filters)
        self.assertEqual(2, len(results))

    def test_webhook_get_all_with_project_safe(self):
        shared.create_webhook(self.ctx, self.obj_id,
                              self.obj_type, self.action, name='webhook1')
        shared.create_webhook(self.ctx, self.obj_id,
                              self.obj_type, self.action, name='webhook2')

        self.ctx.project = 'a-different-project'
        results = db_api.webhook_get_all(self.ctx, project_safe=False)
        self.assertEqual(2, len(results))

        self.ctx.project = 'a-different-project'
        results = db_api.webhook_get_all(self.ctx)
        self.assertEqual(0, len(results))

        results = db_api.webhook_get_all(self.ctx, project_safe=True)
        self.assertEqual(0, len(results))

    def test_webhook_delete(self):
        res = shared.create_webhook(self.ctx, self.obj_id,
                                    self.obj_type, self.action)
        webhook_id = res.id
        webhook = db_api.webhook_get(self.ctx, webhook_id)
        self.assertIsNotNone(webhook)

        db_api.webhook_delete(self.ctx, webhook_id)
        res = db_api.webhook_get(self.ctx, webhook_id)
        self.assertIsNone(res)

    def test_webhook_delete_not_found(self):
        webhook_id = 'BogusWebhookID'
        res = db_api.webhook_delete(self.ctx, webhook_id)
        self.assertIsNone(res)

        res = db_api.webhook_get(self.ctx, webhook_id)
        self.assertIsNone(res)
