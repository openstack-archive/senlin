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


from oslo_serialization import jsonutils
from oslo_utils import timeutils as tu
from oslo_utils import uuidutils

from senlin.db.sqlalchemy import api as db_api
from senlin.engine import parser


sample_profile = '''
  name: test_profile_name
  type: my_test_profile_type
  spec:
    template:
      heat_template_version: "2013-05-23"
      resources:
        myrandom: OS::Heat::RandomString
      files:
        myfile: contents
'''

sample_action = '''
  name: test_cluster_create_action
  target: cluster_001
  action: create
  cause: User Initiate
  timeout: 60
  control: READY
  status: INIT
  status_reason: Just Initialized
  inputs:
    min_size: 1
    max_size: 10
    pause_time: PT10M
'''


UUIDs = (UUID1, UUID2, UUID3) = sorted([uuidutils.generate_uuid()
                                        for x in range(3)])


def create_profile(context, profile=sample_profile, **kwargs):
    data = parser.simple_parse(profile)
    data['user'] = context.user_id
    data['project'] = context.project_id
    data['domain'] = context.domain_id
    data.update(kwargs)
    return db_api.profile_create(context, data)


def create_cluster(ctx, profile, **kwargs):
    values = {
        'name': 'db_test_cluster_name',
        'profile_id': profile.id,
        'user': ctx.user_id,
        'project': ctx.project_id,
        'domain': 'unknown',
        'parent': None,
        'next_index': 1,
        'timeout': 60,
        'desired_capacity': 0,
        'init_at': tu.utcnow(True),
        'status': 'INIT',
        'status_reason': 'Just Initialized',
        'meta_data': {},
        'dependents': {},
        'config': {},
    }
    values.update(kwargs)
    if 'project' in kwargs:
        values.update({'project': kwargs.get('project')})
    return db_api.cluster_create(ctx, values)


def create_node(ctx, cluster, profile, **kwargs):
    if cluster:
        cluster_id = cluster.id
        index = db_api.cluster_next_index(ctx, cluster_id)
    else:
        cluster_id = ''
        index = -1

    values = {
        'name': 'test_node_name',
        'physical_id': UUID1,
        'cluster_id': cluster_id,
        'profile_id': profile.id,
        'project': ctx.project_id,
        'index': index,
        'role': None,
        'created_at': None,
        'updated_at': None,
        'status': 'ACTIVE',
        'status_reason': 'create complete',
        'meta_data': jsonutils.loads('{"foo": "123"}'),
        'data': jsonutils.loads('{"key1": "value1"}'),
        'dependents': {},
    }
    values.update(kwargs)
    return db_api.node_create(ctx, values)


def create_webhook(ctx, obj_id, obj_type, action, **kwargs):
    values = {
        'name': 'test_webhook_name',
        'user': ctx.user_id,
        'project': ctx.project_id,
        'domain': ctx.domain_id,
        'created_at': None,
        'obj_id': obj_id,
        'obj_type': obj_type,
        'action': action,
        'credential': None,
        'params': None,
    }
    values.update(kwargs)
    return db_api.webhook_create(ctx, values)


def create_action(ctx, **kwargs):
    values = {
        'context': kwargs.get('context'),
        'description': 'Action description',
        'target': kwargs.get('target'),
        'action': kwargs.get('action'),
        'cause': 'Reason for action',
        'owner': kwargs.get('owner'),
        'interval': -1,
        'inputs': {'key': 'value'},
        'outputs': {'result': 'value'},
        'depends_on': [],
        'depended_by': []
    }
    values.update(kwargs)
    return db_api.action_create(ctx, values)


def create_policy(ctx, **kwargs):
    values = {
        'name': 'test_policy',
        'type': 'senlin.policy.scaling',
        'user': ctx.user_id,
        'project': ctx.project_id,
        'domain': ctx.domain_id,
        'spec': {
            'type': 'senlin.policy.scaling',
            'version': '1.0',
            'properties': {
                'adjustment_type': 'WHATEVER',
                'count': 1,
            }
        },
        'data': None,
    }

    values.update(kwargs)
    return db_api.policy_create(ctx, values)


def create_event(ctx, **kwargs):
    values = {
        'timestamp': tu.utcnow(True),
        'obj_id': 'FAKE_ID',
        'obj_name': 'FAKE_NAME',
        'obj_type': 'CLUSTER',
        'cluster_id': 'FAKE_CLUSTER',
        'level': '20',
        'user': ctx.user_id,
        'project': ctx.project_id,
        'action': 'DANCE',
        'status': 'READY',
        'status_reason': 'Just created.',
        'meta_data': {
            'air': 'polluted'
        }
    }

    values.update(kwargs)
    return db_api.event_create(ctx, values)
