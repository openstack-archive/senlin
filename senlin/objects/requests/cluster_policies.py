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
class ClusterPolicyListRequest(base.SenlinObject):

    fields = {
        'identity': fields.StringField(),
        'policy_name': fields.NameField(nullable=True),
        'policy_type': fields.StringField(nullable=True),
        'enabled': fields.BooleanField(nullable=True),
        'sort': fields.SortField(
            valid_keys=list(consts.CLUSTER_POLICY_SORT_KEYS), nullable=True)
    }


@base.SenlinObjectRegistry.register
class ClusterPolicyGetRequest(base.SenlinObject):

    fields = {
        'identity': fields.StringField(),
        'policy_id': fields.StringField(),
    }
