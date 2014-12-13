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


class ProfileBase(object):
    '''
    Base class for profiles.
    '''
    def __init__(self, name, type_name, **kwargs):
        self.name = name
        self.type_name = type_name
        self.permission = ''
        self.uuid = None
        self.spec = {}

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
    def from_dict(self, **kwargs):
        pb = ProfileBase(**kwargs)
        return pb
