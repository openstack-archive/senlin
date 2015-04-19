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

from oslo_log import log as logging
from senlin.common import context
from senlin.common import exception
from senlin.common import schema
from senlin.db import api as db_api
from senlin.drivers.openstack import keystone_v3 as keystoneclient
from senlin.engine import environment

LOG = logging.getLogger(__name__)


class Profile(object):
    '''Base class for profiles.'''

    def __new__(cls, ctx, type_name, name, **kwargs):
        '''Create a new profile of the appropriate class.'''

        if cls != Profile:
            ProfileClass = cls
        else:
            ProfileClass = environment.global_env().get_profile(type_name)

        return super(Profile, cls).__new__(ProfileClass)

    def __init__(self, ctx, type_name, name, **kwargs):
        '''Initialize the profile with given parameters and a JSON object.'''

        self.name = name
        self.type = type_name
        self.id = kwargs.get('id', None)

        self.context = ctx
        self.spec = kwargs.get('spec', None)
        self.spec_data = schema.Spec(self.spec_schema, self.spec, self.context)

        self.permission = kwargs.get('permission', '')
        self.tags = kwargs.get('tags', {})
        self.created_time = kwargs.get('created_time', None)
        self.updated_time = kwargs.get('updated_time', None)
        self.deleted_time = kwargs.get('deleted_time', None)

    @classmethod
    def from_db_record(cls, record):
        '''Construct a profile object from database record.

        :param context: the context used for DB operations.
        :param record: a DB Profle object that contains all required fields.
        '''
        kwargs = {
            'id': record.id,
            'spec': record.spec,
            'permission': record.permission,
            'tags': record.tags,
            'created_time': record.created_time,
            'updated_time': record.updated_time,
            'deleted_time': record.deleted_time,
        }

        ctx = context.RequestContext.from_dict(record.context)
        return cls(ctx, record.type, record.name, **kwargs)

    @classmethod
    def load(cls, context, profile_id=None, profile=None):
        '''Retrieve a profile object from database.'''
        if profile is None:
            profile = db_api.profile_get(context, profile_id)
            if profile is None:
                raise exception.ProfileNotFound(profile=profile_id)

        return cls.from_db_record(profile)

    @classmethod
    def load_all(cls, context, limit=None, sort_keys=None, marker=None,
                 sort_dir=None, filters=None, show_deleted=False):
        '''Retrieve all profiles from database.'''

        records = db_api.profile_get_all(context, limit=limit, marker=marker,
                                         sort_keys=sort_keys,
                                         sort_dir=sort_dir,
                                         filters=filters,
                                         show_deleted=show_deleted)

        for record in records:
            yield cls.from_db_record(record)

    @classmethod
    def delete(cls, context, profile_id):
        db_api.profile_delete(context, profile_id)

    def store(self, context):
        '''Store the profile into database and return its ID.'''
        timestamp = datetime.datetime.utcnow()

        values = {
            'name': self.name,
            'type': self.type,
            'context': self.context.to_dict(),
            'spec': self.spec,
            'permission': self.permission,
            'tags': self.tags,
        }

        if self.id:
            self.updated_time = timestamp
            values['updated_time'] = timestamp
            db_api.profile_update(self.context, self.id, values)
        else:
            self.created_time = timestamp
            values['created_time'] = timestamp
            profile = db_api.profile_create(self.context, values)
            self.id = profile.id

        return self.id

    @classmethod
    def create_object(cls, context, obj):
        profile = cls.load(context, obj.profile_id)
        return profile.do_create(obj)

    @classmethod
    def delete_object(cls, context, obj):
        profile = cls.load(context, obj.profile_id)
        return profile.do_delete(obj)

    @classmethod
    def update_object(cls, context, obj, new_profile_id):
        profile = cls.load(context, obj.profile_id)
        new_profile = cls.load(context, new_profile_id)
        return profile.do_update(obj, new_profile)

    def validate(self):
        '''Validate the schema and the data provided.'''
        self.spec_data.validate()

    def _get_connection_params(self, obj):
        cred = db_api.cred_get(self.context, obj.user, obj.project)
        if cred is None:
            raise exception.TrustNotFound(trustor=obj.user)

        trust_id = cred.cred['openstack']['trust']
        ctx = keystoneclient.get_service_credentials()
        params = {
            'auth_url': ctx['auth_url'],
            'user_name': ctx['user_name'],
            'user_domain_name': ctx['user_domain_name'],
            'password': ctx['password'],
            'project_id': obj.project,
            'trusts': trust_id,
        }

        profile_context = self.spec_data[self.CONTEXT]
        if profile_context is not None and len(profile_context) > 0:
            # We don't know what will happen, it is completely left to users.
            params.update(profile_context)
        return params

    def do_create(self, obj):
        '''For subclass to override.'''

        return NotImplemented

    def do_delete(self, obj):
        '''For subclass to override.'''

        return NotImplemented

    def do_update(self, obj, new_profile):
        '''For subclass to override.'''

        return NotImplemented

    def do_check(self, obj):
        '''For subclass to override.'''
        return NotImplemented

    def to_dict(self):
        pb_dict = {
            'id': self.id,
            'name': self.name,
            'type': self.type,
            'permission': self.permission,
            'spec': self.spec,
            'tags': self.tags,
            'created_time': self.created_time,
            'updated_time': self.updated_time,
            'deleted_time': self.deleted_time,
        }
        return pb_dict

    @classmethod
    def from_dict(cls, **kwargs):
        return cls(kwargs)
