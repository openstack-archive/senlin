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

"""
Policy Engine For Senlin
"""

# from oslo_concurrency import lockutils
from oslo_config import cfg
from oslo_policy import policy

from senlin.common import exception
from senlin.common import policies

POLICY_ENFORCER = None
CONF = cfg.CONF


# @lockutils.synchronized('policy_enforcer', 'senlin-')
def _get_enforcer(policy_file=None, rules=None, default_rule=None):

    global POLICY_ENFORCER

    if POLICY_ENFORCER is None:
        POLICY_ENFORCER = policy.Enforcer(CONF,
                                          policy_file=policy_file,
                                          rules=rules,
                                          default_rule=default_rule)
        POLICY_ENFORCER.register_defaults(policies.list_rules())
    return POLICY_ENFORCER


def enforce(context, rule, target, do_raise=True, *args, **kwargs):

    enforcer = _get_enforcer()
    credentials = context.to_dict()
    target = target or {}
    if do_raise:
        kwargs.update(exc=exception.Forbidden)

    return enforcer.enforce(rule, target, credentials, do_raise,
                            *args, **kwargs)
