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
class NodeCreateRequestBody(base.SenlinObject):

    fields = {
        'cluster_id': fields.StringField(nullable=True, default=''),
        'metadata': fields.JsonField(nullable=True, default={}),
        'name': fields.NameField(),
        'profile_id': fields.StringField(),
        'role': fields.fields.StringField(nullable=True, default='')
    }


@base.SenlinObjectRegistry.register
class NodeCreateRequest(base.SenlinObject):

    fields = {
        'node': fields.ObjectField('NodeCreateRequestBody')
    }


@base.SenlinObjectRegistry.register
class NodeListRequest(base.SenlinObject):

    fields = {
        'cluster_id': fields.StringField(nullable=True),
        'name': fields.ListOfStringsField(nullable=True),
        'status': fields.ListOfEnumField(
            valid_values=list(consts.NODE_STATUSES), nullable=True),
        'limit': fields.NonNegativeIntegerField(nullable=True),
        'marker': fields.UUIDField(nullable=True),
        'sort': fields.SortField(
            valid_keys=list(consts.NODE_SORT_KEYS), nullable=True),
        'project_safe': fields.FlexibleBooleanField(default=True)
    }


@base.SenlinObjectRegistry.register
class NodeGetRequest(base.SenlinObject):

    fields = {
        'identity': fields.StringField(),
        'show_details': fields.FlexibleBooleanField(nullable=True,
                                                    default=False)
    }


@base.SenlinObjectRegistry.register
class NodeUpdateRequest(base.SenlinObject):

    fields = {
        'identity': fields.StringField(),
        'metadata': fields.JsonField(nullable=True),
        'name': fields.NameField(nullable=True),
        'profile_id': fields.StringField(nullable=True),
        'role': fields.fields.StringField(nullable=True)
    }


@base.SenlinObjectRegistry.register
class NodeDeleteRequest(base.SenlinObject):

    fields = {
        'identity': fields.StringField()
    }


@base.SenlinObjectRegistry.register
class NodeCheckRequest(base.SenlinObject):

    fields = {
        'identity': fields.StringField(),
        'params': fields.JsonField(nullable=True)
    }


@base.SenlinObjectRegistry.register
class NodeRecoverRequest(base.SenlinObject):

    fields = {
        'identity': fields.StringField(),
        'params': fields.JsonField(nullable=True)
    }


@base.SenlinObjectRegistry.register
class NodeOperationRequest(base.SenlinObject):

    fields = {
        'identity': fields.StringField(),
        'operation': fields.StringField(),
        'params': fields.JsonField(nullable=True)
    }
