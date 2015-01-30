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


from openstack import resource
from openstack.orchestration import orchestration_service


class Stack(resource.Resource):
    resources_key = 'stacks'
    base_path = '/stacks'
    service = orchestration_service.OrchestrationService()

    # capabilities
    allow_list = True
    allow_create = True
    allow_retrieve = True
    allow_delete = True

    # Properties
    id = resource.prop('id')
    name = resource.prop('name')
    description = resource.prop('description')
    stack_status = resource.prop('stack_status')
    stack_status_reason = resource.prop('stack_status_reason')
    creation_time = resource.prop('created_time')
    deletion_time = resource.prop('deletion_time')
    updated_time = resource.prop('updated_time')
    stack_owner = resource.prop('stack_owner')
    parent  = resource.prop('parent')
