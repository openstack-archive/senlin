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
    # VERSION 1.0: Initial version
    # VERSION 1.1 Added field 'force'
    VERSION = '1.1'
    VERSION_MAP = {
        '1.8': '1.1',
    }

    fields = {
        'identity': fields.StringField(),
        'force': fields.BooleanField(default=False)
    }

    def obj_make_compatible(self, primitive, target_version):
        super(NodeDeleteRequest, self).obj_make_compatible(
            primitive, target_version)
        target_version = versionutils.convert_version_to_tuple(target_version)
        if target_version < (1, 1):
            if 'force' in primitive['senlin_object.data']:
                del primitive['senlin_object.data']['force']


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


@base.SenlinObjectRegistry.register
class NodeAdoptRequest(base.SenlinObject):

    fields = {
        'identity': fields.StringField(),
        'type': fields.StringField(),
        'name': fields.NameField(nullable=True),
        'role': fields.StringField(nullable=True),
        'metadata': fields.JsonField(nullable=True, default={}),
        'overrides': fields.JsonField(nullable=True),
        'snapshot': fields.BooleanField(nullable=True, default=False)
    }


@base.SenlinObjectRegistry.register
class NodeAdoptPreviewRequest(base.SenlinObject):

    fields = {
        'identity': fields.StringField(),
        'type': fields.StringField(),
        'overrides': fields.JsonField(nullable=True),
        'snapshot': fields.BooleanField(nullable=True, default=False)
    }
