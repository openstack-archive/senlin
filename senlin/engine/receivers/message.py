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

import socket

from keystoneauth1 import loading as ks_loading
from oslo_config import cfg
from oslo_log import log as logging

from senlin.common import exception as exc
from senlin.common.i18n import _
from senlin.drivers import base as driver_base
from senlin.engine.receivers import base

LOG = logging.getLogger(__name__)

CONF = cfg.CONF


class Message(base.Receiver):
    """Zaqar message type of receivers."""
    def __init__(self, rtype, cluster_id, action, **kwargs):
        super(Message, self).__init__(rtype, cluster_id, action, **kwargs)
        self._zaqarclient = None
        self._keystoneclient = None

    def zaqar(self):
        if self._zaqarclient is not None:
            return self._zaqarclient
        params = self._build_conn_params(self.user, self.project)
        self._zaqarclient = driver_base.SenlinDriver().message(params)
        return self._zaqarclient

    def keystone(self):
        if self._keystoneclient is not None:
            return self._keystoneclient
        params = self._build_conn_params(self.user, self.project)
        self._keystoneclient = driver_base.SenlinDriver().identity(params)
        return self._keystoneclient

    def _generate_subscriber_url(self):
        # TODO(Yanyanhu): Define dedicated configuration options
        # for subscriber base url building?
        host = CONF.webhook.host
        port = CONF.webhook.port
        base = None

        if not host:
            # Try to get base url by querying senlin endpoint if host
            # is not provided in configuration file
            base = self._get_base_url()
            if not base:
                host = socket.gethostname()
                msg = _('Webhook host is not specified in configuration '
                        'file and Senlin service endpoint can not be found,'
                        'using local hostname (%(host)s) for subscriber url.'
                        ) % {'host': host}
                LOG.warning(msg)

        if not base:
            base = "http://%(h)s:%(p)s/v1" % {'h': host, 'p': port}
        sub_url = "/receivers/%(id)s/notify" % {'id': self.id}

        return "".join(["trust+", base, sub_url])

    def _build_trust(self):
        # Get zaqar trustee user ID for trust building
        auth = ks_loading.load_auth_from_conf_options(CONF, 'zaqar')
        session = ks_loading.load_session_from_conf_options(CONF, 'zaqar')
        zaqar_trustee_user_id = session.get_user_id(auth=auth)
        try:
            trust = self.keystone().trust_get_by_trustor(self.user,
                                                         zaqar_trustee_user_id,
                                                         self.project)
            if not trust:
                # Create a trust if no existing one found
                # TODO(Yanyanhu): get user roles list for trust creation
                trust = self.keystone().trust_create(self.user,
                                                     zaqar_trustee_user_id,
                                                     self.project, ['admin'])
        except exc.InternalError as ex:
            msg = _('Can not build trust between user %(user)s and zaqar '
                    'service user %(zaqar)s for receiver %(receiver)s.'
                    ) % {'user': self.user, 'zaqar': zaqar_trustee_user_id,
                         'receiver': self.id}
            LOG.error(msg)
            raise exc.EResourceCreation(type='trust',
                                        message=ex.message)
        return trust.id

    def _create_queue(self):
        # TODO(YanyanHu): make queue attributes configurable.
        queue_name = "senlin-receiver-%s" % self.id
        kwargs = {
            "_max_messages_post_size": 262144,
            "_default_message_ttl": 3600,
            "description": "Queue for Senlin receiver.",
            "name": queue_name
        }
        try:
            self.zaqar().queue_create(**kwargs)
        except exc.InternalError as ex:
            raise exc.EResourceCreation(type='queue', message=ex.message)

        return queue_name

    def _create_subscription(self, queue_name):
        subscriber = self._generate_subscriber_url()
        trust_id = self._build_trust()

        # TODO(Yanyanhu): make subscription attributes configurable.
        kwargs = {
            "ttl": 3600,
            "subscriber": subscriber,
            "options": {
                "from": "senlin and zaqar",
                "subject": "hello, senlin",
                "trust_id": trust_id
            }
        }
        try:
            subscription = self.zaqar().subscription_create(queue_name,
                                                            **kwargs)
        except exc.InternalError as ex:
            raise exc.EResourceCreation(type='subscription',
                                        message=ex.message)
        return subscription

    def initialize_channel(self):
        queue_name = self._create_queue()
        subscription = self._create_subscription(queue_name)

        self.channel = {
            'queue_name': queue_name,
            'subscription': subscription.subscription_id
        }
        return self.channel

    def release_channel(self):
        queue_name = self.channel['queue_name']
        subscription = self.channel['subscription']

        # Delete subscription on zaqar queue
        try:
            self.zaqar().subscription_delete(queue_name, subscription)
        except exc.InternalError as ex:
            raise exc.EResourceDeletion(type='subscription',
                                        id='subscription',
                                        message=ex.message)
        # Delete zaqar queue
        try:
            self.zaqar().queue_delete(queue_name)
        except exc.InternalError as ex:
            raise exc.EResourceDeletion(type='queue',
                                        id='queue_name',
                                        message=ex.message)

    def to_dict(self):
        message = super(Message, self).to_dict()
        # Pop subscription from channel info since it
        # should be invisible for user.
        message['channel'].pop('subscription')

        return message
