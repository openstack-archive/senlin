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

from webob import exc

from oslo_log import log as logging

from senlin.api.openstack.v1 import util
from senlin.common import consts
from senlin.common import serializers
from senlin.common import utils
from senlin.common import wsgi
from senlin.rpc import client as rpc_client

LOG = logging.getLogger(__name__)


class EventController(object):
    '''WSGI controller for events in Senlin v1 API.'''

    # Define request scope (must match what is in policy.json)
    REQUEST_SCOPE = 'events'

    def __init__(self, options):
        self.options = options
        self.rpc_client = rpc_client.EngineClient()

    def default(self, req, **args):
        raise exc.HTTPNotFound()

    @util.policy_enforce
    def index(self, req):
        filter_whitelist = {
            'obj_name': 'mixed',
            'obj_type': 'mixed',
            'obj_id': 'mixed',
            'cluster_id': 'mixed',
            'action': 'mixed',
        }
        param_whitelist = {
            'limit': 'single',
            'marker': 'single',
            'sort_dir': 'single',
            'sort_keys': 'multi',
            'global_project': 'single',
            'show_deleted': 'single',
        }
        params = util.get_allowed_params(req.params, param_whitelist)
        filters = util.get_allowed_params(req.params, filter_whitelist)

        key = consts.PARAM_SHOW_DELETED
        if key in params:
            params[key] = utils.parse_bool_param(key, params[key])

        key = consts.PARAM_GLOBAL_PROJECT
        if key in params:
            global_project = utils.parse_bool_param(key, params[key])
            params.pop(key)
            params['project_safe'] = not global_project

        key = consts.PARAM_LIMIT
        if key in params:
            params[key] = utils.parse_int_param(key, params[key])

        if not filters:
            filters = None

        events = self.rpc_client.event_list(req.context,
                                            filters=filters,
                                            **params)

        return {'events': events}

    @util.policy_enforce
    def get(self, req, event_id):
        event = self.rpc_client.event_get(req.context, event_id)
        return {'event': event}


def create_resource(options):
    '''Events factory method.'''

    return wsgi.Resource(EventController(options),
                         wsgi.JSONRequestDeserializer(),
                         serializers.JSONResponseSerializer())
