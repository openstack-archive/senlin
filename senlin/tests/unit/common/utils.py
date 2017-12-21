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

import random
import string

from oslo_config import cfg
from oslo_db import options
from oslo_utils import timeutils
import sqlalchemy

from senlin.common import context
from senlin.db import api as db_api
from senlin import objects


def random_name():
    return ''.join(random.choice(string.ascii_uppercase)
                   for x in range(10))


def setup_dummy_db():
    options.cfg.set_defaults(options.database_opts, sqlite_synchronous=False)
    options.set_defaults(cfg.CONF, connection="sqlite://")
    engine = db_api.get_engine()
    db_api.db_sync(engine)
    engine.connect()


def reset_dummy_db():
    engine = db_api.get_engine()
    meta = sqlalchemy.MetaData()
    meta.reflect(bind=engine)

    for table in reversed(meta.sorted_tables):
        if table.name == 'migrate_version':
            continue
        engine.execute(table.delete())


def dummy_context(user=None, project=None, password=None, roles=None,
                  user_id=None, trust_id=None, region_name=None, domain=None,
                  is_admin=False, api_version=None):

    roles = roles or []
    return context.RequestContext.from_dict({
        'project_id': project or 'test_project_id',
        'user_id': user_id or 'test_user_id',
        'user_name': user or 'test_username',
        'password': password or 'password',
        'roles': roles or [],
        'is_admin': is_admin,
        'auth_url': 'http://server.test:5000/v2.0',
        'auth_token': 'abcd1234',
        'trust_id': trust_id or 'trust_id',
        'region_name': region_name or 'region_one',
        'domain_id': domain or '',
        'api_version': api_version or '1.2',
    })


def create_profile(context, profile_id):
    values = {
        'id': profile_id,
        'context': context.to_dict(),
        'type': 'os.nova.server-1.0',
        'name': 'test-profile',
        'spec': {
            'type': 'os.nova.server',
            'version': '1.0',
        },
        'created_at': timeutils.utcnow(True),
        'user': context.user_id,
        'project': context.project_id,
    }
    return objects.Profile.create(context, values)


def create_cluster(context, cluster_id, profile_id, **kwargs):
    values = {
        'id': cluster_id,
        'profile_id': profile_id,
        'name': 'test-cluster',
        'next_index': 1,
        'min_size': 1,
        'max_size': 5,
        'desired_capacity': 3,
        'status': 'ACTIVE',
        'init_at': timeutils.utcnow(True),
        'user': context.user_id,
        'project': context.project_id,
    }
    values.update(kwargs)
    return objects.Cluster.create(context, values)


def create_node(context, node_id, profile_id, cluster_id, physical_id=None):
    values = {
        'id': node_id,
        'name': 'node1',
        'profile_id': profile_id,
        'cluster_id': cluster_id or '',
        'physical_id': physical_id,
        'index': 2,
        'init_at': timeutils.utcnow(True),
        'created_at': timeutils.utcnow(True),
        'role': 'test_node',
        'status': 'ACTIVE',
        'user': context.user_id,
        'project': context.project_id,
    }
    return objects.Node.create(context, values)


def create_policy(context, policy_id, name=None):
    values = {
        'id': policy_id,
        'name': name or 'test_policy',
        'type': 'senlin.policy.dummy-1.0',
        'spec': {
            'type': 'senlin.policy.dummy',
            'version': '1.0',
            'properties': {
                'key1': 'value1',
                'key2': 2
            }
        },
        'created_at': timeutils.utcnow(True),
        'user': context.user_id,
        'project': context.project_id,
    }
    return objects.Policy.create(context, values)
