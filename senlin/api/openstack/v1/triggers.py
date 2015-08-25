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
Trigger resource for Senlin v1 ReST API.
"""

from webob import exc

from senlin.api.openstack.v1 import util
from senlin.common import consts
from senlin.common.i18n import _
from senlin.common import serializers
from senlin.common import utils
from senlin.common import wsgi
from senlin.rpc import client as rpc_client


class TriggerData(object):
    """The body for a POST/PATCH request to create/update a trigger."""

    def __init__(self, data):
        self.name = data.get(consts.TRIGGER_NAME, None)
        self.spec = data.get(consts.TRIGGER_SPEC, None)
        self.desc = data.get(consts.TRIGGER_DESCRIPTION, None)
        self.enabled = data.get(consts.TRIGGER_ENABLED, None)
        self.state = data.get(consts.TRIGGER_STATE, None)
        self.severity = data.get(consts.TRIGGER_SEVERITY, None)

    def validate(self):
        if self.name is None:
            raise exc.HTTPBadRequest(_("No trigger name specified."))

        if self.spec is None:
            raise exc.HTTPBadRequest(_("No trigger spec provided."))

        if self.enabled is not None:
            self.enabled = utils.parse_bool_param(consts.TRIGGER_ENABLED,
                                                  self.enabled)


class TriggerController(object):
    """WSGI controller for trigger resource in Senlin v1 API."""

    # Define request scope (must match what is in policy.json)
    REQUEST_SCOPE = 'triggers'

    def __init__(self, options):
        self.options = options
        self.rpc_client = rpc_client.EngineClient()

    def default(self, req, **args):
        raise exc.HTTPNotFound()

    @util.policy_enforce
    def index(self, req):
        filter_whitelist = {
            consts.TRIGGER_NAME: 'mixed',
            consts.TRIGGER_TYPE: 'mixed',
            consts.TRIGGER_STATE: 'mixed',
            consts.TRIGGER_ENABLED: 'mixed',
            consts.TRIGGER_SEVERITY: 'mixed',
        }
        param_whitelist = {
            consts.PARAM_LIMIT: 'single',
            consts.PARAM_MARKER: 'single',
            consts.PARAM_SORT_DIR: 'single',
            consts.PARAM_SORT_KEYS: 'multi',
            consts.PARAM_SHOW_DELETED: 'single',
            consts.PARAM_GLOBAL_PROJECT: 'single',
        }
        params = util.get_allowed_params(req.params, param_whitelist)
        filters = util.get_allowed_params(req.params, filter_whitelist)

        key = consts.PARAM_SHOW_DELETED
        if key in params:
            params[key] = utils.parse_bool_param(key, params[key])

        key = consts.PARAM_LIMIT
        if key in params:
            params[key] = utils.parse_int_param(key, params[key])

        key = consts.PARAM_SORT_DIR
        if key in params:
            sort_dir = params[key].lower()
            if sort_dir not in ('asc', 'desc'):
                raise exc.HTTPBadRequest(_("Sorting direction (sort_dir) must "
                                           "be either 'asc' or 'desc'."))

        key = consts.PARAM_GLOBAL_PROJECT
        if key in params:
            project_safe = not utils.parse_bool_param(key, params[key])
            del params[key]
            params['project_safe'] = project_safe

        if not filters:
            filters = None

        triggers = self.rpc_client.trigger_list(req.context,
                                                filters=filters,
                                                **params)

        return {'triggers': triggers}

    @util.policy_enforce
    def create(self, req, body):
        trigger_data = body.get('trigger')
        if trigger_data is None:
            raise exc.HTTPBadRequest(_("Malformed request data, missing "
                                       "'trigger' key in request body."))

        data = TriggerData(trigger_data)
        data.validate()
        trigger = self.rpc_client.trigger_create(
            req.context, data.name, data.spec,
            description=data.desc, enabled=data.enabled,
            state=data.state, severity=data.severity)

        return {'trigger': trigger}

    @util.policy_enforce
    def get(self, req, trigger_id):
        trigger = self.rpc_client.trigger_get(req.context, trigger_id)

        return {'trigger': trigger}

    @util.policy_enforce
    def delete(self, req, trigger_id):
        self.rpc_client.trigger_delete(req.context, trigger_id, cast=False)

        raise exc.HTTPNoContent()


def create_resource(options):
    """Trigger resource factory method."""

    return wsgi.Resource(TriggerController(options),
                         wsgi.JSONRequestDeserializer(),
                         serializers.JSONResponseSerializer())
