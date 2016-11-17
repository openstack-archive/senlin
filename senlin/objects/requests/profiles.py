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
class ProfileCreateRequestBody(base.SenlinObject):

    fields = {
        'name': fields.NameField(),
        'spec': fields.JsonField(),
        'metadata': fields.JsonField(nullable=True, default={}),
    }


@base.SenlinObjectRegistry.register
class ProfileCreateRequest(base.SenlinObject):

    fields = {
        'profile': fields.ObjectField('ProfileCreateRequestBody')
    }


@base.SenlinObjectRegistry.register
class ProfileListRequest(base.SenlinObject):

    fields = {
        'name': fields.ListOfStringsField(nullable=True),
        'type': fields.ListOfStringsField(nullable=True),
        'limit': fields.NonNegativeIntegerField(nullable=True),
        'marker': fields.UUIDField(nullable=True),
        'sort': fields.SortField(
            valid_keys=list(consts.PROFILE_SORT_KEYS), nullable=True),
        'project_safe': fields.FlexibleBooleanField(default=True),
    }


@base.SenlinObjectRegistry.register
class ProfileGetRequest(base.SenlinObject):

    fields = {
        'identity': fields.StringField()
    }


@base.SenlinObjectRegistry.register
class ProfileUpdateRequestBody(base.SenlinObject):

    fields = {
        'name': fields.NameField(nullable=True),
        'metadata': fields.JsonField(nullable=True)
    }


@base.SenlinObjectRegistry.register
class ProfileUpdateRequest(base.SenlinObject):

    fields = {
        'identity': fields.StringField(),
        'profile': fields.ObjectField('ProfileUpdateRequestBody'),
    }


@base.SenlinObjectRegistry.register
class ProfileDeleteRequest(base.SenlinObject):

    fields = {
        'identity': fields.StringField()
    }


@base.SenlinObjectRegistry.register
class ProfileValidateRequestBody(base.SenlinObject):

    fields = {
        'spec': fields.JsonField()
    }


@base.SenlinObjectRegistry.register
class ProfileValidateRequest(base.SenlinObject):

    fields = {
        'profile': fields.ObjectField('ProfileValidateRequestBody')
    }
