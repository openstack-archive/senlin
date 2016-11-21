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
class EventListRequest(base.SenlinObject):

    action_name_list = list(consts.CLUSTER_ACTION_NAMES)
    action_name_list.extend(list(consts.NODE_ACTION_NAMES))

    fields = {
        'oid': fields.ListOfStringsField(nullable=True),
        'oname': fields.ListOfStringsField(nullable=True),
        'otype': fields.ListOfStringsField(nullable=True),
        'action': fields.ListOfEnumField(
            valid_values=action_name_list, nullable=True),
        'cluster_id': fields.ListOfStringsField(nullable=True),
        'level': fields.ListOfEnumField(
            valid_values=list(consts.EVENT_LEVELS.keys()), nullable=True),
        'limit': fields.NonNegativeIntegerField(nullable=True),
        'marker': fields.UUIDField(nullable=True),
        'sort': fields.SortField(
            valid_keys=list(consts.EVENT_SORT_KEYS), nullable=True),
        'project_safe': fields.FlexibleBooleanField(default=True)
    }


@base.SenlinObjectRegistry.register
class EventGetRequest(base.SenlinObject):

    fields = {
        'identity': fields.StringField(),
    }
