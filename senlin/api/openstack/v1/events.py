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
Event endpoint for Senlin v1 ReST API.
"""
from webob import exc

from senlin.api.common import util
from senlin.api.common import wsgi
from senlin.common import consts
from senlin.common.i18n import _
from senlin.common import utils


class EventController(wsgi.Controller):
    """WSGI controller for events in Senlin v1 API."""

    # Define request scope (must match what is in policy.json)
    REQUEST_SCOPE = 'events'

    @util.policy_enforce
    def index(self, req):
        filter_whitelist = {
            consts.EVENT_OBJ_NAME: 'mixed',
            consts.EVENT_OBJ_TYPE: 'mixed',
            consts.EVENT_OBJ_ID: 'mixed',
            consts.EVENT_CLUSTER_ID: 'mixed',
            consts.EVENT_ACTION: 'mixed',
            consts.EVENT_LEVEL: 'mixed',
        }
        param_whitelist = {
            consts.PARAM_LIMIT: 'single',
            consts.PARAM_MARKER: 'single',
            consts.PARAM_SORT: 'single',
            consts.PARAM_GLOBAL_PROJECT: 'single',
        }
        for key in req.params.keys():
            if (key not in param_whitelist.keys() and key not in
                    filter_whitelist.keys()):
                raise exc.HTTPBadRequest(_('Invalid parameter %s') % key)
        params = util.get_allowed_params(req.params, param_whitelist)
        filters = util.get_allowed_params(req.params, filter_whitelist)

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

        events = self.rpc_client.event_list(req.context, filters=filters,
                                            **params)

        return {'events': events}

    @util.policy_enforce
    def get(self, req, event_id):
        event = self.rpc_client.event_get(req.context, event_id)
        return {'event': event}
