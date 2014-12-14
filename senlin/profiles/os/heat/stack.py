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

import uuid

from senlin.drivers import heat_v1 as heat
from senlin.profile import base

__type_name__ = 'os.heat.stack'


class StackProfile(base.ProfileBase):
    '''
    Profile for an OpenStack Heat stack.
    When this profile is used, the whole cluster is a collection of Heat
    stacks.
    '''
    def __init__(self, name, type_name=__type_name__, **kwargs):
        super(StackProfile, self).__init__(name, type_name, kwargs)
        self.enable_rollback = 
        self.timeout = kwargs.get('timeout') or 60

    def do_create(self):
        return stack

    def do_delete(self):
        return True

    def do_update(self, ):
        self.status = self.UPDATING
        self.status = self.ACTIVE
        return True
