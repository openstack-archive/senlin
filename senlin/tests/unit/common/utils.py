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
import sqlalchemy

from senlin.common import context
from senlin.db import api as db_api

get_engine = db_api.get_engine


def random_name():
    return ''.join(random.choice(string.ascii_uppercase)
                   for x in range(10))


def setup_dummy_db():
    options.cfg.set_defaults(options.database_opts, sqlite_synchronous=False)
    options.set_defaults(cfg.CONF,
                         connection="sqlite://",
                         sqlite_db='senlin.db')
    engine = get_engine()
    db_api.db_sync(engine)
    engine.connect()


def reset_dummy_db():
    engine = get_engine()
    meta = sqlalchemy.MetaData()
    meta.reflect(bind=engine)

    for table in reversed(meta.sorted_tables):
        if table.name == 'migrate_version':
            continue
        engine.execute(table.delete())


def dummy_context(user=None, project=None, password=None, roles=None,
                  user_id=None, trust_id=None, region_name=None, domain=None,
                  is_admin=False):

    roles = roles or []
    return context.RequestContext.from_dict({
        'project': project or 'test_project_id',
        'user': user_id or 'test_user_id',
        'user_name': user or 'test_username',
        'password': password or 'password',
        'roles': roles or [],
        'is_admin': is_admin,
        'auth_url': 'http://server.test:5000/v2.0',
        'auth_token': 'abcd1234',
        'trust_id': trust_id or 'trust_id',
        'region_name': region_name or 'region_one',
        'domain': domain or ''
    })
