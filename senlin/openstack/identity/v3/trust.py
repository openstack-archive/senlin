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


from openstack.identity import identity_service
from openstack import resource


class Trust(resource.Resource):
    resource_key = 'trust'
    resources_key = 'trusts'
    base_path = '/OS-TRUST/trusts'
    service = identity_service.IdentityService()

    # capabilities
    allow_create = True
    allow_delete = True
    allow_list = True
    allow_retrieve = True

    # Properties
    project_id = resource.prop('project_id')
    expires_at = resource.prop('expires_at')
    id = resource.prop('id')
    impersonation = resource.prop('impersonation')
    trustee_user_id = resource.prop('trustee_user_id')
    trustor_user_id = resource.prop('trustor_user_id')
