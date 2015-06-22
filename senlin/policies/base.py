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


class Policy(object):
    '''Base class for policies.'''

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
        # TODO(Qiming): make this default level a WOULD?
        self.level = kwargs.get('level', 0)
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

    def attach(self, cluster_id, action):
        '''Method to be invoked before policy is attached to a cluster.'''
        return True

    def detach(self, cluster_id, action):
        '''Method to be invoked before policy is detached from a cluster.'''
        return True

    def pre_op(self, cluster_id, action):
        '''A method that will be invoked before an action execution.'''
        return

    def post_op(self, cluster_id, action):
        '''A method that will be invoked after an action execution.'''
        return

    def to_dict(self):
        def _fmt_time(value):
            return value and value.isoformat()

        pb_dict = {
            'id': self.id,
            'name': self.name,
            'type': self.type,
            'spec': self.spec,
            'level': self.level,
            'cooldown': self.cooldown,
            'created_time': _fmt_time(self.created_time),
            'updated_time': _fmt_time(self.updated_time),
            'deleted_time': _fmt_time(self.deleted_time),
            'data': self.data,
        }
        return pb_dict

    @classmethod
    def from_dict(cls, **kwargs):
        type_name = kwargs.get('type', '')
        name = kwargs.get('name', '')
        return cls(type_name, name, **kwargs)
