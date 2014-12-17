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
import uuid

from senlin.openstack.common import log as logging

LOG = logging.getLogger(__name__)


class ProfileBase(object):
    '''
    Base class for profiles.
    '''
    def __new__(cls, profile, *args, **kwargs):
        '''
        Create a new profile of the appropriate class.
        '''
        global _profile_classes
        if _profile_classes is None:
            mgr = extension.ExtensionManager(name_space='senlin.profiles',
                                             invoke_on_load=False,
                                             verify_requirements=True)
            _profile_classes = dict((tuple(name.split('.')), mgr[name].plugin)
                                    for name in mgr.names())

        if cls != ProfileBase:
            ProfileClass = cls
        else:
            ProfileClass = get_profile_class(profile)

        return super(Profile, cls).__new__(ProfileClass)

    def __init__(self, name, type_name, **kwargs):
        '''
        Initialize the profile with given parameters and a JSON object.
        '''
        self.name = name
        self.type_name = type_name
        self.permission = ''
        self.spec = kwargs.get('spec')
        self.tags = {}

    @classmethod
    def create_object(cls, name, type_name, **kwargs):
        obj = cls(name, type_name, kwargs)
        physical_id = obj.do_create()
        return physical_id

    @classmethod
    def delete_object(cls, physical_id):
        obj = db_api.load_member(physical_id=physical_id)
        result = obj.do_delete()
        return result

    @classmethod
    def update_object(cls, physical_id, new_profile):
        obj = db_api.load_member(physical_id=physical_id)
        result = obj.do_update()
        return result

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
        pb = cls(kwargs)
        return pb
