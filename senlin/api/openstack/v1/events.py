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


class EventController(wsgi.Controller):
    """WSGI controller for events in Senlin v1 API."""

    # Define request scope
    # (must match what is in policy file and policies in code.)
    REQUEST_SCOPE = 'events'

    @util.policy_enforce
    def index(self, req):
        whitelist = {
            consts.EVENT_OBJ_NAME: 'mixed',
            consts.EVENT_OBJ_TYPE: 'mixed',
            consts.EVENT_OBJ_ID: 'mixed',
            consts.EVENT_CLUSTER_ID: 'mixed',
            consts.EVENT_ACTION: 'mixed',
            consts.EVENT_LEVEL: 'mixed',
            consts.PARAM_LIMIT: 'single',
            consts.PARAM_MARKER: 'single',
            consts.PARAM_SORT: 'single',
            consts.PARAM_GLOBAL_PROJECT: 'single',
        }

        for key in req.params.keys():
            if key not in whitelist.keys():
                raise exc.HTTPBadRequest(_('Invalid parameter %s') % key)
        params = util.get_allowed_params(req.params, whitelist)

        project_safe = not util.parse_bool_param(
            consts.PARAM_GLOBAL_PROJECT,
            params.pop(consts.PARAM_GLOBAL_PROJECT, False))
        params['project_safe'] = project_safe

        obj = util.parse_request('EventListRequest', req, params)
        events = self.rpc_client.call(req.context, "event_list", obj)

        return {'events': events}

    @util.policy_enforce
    def get(self, req, event_id):

        obj = util.parse_request('EventGetRequest', req,
                                 {'identity': event_id})
        event = self.rpc_client.call(req.context, 'event_get', obj)

        return {'event': event}
