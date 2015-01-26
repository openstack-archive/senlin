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

#from senlin.drivers import heat_v1 as heat
from senlin.profiles import base

__type_name__ = 'os.heat.resource'


class ResourceProfile(base.Profile):
    '''
    Profile for an OpenStack Heat resource.
    When this profile is used, the whole cluster is Heat stack, composed
    of resources initialzed from this profile.
    '''
    def __init__(self, name, type_name=__type_name__, **kwargs):
        super(ResourceProfile, self).__init__(name, type_name, kwargs)

    def do_create(self):
        '''
        A resource is represented as a YAML snippet that can be composed
        into a Heat stack.
        '''
        return {}

    def do_delete(self, id):
        return True

    def do_update(self, ):
        self.status = self.UPDATING
        # TODO(anyone): do update
        self.status = self.ACTIVE
        return {}

    def do_check(self, id):
        #TODO(liuh): add actual checking logic
        return True
