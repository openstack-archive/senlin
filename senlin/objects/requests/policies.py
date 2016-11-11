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

from senlin.common import consts
from senlin.objects import base
from senlin.objects import fields


@base.SenlinObjectRegistry.register
class PolicyListRequest(base.SenlinObject):

    fields = {
        'name': fields.ListOfStringsField(nullable=True),
        'type': fields.ListOfStringsField(nullable=True),
        'limit': fields.NonNegativeIntegerField(nullable=True),
        'marker': fields.UUIDField(nullable=True),
        'sort': fields.SortField(
            valid_keys=list(consts.POLICY_SORT_KEYS), nullable=True),
        'project_safe': fields.FlexibleBooleanField(default=True),
    }


@base.SenlinObjectRegistry.register
class PolicyCreateRequestBody(base.SenlinObject):

    fields = {
        'name': fields.NameField(),
        'spec': fields.JsonField(),
    }


@base.SenlinObjectRegistry.register
class PolicyCreateRequest(base.SenlinObject):

    fields = {
        'policy': fields.ObjectField('PolicyCreateRequestBody')
    }


@base.SenlinObjectRegistry.register
class PolicyGetRequest(base.SenlinObject):

    fields = {
        'identity': fields.StringField()
    }


@base.SenlinObjectRegistry.register
class PolicyUpdateRequestBody(base.SenlinObject):

    fields = {
        'name': fields.NameField()
    }


@base.SenlinObjectRegistry.register
class PolicyUpdateRequest(base.SenlinObject):

    fields = {
        'identity': fields.StringField(),
        'policy': fields.ObjectField('PolicyUpdateRequestBody'),
    }


@base.SenlinObjectRegistry.register
class PolicyDeleteRequest(base.SenlinObject):

    fields = {
        'identity': fields.StringField()
    }


@base.SenlinObjectRegistry.register
class PolicyValidateRequestBody(base.SenlinObject):

    fields = {
        'spec': fields.JsonField()
    }


@base.SenlinObjectRegistry.register
class PolicyValidateRequest(base.SenlinObject):

    fields = {
        'policy': fields.ObjectField('PolicyValidateRequestBody')
    }
