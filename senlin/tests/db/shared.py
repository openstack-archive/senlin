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


from senlin.db.sqlalchemy import api as db_api
from senlin.engine import parser

sample_profile = '''
  name: my_test_profile
  type: os.heat.stack
  spec:
    template:
      get_file: template_file
    files:
      fname: contents
'''


def create_profile(context, **kwargs):
    data = parser.parse_profile(sample_profile)
    values = {
        'name': 'test_profile_name',
        'type': 'os.heat.stack',
        'spec': {
            'template': {
                'heat_template_version': '2013-05-23',
                'resources': {
                    'myrandom': 'OS::Heat::RandomString',
                }
            },
            'files': {'foo': 'bar'}
        },
        'permission': 'xxxyyy',
    }
    values.update(kwargs)
    return db_api.profile_create(context, values)


def create_cluster(ctx, profile, **kwargs):
    values = {
        'name': 'db_test_cluster_name',
        'profile_id': profile.id,
        'user': ctx.user,
        'project': ctx.tenant_id,
        'domain': 'unknown',
        'parent': None,
        'next_index': 0,
        'timeout': '60',
        'status': 'INIT',
        'status_reason': 'Just Initialized'
    }
    values.update(kwargs)
    return db_api.cluster_create(ctx, values)
