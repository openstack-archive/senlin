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
import datetime

from senlin.common import exception
from senlin.common import schema
from senlin.db import api as db_api
from senlin.engine import environment

CHECK_RESULTS = (
    CHECK_OK, CHECK_ERROR
) = (
    'OK', 'ERROR'
)


class PolicyData(collections.Mapping):
    '''An object wrapping the policy check result.'''

    def __init__(self, status=CHECK_OK, reason='Check succeeded'):
        self.status = status
        self.reason = reason
        self.data = {}

    def __setitem__(self, key, value):
        self.data[key] = value

    def __getitem__(self, key):
        return self.data.get(key, None)

    def __len__(self):
        return len(self.data)

    def __contains__(self, key):
        return key in self.data

    def __iter__(self):
        return iter(self.data)

    def update(self, newdata):
        return self.data.update(newdata)

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
        self.name = name
        self.type = type_name

        self.id = kwargs.get('id', None)
        self.level = kwargs.get('level', self.DEBUG)
        self.cooldown = kwargs.get('cooldown', 0)
        self.spec = kwargs.get('spec', {})
        self.context = kwargs.get('context', {})
        self.data = kwargs.get('data', {})
        self.created_time = kwargs.get('created_time', None)
        self.updated_time = kwargs.get('updated_time', None)
        self.deleted_time = kwargs.get('deleted_time', None)

        self.spec_data = schema.Spec(self.spec_schema, self.spec, self.context)

    @classmethod
    def _from_db_record(cls, context, record):
        '''Construct a policy object from a database record.'''

        kwargs = {
            'id': record.id,
            'spec': record.spec,
            'level': record.level,
            'cooldown': record.cooldown,
            'created_time': record.created_time,
            'updated_time': record.updated_time,
            'deleted_time': record.deleted_time,
            'data': record.data,
            'context': context,
        }

        return cls(record.type, record.name, **kwargs)

    @classmethod
    def load(cls, context, policy_id=None, policy=None):
        '''Retrieve and reconstruct a policy object from DB.'''
        if policy is None:
            policy = db_api.policy_get(context, policy_id)
            if policy is None:
                raise exception.PolicyNotFound(policy=policy_id)

        return cls._from_db_record(context, policy)

    @classmethod
    def load_all(cls, context, limit=None, sort_keys=None, marker=None,
                 sort_dir=None, filters=None, show_deleted=False):
        '''Retrieve all policies from database.'''

        records = db_api.policy_get_all(context, limit=limit, marker=marker,
                                        sort_keys=sort_keys,
                                        sort_dir=sort_dir,
                                        filters=filters,
                                        show_deleted=show_deleted)

        for record in records:
            yield cls._from_db_record(context, record)

    @classmethod
    def delete(cls, context, policy_id):
        db_api.policy_delete(context, policy_id)

    def store(self, context):
        '''Store the policy object into database table.'''
        timestamp = datetime.datetime.utcnow()

        values = {
            'name': self.name,
            'type': self.type,
            'spec': self.spec,
            'level': self.level,
            'cooldown': self.cooldown,
            'data': self.data,
        }

        if self.id is not None:
            self.updated_time = timestamp
            values['updated_time'] = timestamp
            db_api.policy_update(self.context, self.id, values)
        else:
            self.created_time = timestamp
            values['created_time'] = timestamp
            policy = db_api.policy_create(self.context, values)
            self.id = policy.id

        return self.id

    def validate(self):
        '''Validate the schema and the data provided.'''
        self.spec_data.validate()

    def attach(self, context, cluster_id, policy_data):
        '''Method to be invoked before the policy is attached to a cluster.
        '''
        return True

    def detach(self, context, cluster_id, policy_data):
        '''Method to be invoked before the policy is detached from a cluster.
        '''
        return True

    def pre_op(self, cluster_id, action, policy_data):
        '''A method that will be invoked before an action execution.
        '''
        return policy_data

    def post_op(self, cluster_id, action, policy_data):
        '''A method that will be invoked after an action execution.
        '''
        return policy_data

    def to_dict(self):
        pb_dict = {
            'id': self.id,
            'name': self.name,
            'type': self.type,
            'spec': self.spec,
            'level': self.level,
            'cooldown': self.cooldown,
            'created_time': self.created_time,
            'updated_time': self.updated_time,
            'deleted_time': self.deleted_time,
            'data': self.data,
        }
        return pb_dict

    @classmethod
    def from_dict(cls, **kwargs):
        type_name = kwargs.get('type', '')
        name = kwargs.get('name', '')
        return cls(type_name, name, **kwargs)
