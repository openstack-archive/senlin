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
import uuid

from oslo_config import cfg
from oslo_db import options
import sqlalchemy

from senlin.common import context
from senlin.db import api as db_api
from senlin.engine import node as node_mod

get_engine = db_api.get_engine


class UUIDStub(object):
    def __init__(self, value):
        self.value = value

    def __enter__(self):
        self.uuid4 = uuid.uuid4
        uuid_stub = lambda: self.value
        uuid.uuid4 = uuid_stub

    def __exit__(self, *exc_info):
        uuid.uuid4 = self.uuid4


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


def dummy_context(user='test_username', project='test_project_id',
                  password='password', roles=None, user_id='test_user_id',
                  trust_id=None, region_name=None, domain=None):
    roles = roles or []
    return context.RequestContext.from_dict({
        'project': project,
        'user': user_id,
        'user_name': user,
        'password': password,
        'roles': roles,
        'is_admin': False,
        'auth_url': 'http://server.test:5000/v2.0',
        'auth_token': 'abcd1234',
        'trust_id': trust_id,
        'region_name': region_name,
        'domain': domain
    })


class PhysName(object):
    mock_short_id = 'x' * 12

    def __init__(self, cluster_name, node_name, limit=255):
        name = '%s-%s-%s' % (cluster_name,
                             node_name,
                             self.mock_short_id)
        self._physname = node_mod.Node.reduce_physical_node_name(
            name, limit)
        self.cluster, self.res, self.sid = self._physname.rsplit('-', 2)

    def __eq__(self, physical_name):
        try:
            stk, res, short_id = str(physical_name).rsplit('-', 2)
        except ValueError:
            return False

        if len(short_id) != len(self.mock_short_id):
            return False

        # ignore the cluster portion of the name, as it may have been truncated
        return res == self.res

    def __ne__(self, physical_name):
        return not self.__eq__(physical_name)

    def __repr__(self):
        return self._physname
