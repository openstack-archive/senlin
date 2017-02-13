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

'''
A module that contains various fake entities
'''

from senlin.common import schema
from senlin.policies import base as policy_base
from senlin.profiles import base as profile_base


class TestProfile(profile_base.Profile):

    CONTEXT = 'context'

    properties_schema = {
        CONTEXT: schema.Map("context property"),
        'INT': schema.Integer('int property', default=0),
        'STR': schema.String('string property', default='a string'),
        'MAP': schema.Map(
            'map property',
            schema={
                'KEY1': schema.Integer('key1'),
                'KEY2': schema.String('key2')
            }
        ),
        'LIST': schema.List(
            'list property',
            schema=schema.String('list item'),
        ),
    }

    OPERATIONS = {}

    def __init__(self, name, spec, **kwargs):
        super(TestProfile, self).__init__(name, spec, **kwargs)

    @classmethod
    def delete(cls, ctx, profile_id):
        super(TestProfile, cls).delete(ctx, profile_id)

    def do_create(self):
        return {}

    def do_delete(self, id):
        return True

    def do_update(self):
        return {}

    def do_check(self, id):
        return True


class TestPolicy(policy_base.Policy):
    VERSION = 1.0
    properties_schema = {
        'KEY1': schema.String('key1', default='default1'),
        'KEY2': schema.Integer('key2', required=True),
    }

    TARGET = [
        ('BEFORE', 'CLUSTER_ADD_NODES')
    ]

    def __init__(self, name, spec, **kwargs):
        super(TestPolicy, self).__init__(name, spec, **kwargs)

    def attach(self, cluster, enabled=True):
        return True, {}

    def detach(self, cluster):
        return True, 'OK'

    def pre_op(self, cluster_id, action):
        return

    def post_op(self, cluster_id, action):
        return
