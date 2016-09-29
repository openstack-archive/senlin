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

from senlin.objects import base
from senlin.objects import fields


@base.SenlinObjectRegistry.register
class ClusterCreateRequestBody(base.SenlinObject):

    fields = {
        'name': fields.NameField(),
        'profile_id': fields.StringField(),
        'min_size': fields.IntegerField(nullable=True, default=0),
        'max_size': fields.IntegerField(nullable=True, default=-1),
        'desired_capacity': fields.IntegerField(nullable=True, default=0),
        'metadata': fields.JsonField(nullable=True, default={}),
    }


@base.SenlinObjectRegistry.register
class ClusterCreateRequest(base.SenlinObject):

    fields = {
        'cluster': fields.ObjectField('ClusterCreateRequestBody')
    }
