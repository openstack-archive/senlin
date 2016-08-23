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

    def zaqar(self):
        if self._zaqarclient is not None:
            return self._zaqarclient
        params = self._build_conn_params(self.user, self.project)
        self._zaqarclient = driver_base.SenlinDriver().message(params)
        return self._zaqarclient

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

        # TODO(Yanyanhu): building trust for subscription.
        return "".join(["trust+", base, sub_url])

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

    def _create_subscription(self, queue_name, subscriber):
        # TODO(Yanyanhu): make subscription attributes configurable.
        kwargs = {
            "ttl": 3600,
            "subscriber": subscriber,
            "options": {
                "from": "senlin and zaqar",
                "subject": "hello, senlin"
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
        subscriber = self._generate_subscriber_url()
        subscription = self._create_subscription(queue_name, subscriber)

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
        # Pop subscription from channel info since it should be
        # invisible for user.
        message['channel'].pop('subscription')

        return message
