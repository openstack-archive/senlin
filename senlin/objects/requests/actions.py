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
class ActionCreateRequestBody(base.SenlinObject):
    fields = {
        'name': fields.NameField(),
        'cluster_id': fields.StringField(),
        'action': fields.StringField(),
        'inputs': fields.JsonField(nullable=True, default={}),
    }


@base.SenlinObjectRegistry.register
class ActionCreateRequest(base.SenlinObject):

    fields = {
        'action': fields.ObjectField('ActionCreateRequestBody')
    }


@base.SenlinObjectRegistry.register
class ActionListRequest(base.SenlinObject):
    action_name_list = list(consts.CLUSTER_ACTION_NAMES)
    action_name_list.extend(list(consts.NODE_ACTION_NAMES))

    fields = {
        'name': fields.ListOfStringsField(nullable=True),
        'action': fields.ListOfEnumField(
            valid_values=action_name_list, nullable=True),
        'target': fields.ListOfStringsField(nullable=True),
        'status': fields.ListOfEnumField(
            valid_values=list(consts.ACTION_STATUSES), nullable=True),
        'limit': fields.NonNegativeIntegerField(nullable=True),
        'marker': fields.UUIDField(nullable=True),
        'sort': fields.SortField(
            valid_keys=list(consts.ACTION_SORT_KEYS), nullable=True),
        'project_safe': fields.FlexibleBooleanField(default=True)
    }


@base.SenlinObjectRegistry.register
class ActionGetRequest(base.SenlinObject):

    fields = {
        'identity': fields.StringField(),
    }


@base.SenlinObjectRegistry.register
class ActionDeleteRequest(base.SenlinObject):

    fields = {
        'identity': fields.StringField()
    }
