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
from senlin.db import api as db_api
from senlin.engine import environment
from senlin.openstack.common import log as logging

LOG = logging.getLogger(__name__)


class Profile(object):
    '''
    Base class for profiles.
    '''
    def __new__(cls, type_name, name, **kwargs):
        '''
        Create a new profile of the appropriate class.
        '''
        if cls != Profile:
            ProfileClass = cls
        else:
            ProfileClass = environment.global_env().get_profile(type_name)

        return super(Profile, cls).__new__(ProfileClass)

    def __init__(self, type_name, name, **kwargs):
        '''
        Initialize the profile with given parameters and a JSON object.
        '''
        self.name = name
        self.type = type_name
        self.id = kwargs.get('id', None)
        self.permission = kwargs.get('permission', '')
        self.spec = kwargs.get('spec', {})
        self.tags = kwargs.get('tags', {})
        self.created_time = kwargs.get('created_time', None)
        self.updated_time = kwargs.get('updated_time', None)
        self.deleted_time = kwargs.get('deleted_time', None)

    @classmethod
    def from_db_record(cls, context, record):
        '''
        Construct a profile object from database record.
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

        return cls(record.type, record.name, **kwargs)

    @classmethod
    def load(cls, context, profile_id):
        '''
        Retrieve a profile object from database.
        '''
        profile = db_api.profile_get(context, profile_id)
        if profile is None:
            msg = _('No profile with id "%s" exists') % profile_id
            raise exception.NotFound(msg)

        return cls.from_db_record(context, profile)

    @classmethod
    def load_all(cls, context, limit=None, sort_keys=None, marker=None,
                 sort_dir=None, filters=None, show_deleted=False):
        '''
        Retrieve all profiles from database.
        '''
        records = db_api.profile_get_all(context, limit, marker, sort_keys,
                                         sort_dir, filters, show_deleted)

        for record in records:
            yield cls.from_db_record(context, record)

    @classmethod
    def delete(cls, context, profile_id):
        db_api.profile_delete(context, profile_id)

    def store(self, context):
        '''
        Store the profile into database and return its ID.
        '''
        values = {
            'name': self.name,
            'type': self.type,
            'spec': self.spec,
            'permission': self.permission,
            'tags': self.tags,
            'created_time': datetime.datetime.utcnow()
        }
        profile = db_api.profile_create(context, values)
        self.id = profile.id
        return profile.id

    @classmethod
    def create_object(cls, obj):
        profile = cls.load(obj.context, obj.profile_id)
        return profile.do_create(obj)

    @classmethod
    def delete_object(cls, obj):
        profile = cls.load(obj.context, obj.profile_id)
        return profile.do_delete(obj)

    @classmethod
    def update_object(cls, obj, new_profile_id):
        profile = cls.load(obj.context, obj.profile_id)
        new_profile = cls.load(obj.context, new_profile_id)
        return profile.do_update(obj, new_profile)

    def do_create(self, obj):
        '''
        For subclass to override.
        '''
        return NotImplemented

    def do_delete(self, obj):
        '''
        For subclass to override.
        '''
        return NotImplemented

    def do_update(self, obj, new_profile):
        '''
        For subclass to override.
        '''
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
