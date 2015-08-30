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
Policy endpoint for Senlin v1 ReST API.
"""

from webob import exc

from senlin.api.openstack.v1 import util
from senlin.common import consts
from senlin.common.i18n import _
from senlin.common import serializers
from senlin.common import utils
from senlin.common import wsgi
from senlin.rpc import client as rpc_client


class PolicyData(object):
    '''The data accompanying a POST/PUT request to create/update a policy.'''
    def __init__(self, data):
        self.data = data

    def name(self):
        if consts.POLICY_NAME not in self.data:
            raise exc.HTTPBadRequest(_("No policy name specified"))
        return self.data[consts.POLICY_NAME]

    def spec(self):
        if consts.POLICY_SPEC not in self.data:
            raise exc.HTTPBadRequest(_("No policy spec provided"))
        return self.data[consts.POLICY_SPEC]

    def level(self):
        return self.data.get(consts.POLICY_LEVEL, None)

    def cooldown(self):
        return self.data.get(consts.POLICY_COOLDOWN, None)


class PolicyController(object):
    '''WSGI controller for policy resource in Senlin v1 API.'''

    # Define request scope (must match what is in policy.json)
    REQUEST_SCOPE = 'policies'

    def __init__(self, options):
        self.options = options
        self.rpc_client = rpc_client.EngineClient()

    def default(self, req, **args):
        raise exc.HTTPNotFound()

    @util.policy_enforce
    def index(self, req):
        filter_whitelist = {
            'name': 'mixed',
            'type': 'mixed',
            'level': 'mixed',
            'cooldown': 'mixed',
            'created_time': 'single',
            'updated_time': 'single',
            'deleted_time': 'single',
        }
        param_whitelist = {
            'limit': 'single',
            'marker': 'single',
            'sort_dir': 'single',
            'sort_keys': 'multi',
            'show_deleted': 'single',
        }
        params = util.get_allowed_params(req.params, param_whitelist)
        filters = util.get_allowed_params(req.params, filter_whitelist)

        key = consts.PARAM_SHOW_DELETED
        if key in params:
            params[key] = utils.parse_bool_param(key, params[key])

        key = consts.PARAM_LIMIT
        if key in params:
            params[key] = utils.parse_int_param(key, params[key])

        if not filters:
            filters = None

        policies = self.rpc_client.policy_list(req.context,
                                               filters=filters,
                                               **params)

        return {'policies': policies}

    @util.policy_enforce
    def create(self, req, body):
        policy_data = body.get('policy', None)
        if policy_data is None:
            raise exc.HTTPBadRequest(_("Malformed request data, missing "
                                       "'policy' key in request body."))

        data = PolicyData(policy_data)
        result = self.rpc_client.policy_create(req.context, data.name(),
                                               data.spec(), data.level(),
                                               data.cooldown())

        return {'policy': result}

    @util.policy_enforce
    def get(self, req, policy_id):
        policy = self.rpc_client.policy_get(req.context, policy_id)
        return {'policy': policy}

    @util.policy_enforce
    def update(self, req, policy_id, body):
        policy_data = body.get('policy', None)
        if policy_data is None:
            raise exc.HTTPBadRequest(_("Malformed request data, missing "
                                       "'policy' key in request body."))

        spec = policy_data.get(consts.POLICY_SPEC)
        if spec is not None:
            msg = _("Updating the spec of a policy is not supported because "
                    "it may cause state conflicts in engine.")
            raise exc.HTTPBadRequest(msg)

        name = policy_data.get(consts.POLICY_NAME, None)

        level = policy_data.get(consts.POLICY_LEVEL, None)
        if level is not None:
            level = utils.parse_int_param(consts.POLICY_LEVEL, level)

        cooldown = policy_data.get(consts.POLICY_COOLDOWN, None)
        if cooldown is not None:
            cooldown = utils.parse_int_param(consts.POLICY_COOLDOWN, cooldown)

        policy = self.rpc_client.policy_update(req.context, policy_id, name,
                                               level, cooldown)

        return {'policy': policy}

    @util.policy_enforce
    def delete(self, req, policy_id):
        self.rpc_client.policy_delete(req.context, policy_id, cast=False)

        raise exc.HTTPNoContent()


def create_resource(options):
    '''Policies resource factory method.'''

    return wsgi.Resource(PolicyController(options),
                         wsgi.JSONRequestDeserializer(),
                         serializers.JSONResponseSerializer())
