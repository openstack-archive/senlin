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
from oslo_context import context as oslo_context
from oslo_log import log as logging

from senlin.common import context as senlin_context
from senlin.common import exception
from senlin.drivers import base as driver_base
from senlin.objects import credential as co

LOG = logging.getLogger(__name__)

CONF = cfg.CONF


class Message(object):
    """Zaqar message type of notification."""
    def __init__(self, queue_name, **kwargs):
        self.user = kwargs.get('user', '')
        self.project = kwargs.get('project', '')
        self.domain = kwargs.get('domain', '')

        self.queue_name = queue_name

        self._zaqarclient = None
        self._keystoneclient = None

    def zaqar(self):
        if self._zaqarclient is not None:
            return self._zaqarclient
        params = self._build_conn_params(self.user, self.project)
        self._zaqarclient = driver_base.SenlinDriver().message(params)
        return self._zaqarclient

    def _build_conn_params(self, user, project):
        """Build connection params for specific user and project.

        :param user: The ID of the user for which a trust will be used.
        :param project: The ID of the project for which a trust will be used.
        :returns: A dict containing the required parameters for connection
                  creation.
        """
        service_creds = senlin_context.get_service_credentials()
        params = {
            'username': service_creds.get('username'),
            'password': service_creds.get('password'),
            'auth_url': service_creds.get('auth_url'),
            'user_domain_name': service_creds.get('user_domain_name')
        }

        cred = co.Credential.get(oslo_context.get_current(), user, project)
        if cred is None:
            raise exception.TrustNotFound(trustor=user)
        params['trust_id'] = cred.cred['openstack']['trust']

        return params

    def post_lifecycle_hook_message(self, lifecycle_action_token,
                                    node_id, lifecycle_transition_type):
        try:
            message_list = [{
                "ttl": CONF.notification.ttl,
                "body": {
                    "lifecycle_action_token": lifecycle_action_token,
                    "node_id": node_id,
                    "lifecycle_transition_type": lifecycle_transition_type
                }
            }]

            if not self.zaqar().queue_exists(self.queue_name):
                kwargs = {
                    "_max_messages_post_size":
                        CONF.notification.max_message_size,
                    "description": "Senlin lifecycle hook notification",
                    "name": self.queue_name
                }
                self.zaqar().queue_create(**kwargs)

            return self.zaqar().message_post(self.queue_name, message_list)
        except exception.InternalError as ex:
            raise exception.EResourceCreation(type='queue', message=ex.message)
