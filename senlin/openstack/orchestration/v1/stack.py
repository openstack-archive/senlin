# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.


from openstack import exceptions
from openstack import resource
from openstack import utils


class Stack(resource.Resource):
    resource_key = 'stack'
    resources_key = 'stacks'
    base_path = '/stacks'

    # capabilities
    allow_list = True
    allow_create = True
    allow_retrieve = True
    allow_delete = True

    # Properties
    description = resource.prop('description')
    stack_status = resource.prop('stack_status')
    stack_status_reason = resource.prop('stack_status_reason')
    creation_time = resource.prop('created_time')
    deletion_time = resource.prop('deletion_time')
    updated_time = resource.prop('updated_time')
    stack_owner = resource.prop('stack_owner')
    parent = resource.prop('parent')

    @classmethod
    def create_by_id(cls, session, attrs, resource_id=None, path_args=None):
        '''Overriden version of Resource.create_by_id method.

        Heat stack_create API is asymetric, so this is necessary.
        '''
        if not cls.allow_create:
            raise exceptions.MethodNotSupported('create')

        body = attrs

        if path_args:
            url = cls.base_path % path_args
        else:
            url = cls.base_path

        if resource_id:
            url = utils.urljoin(url, resource_id)
            resp = session.put(url, service=cls.service, json=body).body
        else:
            resp = session.post(url, service=cls.service,
                                json=body).body

        if cls.resource_key:
            resp = resp[cls.resource_key]

        return resp
