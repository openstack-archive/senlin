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

from webob import exc

from oslo_log import log as logging

from senlin.api.openstack.v1 import util
from senlin.common import consts
from senlin.common.i18n import _
from senlin.common import serializers
from senlin.common import utils
from senlin.common import wsgi
from senlin.rpc import client as rpc_client

LOG = logging.getLogger(__name__)


class ActionData(object):
    '''All required data fields for an action.'''

    PARAMS = (consts.ACTION_NAME, consts.ACTION_TARGET, consts.ACTION_ACTION)

    def __init__(self, data):
        self.data = data

    def name(self):
        if consts.ACTION_NAME not in self.data:
            raise exc.HTTPBadRequest(_("No action name specified"))
        return self.data[consts.ACTION_NAME]

    def target(self):
        if consts.ACTION_TARGET not in self.data:
            raise exc.HTTPBadRequest(_("No target specified"))
        return self.data[consts.ACTION_TARGET]

    def action(self):
        if consts.ACTION_ACTION not in self.data:
            raise exc.HTTPBadRequest(_("No action specified"))
        return self.data[consts.ACTION_ACTION]

    def params(self):
        data = self.data.items()
        return dict((k, v) for k, v in data if k not in self.PARAMS)


class ActionController(object):
    '''WSGI controller for Actions in Senlin v1 API.'''

    # Define request scope (must match what is in policy.json)
    REQUEST_SCOPE = 'actions'

    def __init__(self, options):
        self.options = options
        self.rpc_client = rpc_client.EngineClient()

    def default(self, req, **args):
        raise exc.HTTPNotFound()

    @util.policy_enforce
    def index(self, req):
        filter_whitelist = {
            'name': 'mixed',
            'target': 'mixed',
            'action': 'mixed',
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

        key = consts.PARAM_LIMIT
        if key in params:
            params[key] = utils.parse_int_param(key, params[key])

        key = consts.PARAM_SHOW_DELETED
        if key in params:
            params[key] = utils.parse_bool_param(key, params[key])

        if not filters:
            filters = None

        actions = self.rpc_client.action_list(req.context,
                                              filters=filters,
                                              **params)

        return {'actions': actions}

    @util.policy_enforce
    def create(self, req, body):
        data = ActionData(body)
        result = self.rpc_client.action_create(req.context,
                                               data.name(),
                                               data.target(),
                                               data.action(),
                                               data.params())

        return result

    @util.policy_enforce
    def get(self, req, action_id):
        action = self.rpc_client.action_get(req.context, action_id)
        if not action:
            raise exc.HTTPNotFound()

        return {'action': action}


def create_resource(options):
    '''Actions factory method.'''

    return wsgi.Resource(ActionController(options),
                         wsgi.JSONRequestDeserializer(),
                         serializers.JSONResponseSerializer())
