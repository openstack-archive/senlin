# All Rights Reserved.
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.
#
# Borrowed from Zun


import itertools

from senlin.common.policies import actions
from senlin.common.policies import base
from senlin.common.policies import build_info
from senlin.common.policies import cluster_policies
from senlin.common.policies import clusters
from senlin.common.policies import events
from senlin.common.policies import nodes
from senlin.common.policies import policies
from senlin.common.policies import policy_types
from senlin.common.policies import profile_types
from senlin.common.policies import profiles
from senlin.common.policies import receivers
from senlin.common.policies import services
from senlin.common.policies import webhooks


def list_rules():
    return itertools.chain(
        base.list_rules(),
        build_info.list_rules(),
        profile_types.list_rules(),
        policy_types.list_rules(),
        clusters.list_rules(),
        profiles.list_rules(),
        nodes.list_rules(),
        policies.list_rules(),
        cluster_policies.list_rules(),
        receivers.list_rules(),
        actions.list_rules(),
        events.list_rules(),
        webhooks.list_rules(),
        services.list_rules()
    )
