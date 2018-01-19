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

from oslo_config import cfg
from oslo_utils import versionutils

from senlin.common import consts
from senlin.objects import base
from senlin.objects import fields

CONF = cfg.CONF
CONF.import_opt('default_action_timeout', 'senlin.common.config')


@base.SenlinObjectRegistry.register
class ClusterListRequest(base.SenlinObject):

    fields = {
        'name': fields.ListOfStringsField(nullable=True),
        'status': fields.ListOfEnumField(
            valid_values=list(consts.CLUSTER_STATUSES), nullable=True),
        'limit': fields.NonNegativeIntegerField(nullable=True),
        'marker': fields.UUIDField(nullable=True),
        'sort': fields.SortField(
            valid_keys=list(consts.CLUSTER_SORT_KEYS), nullable=True),
        'project_safe': fields.FlexibleBooleanField(default=True),
    }


@base.SenlinObjectRegistry.register
class ClusterCreateRequestBody(base.SenlinObject):

    # VERSION 1.0: initial version
    # VERSION 1.1: added field 'config'
    VERSION = '1.1'
    VERSION_MAP = {
        '1.7': '1.1',
    }

    fields = {
        'name': fields.NameField(),
        'profile_id': fields.StringField(),
        'min_size': fields.CapacityField(
            nullable=True, minimum=0,
            default=consts.CLUSTER_DEFAULT_MIN_SIZE),
        'max_size': fields.CapacityField(
            nullable=True, minimum=-1,
            default=consts.CLUSTER_DEFAULT_MAX_SIZE),
        'desired_capacity': fields.CapacityField(
            nullable=True, minimum=0),
        'metadata': fields.JsonField(nullable=True, default={}),
        'timeout': fields.NonNegativeIntegerField(
            nullable=True, default=CONF.default_action_timeout),
        'config': fields.JsonField(nullable=True, default={}),
    }

    def obj_make_compatible(self, primitive, target_version):
        super(ClusterCreateRequest, self).obj_make_compatible(
            primitive, target_version)
        target_version = versionutils.convert_version_to_tuple(target_version)
        if target_version < (1, 1):
            if 'config' in primitive['senlin_object.data']:
                del primitive['senlin_object.data']['config']


@base.SenlinObjectRegistry.register
class ClusterCreateRequest(base.SenlinObject):

    fields = {
        'cluster': fields.ObjectField('ClusterCreateRequestBody')
    }


@base.SenlinObjectRegistry.register
class ClusterGetRequest(base.SenlinObject):

    fields = {
        'identity': fields.StringField()
    }


@base.SenlinObjectRegistry.register
class ClusterUpdateRequest(base.SenlinObject):

    # VERSION 1.0: initial version
    # VERSION 1.1: added field 'profile_only'
    # VERSION 1.2: added field 'config'
    VERSION = '1.2'
    VERSION_MAP = {
        '1.6': '1.1',
        '1.7': '1.2',
    }

    fields = {
        'identity': fields.StringField(),
        'name': fields.NameField(nullable=True),
        'profile_id': fields.StringField(nullable=True),
        'metadata': fields.JsonField(nullable=True),
        'timeout': fields.NonNegativeIntegerField(nullable=True),
        'profile_only': fields.BooleanField(nullable=True),
        'config': fields.JsonField(nullable=True),
    }

    def obj_make_compatible(self, primitive, target_version):
        super(ClusterUpdateRequest, self).obj_make_compatible(
            primitive, target_version)
        target_version = versionutils.convert_version_to_tuple(target_version)
        if target_version < (1, 1):
            if 'profile_only' in primitive['senlin_object.data']:
                del primitive['senlin_object.data']['profile_only']
        if target_version < (1, 2):
            if 'config' in primitive['senlin_object.data']:
                del primitive['senlin_object.data']['config']


@base.SenlinObjectRegistry.register
class ClusterAddNodesRequest(base.SenlinObject):

    fields = {
        'identity': fields.StringField(),
        'nodes': fields.IdentityListField(min_items=1)
    }


@base.SenlinObjectRegistry.register
class ClusterDelNodesRequest(base.SenlinObject):

    # VERSION 1.0: Initial version
    # VERSION 1.1: Add field 'destroy_after_deletion'
    VERSION = '1.1'
    VERSION_MAP = {
        '1.4': '1.1',
    }

    fields = {
        'identity': fields.StringField(),
        'nodes': fields.IdentityListField(min_items=1),
        'destroy_after_deletion': fields.BooleanField(nullable=True,
                                                      default=False)
    }

    def obj_make_compatible(self, primitive, target_version):
        super(ClusterDelNodesRequest, self).obj_make_compatible(
            primitive, target_version)
        target_version = versionutils.convert_version_to_tuple(target_version)
        if target_version < (1, 1):
            if 'destroy_after_deletion' in primitive['senlin_object.data']:
                del primitive['senlin_object.data']['destroy_after_deletion']


@base.SenlinObjectRegistry.register
class ClusterReplaceNodesRequest(base.SenlinObject):

    fields = {
        'identity': fields.StringField(),
        'nodes': fields.NodeReplaceMapField(),
    }


@base.SenlinObjectRegistry.register
class ClusterResizeRequest(base.SenlinObject):

    fields = {
        'identity': fields.StringField(),
        'adjustment_type': fields.AdjustmentTypeField(nullable=True),
        'number': fields.FloatField(nullable=True),
        'min_size': fields.CapacityField(nullable=True, minimum=0),
        'max_size': fields.CapacityField(nullable=True, minimum=-1),
        'min_step': fields.NonNegativeIntegerField(nullable=True),
        'strict': fields.BooleanField(nullable=True, default=True),
    }


@base.SenlinObjectRegistry.register
class ClusterScaleInRequest(base.SenlinObject):

    fields = {
        'identity': fields.StringField(),
        'count': fields.NonNegativeIntegerField(nullable=True),
    }


@base.SenlinObjectRegistry.register
class ClusterScaleOutRequest(base.SenlinObject):

    fields = {
        'identity': fields.StringField(),
        'count': fields.NonNegativeIntegerField(nullable=True),
    }


@base.SenlinObjectRegistry.register
class ClusterAttachPolicyRequest(base.SenlinObject):

    fields = {
        'identity': fields.StringField(),
        'policy_id': fields.StringField(),
        'enabled': fields.BooleanField(nullable=True, default=True),
    }


@base.SenlinObjectRegistry.register
class ClusterUpdatePolicyRequest(base.SenlinObject):

    fields = {
        'identity': fields.StringField(),
        'policy_id': fields.StringField(),
        'enabled': fields.BooleanField(nullable=True, default=True),
    }


@base.SenlinObjectRegistry.register
class ClusterDetachPolicyRequest(base.SenlinObject):

    fields = {
        'identity': fields.StringField(),
        'policy_id': fields.StringField(),
    }


@base.SenlinObjectRegistry.register
class ClusterCheckRequest(base.SenlinObject):

    fields = {
        'identity': fields.StringField(),
        'params': fields.JsonField(nullable=True),
    }


@base.SenlinObjectRegistry.register
class ClusterRecoverRequest(base.SenlinObject):

    fields = {
        'identity': fields.StringField(),
        'params': fields.JsonField(nullable=True),
    }


@base.SenlinObjectRegistry.register
class ClusterCollectRequest(base.SenlinObject):

    fields = {
        'identity': fields.StringField(),
        'path': fields.StringField(),
    }


@base.SenlinObjectRegistry.register
class ClusterOperationRequest(base.SenlinObject):

    fields = {
        'identity': fields.StringField(),
        'operation': fields.StringField(),
        'filters': fields.JsonField(nullable=True, default={}),
        'params': fields.JsonField(nullable=True, default={}),
    }


@base.SenlinObjectRegistry.register
class ClusterDeleteRequest(base.SenlinObject):
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
        super(ClusterDeleteRequest, self).obj_make_compatible(
            primitive, target_version)
        target_version = versionutils.convert_version_to_tuple(target_version)
        if target_version < (1, 1):
            if 'force' in primitive['senlin_object.data']:
                del primitive['senlin_object.data']['force']


@base.SenlinObjectRegistry.register
class ClusterCompleteLifecycleRequest(base.SenlinObject):

    fields = {
        'identity': fields.StringField(),
        'lifecycle_action_token': fields.StringField(),
    }
