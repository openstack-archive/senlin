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

    def store(self):
        '''
        Store the profile into database and return its ID.
        '''
        values = {
            'name': self.name,
            'type': self.type,
            'spec': self.spec,
            'permission': self.permission,
            'tags': self.tags,
        }
        profile = db_api.profile_create(self.context, values)
        return profile.id

    @classmethod
    def create_object(cls, obj):
        profile = cls.from_db(obj.context, obj.profile_id)
        return profile.do_create(obj)

    @classmethod
    def delete_object(cls, obj):
        profile = cls.from_db(obj.context, obj.profile_id)
        return profile.do_delete(obj)

    @classmethod
    def update_object(cls, obj, new_profile_id):
        profile = cls.from_db(obj.context, obj.profile_id)
        return profile.do_update(obj, new_profile_id)

    def do_create(self):
        '''
        For subclass to overrided.
        '''
        return NotImplemented

    def do_delete(self):
        '''
        For subclass to override.
        '''
        return NotImplemented

    def do_update(self, new_profile):
        '''
        For subclass to override.
        '''
        return NotImplemented

    def to_dict(self):
        pb_dict = {
            'name': self.name,
            'type': self.type_name,
            'uuid': self.uuid,
            'permission': self.permission,
            'spec': self.spec,
        }
        return pb_dict

    @classmethod
    def from_dict(cls, **kwargs):
        return cls(kwargs)
