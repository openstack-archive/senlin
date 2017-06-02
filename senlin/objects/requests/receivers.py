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

from oslo_utils import versionutils

from senlin.common import consts
from senlin.objects import base
from senlin.objects import fields


@base.SenlinObjectRegistry.register
class ReceiverCreateRequestBody(base.SenlinObject):

    fields = {
        'name': fields.NameField(),
        'type': fields.ReceiverTypeField(),
        'cluster_id': fields.StringField(nullable=True),
        'action': fields.ClusterActionNameField(nullable=True),
        'actor': fields.JsonField(nullable=True, default={}),
        'params': fields.JsonField(nullable=True, default={})
    }


@base.SenlinObjectRegistry.register
class ReceiverCreateRequest(base.SenlinObject):

    fields = {
        'receiver': fields.ObjectField('ReceiverCreateRequestBody')
    }


@base.SenlinObjectRegistry.register
class ReceiverListRequest(base.SenlinObject):

    # VERSION 1.0: Initial version
    # VERSION 1.1: Add field 'user'
    VERSION = '1.1'
    VERSION_MAP = {
        '1.4': '1.1',
    }

    fields = {
        'name': fields.ListOfStringsField(nullable=True),
        'type': fields.ListOfEnumField(
            valid_values=list(consts.RECEIVER_TYPES), nullable=True),
        'action': fields.ListOfEnumField(
            valid_values=list(consts.CLUSTER_ACTION_NAMES), nullable=True),
        'cluster_id': fields.ListOfStringsField(nullable=True),
        'limit': fields.NonNegativeIntegerField(nullable=True),
        'marker': fields.UUIDField(nullable=True),
        'sort': fields.SortField(
            valid_keys=list(consts.RECEIVER_SORT_KEYS), nullable=True),
        'project_safe': fields.FlexibleBooleanField(default=True),
        'user': fields.ListOfStringsField(nullable=True),
    }

    def obj_make_compatible(self, primitive, target_version):
        super(ReceiverListRequest, self).obj_make_compatible(
            primitive, target_version)
        target_version = versionutils.convert_version_to_tuple(
            target_version)
        if target_version < (1, 1):
            if 'user' in primitive['senlin_object.data']:
                del primitive['senlin_object.data']['user']


@base.SenlinObjectRegistry.register
class ReceiverGetRequest(base.SenlinObject):

    fields = {
        'identity': fields.StringField()
    }


@base.SenlinObjectRegistry.register
class ReceiverUpdateRequest(base.SenlinObject):

    fields = {
        'identity': fields.StringField(),
        'name': fields.NameField(nullable=True),
        'action': fields.ClusterActionNameField(nullable=True),
        'params': fields.JsonField(nullable=True, default={})
    }


@base.SenlinObjectRegistry.register
class ReceiverDeleteRequest(base.SenlinObject):

    fields = {
        'identity': fields.StringField()
    }


@base.SenlinObjectRegistry.register
class ReceiverNotifyRequest(base.SenlinObject):

    fields = {
        'identity': fields.StringField()
    }
