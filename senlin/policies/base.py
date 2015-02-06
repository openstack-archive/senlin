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

import collections

from senlin.common import exception
from senlin.db import api as db_api
from senlin.engine import environment

CHECK_RESULTS = (
    CHECK_OK, CHECK_ERROR, CHECK_RETRY,
) = (
    'OK', 'ERROR', 'RERTY'
)


class PolicyData(collections.Mapping):
    '''An object wrapping the policy check result.'''

    def __init__(self, status=CHECK_OK, reason='Check succeeded'):
        self.status = status
        self.reason = reason
        self.data = {}

    def __setitem__(self, key, value):
        self.data.update(key, value)

    def __getitem__(self, key):
        return self.data.get(key, None)

    def __len__(self):
        return len(self.data)

    def __contains__(self, key):
        return key in self.data

    def __iter__(self):
        return iter(self.data)

    def __repr__(self):
        return ("Check Result: %s (%s)\n\t" % (self.status, self.reason) +
                "\n\t".join(self.data.values()))

    def to_dict(self):
        result = {
            'status': self.status,
            'reason': self.reason,
            'data': self.data,
        }

        return result


class Policy(object):
    '''Base class for policies.'''

    ENFORCEMENT_LEVELS = (
        CRITICAL, ERROR, WARNING, INFO, DEBUG,
    ) = (
        'CRITICAL', 'ERROR', 'WARNING', 'INFO', 'DEBUG',
    )

    def __new__(cls, type_name, name, **kwargs):
        '''Create a new policy of the appropriate class.'''

        if cls != Policy:
            PolicyClass = cls
        else:
            PolicyClass = environment.global_env().get_policy(type_name)

        return super(Policy, cls).__new__(PolicyClass)

    def __init__(self, type_name, name, **kwargs):
        self.id = kwargs.get('id', None)
        self.name = name
        self.type = type_name

        self.context = kwargs.get('context', None)
        self.cooldown = kwargs.get('cooldown', 0)
        self.level = kwargs.get('level', self.DEBUG)
        self.spec = kwargs.get('spec', {})
        self.data = kwargs.get('data', {})

    def store(self):
        '''Store the policy object into database table.

        This could be a policy_create or a policy_update DB API invocation,
        depends on whether self.id is set.
        '''
        values = {
            'name': self.name,
            'type': self.type,
            'cooldown': self.cooldown,
            'level': self.level,
            'spec': self.spec,
            'data': self.data,
        }

        if self.id:
            db_api.policy_update(self.context, self.id, values)
        else:
            policy = db_api.policy_create(self.context, values)
            self.id = policy.id

        return self.id

    @classmethod
    def from_db_record(cls, context, record):
        '''Construct a policy object from a database record.'''

        kwargs = {
            'id': record.id,
            'name': record.name,
            'context': context,
            'type': record.type,
            'cooldown': record.cooldown,
            'level': record.level,
            'spec': record.spec,
            'data': record.data,
        }
        return cls(record.type, record.name, **kwargs)

    @classmethod
    def load(cls, context, policy_id=None, policy=None):
        '''Retrieve and reconstruct a policy object from DB.'''

        if policy is None:
            policy = db_api.policy_get(context, policy_id)
            if policy is None:
                raise exception.PolicyNotFound(policy=policy_id)

        return cls.from_db_record(context, policy)

    def pre_op(self, cluster_id, action, **kwargs):
        '''Force all subclasses to implement an operation that will be invoked
        before an action.
        '''
        return NotImplemented

    def enforce(self, cluster_id, action, **kwargs):
        '''Force all subclasses to implement an operation that can be called
        during an action.
        '''
        return NotImplemented

    def post_op(self, cluster_id, action, **kwargs):
        '''Force all subclasses to implement an operation that will be
        performed after an action.
        '''
        return NotImplemented

    def to_dict(self):
        pb_dict = {
            'id': self.id,
            'name': self.name,
            'type': self.type,
            'spec': self.spec,
            'level': self.level,
            'cooldown': self.cooldown,
            'data': self.data,
        }
        return pb_dict

    @classmethod
    def from_dict(cls, **kwargs):
        type_name = kwargs.get('type', '')
        name = kwargs.get('name', '')
        return cls(type_name, name, **kwargs)
