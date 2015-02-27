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

import datetime
import json
import uuid

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
    permission: xxxyyy
'''

sample_policy = '''
  name: test_scaling_policy
  type: ScalingPolicy
  cooldown: 10
  level: WARNING
  spec:
    min_size: 1
    max_size: 10
    pause_time: PT10M
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


UUIDs = (UUID1, UUID2, UUID3) = sorted([str(uuid.uuid4())
                                        for x in range(3)])


def create_profile(context, profile=sample_profile, **kwargs):
    data = parser.parse_profile(profile)
    data.update(kwargs)
    return db_api.profile_create(context, data)


def create_policy(context, policy=sample_policy, **kwargs):
    data = parser.parse_policy(policy)
    data.update(kwargs)
    return db_api.policy_create(context, data)


def create_cluster(ctx, profile, **kwargs):
    values = {
        'name': 'db_test_cluster_name',
        'profile_id': profile.id,
        'user': ctx.user,
        'project': ctx.tenant_id,
        'domain': 'unknown',
        'parent': None,
        'next_index': 1,
        'timeout': 60,
        'size': 0,
        'init_time': datetime.datetime.utcnow(),
        'status': 'INIT',
        'status_reason': 'Just Initialized',
        'tags': {},
    }
    values.update(kwargs)
    if 'tenant_id' in kwargs:
        values.update({'project': kwargs.get('tenant_id')})
    return db_api.cluster_create(ctx, values)


def create_node(ctx, cluster, profile, **kwargs):
    values = {
        'name': 'test_node_name',
        'physical_id': UUID1,
        'cluster_id': cluster.id if cluster else None,
        'profile_id': profile.id,
        'project': ctx.tenant_id,
        'index': 0,
        'role': None,
        'created_time': None,
        'updated_time': None,
        'deleted_time': None,
        'status': 'ACTIVE',
        'status_reason': 'create complete',
        'tags': json.loads('{"foo": "123"}'),
        'data': json.loads('{"key1": "value1"}'),
    }
    values.update(kwargs)
    return db_api.node_create(ctx, values)


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
