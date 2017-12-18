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
from oslo_utils import uuidutils

from senlin.common import consts
from senlin.common import exception as exc
from senlin.common.i18n import _
from senlin.drivers import base as driver_base
from senlin.engine.actions import base as action_mod
from senlin.engine import dispatcher
from senlin.engine.receivers import base
from senlin.objects import cluster as cluster_obj

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
        host = CONF.receiver.host
        port = CONF.receiver.port
        base = None

        if not host:
            # Try to get base url by querying senlin endpoint if host
            # is not provided in configuration file
            base = self._get_base_url()
            if not base:
                msg = _('Receiver notification host is not specified in '
                        'configuration file and Senlin service endpoint can '
                        'not be found, using local hostname (%(host)s) for '
                        'subscriber url.') % {'host': host}
                LOG.warning(msg)
                host = socket.gethostname()

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
                roles = self.notifier_roles
                for role in roles:
                    # Remove 'admin' role from delegated roles list
                    # unless it is the only role user has
                    if role == 'admin' and len(roles) > 1:
                        roles.remove(role)
                trust = self.keystone().trust_create(self.user,
                                                     zaqar_trustee_user_id,
                                                     self.project,
                                                     roles)
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
        queue_name = "senlin-receiver-%s" % self.id
        kwargs = {
            "_max_messages_post_size": CONF.receiver.max_message_size,
            "description": "Senlin receiver %s." % self.id,
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

        # FIXME(Yanyanhu): For Zaqar doesn't support to create a
        # subscription that never expires, we specify a very large
        # ttl value which doesn't exceed the max time of python.
        kwargs = {
            "ttl": 2 ** 36,
            "subscriber": subscriber,
            "options": {
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

    def _find_cluster(self, context, identity):
        """Find a cluster with the given identity."""
        if uuidutils.is_uuid_like(identity):
            cluster = cluster_obj.Cluster.get(context, identity)
            if not cluster:
                cluster = cluster_obj.Cluster.get_by_name(context, identity)
        else:
            cluster = cluster_obj.Cluster.get_by_name(context, identity)
            # maybe it is a short form of UUID
            if not cluster:
                cluster = cluster_obj.Cluster.get_by_short_id(context,
                                                              identity)

        if not cluster:
            raise exc.ResourceNotFound(type='cluster', id=identity)

        return cluster

    def _build_action(self, context, message):
        body = message.get('body', None)
        if not body:
            msg = _('Message body is empty.')
            raise exc.InternalError(message=msg)

        # Message format check
        cluster = body.get('cluster', None)
        action = body.get('action', None)
        params = body.get('params', {})
        if not cluster or not action:
            msg = _('Both cluster identity and action must be specified.')
            raise exc.InternalError(message=msg)

        # Cluster existence check
        # TODO(YanyanHu): Or maybe we can relax this constraint to allow
        # user to trigger CLUSTER_CREATE action by sending message?
        try:
            cluster_obj = self._find_cluster(context, cluster)
        except exc.ResourceNotFound:
            msg = _('Cluster (%(cid)s) cannot be found.'
                    ) % {'cid': cluster}
            raise exc.InternalError(message=msg)

        # Permission check
        if not context.is_admin and self.user != cluster_obj.user:
            msg = _('%(user)s is not allowed to trigger actions on '
                    'cluster %(cid)s.') % {'user': self.user,
                                           'cid': cluster}
            raise exc.InternalError(message=msg)

        # Use receiver owner context to build action
        context.user_id = self.user
        context.project_id = self.project
        context.domain_id = self.domain

        # Action name check
        if action not in consts.CLUSTER_ACTION_NAMES:
            msg = _("Illegal cluster action '%s' specified.") % action
            raise exc.InternalError(message=msg)

        kwargs = {
            'name': 'receiver_%s_%s' % (self.id[:8], message['id'][:8]),
            'cause': consts.CAUSE_RPC,
            'status': action_mod.Action.READY,
            'inputs': params
        }
        action_id = action_mod.Action.create(context, cluster_obj.id,
                                             action, **kwargs)

        return action_id

    def initialize_channel(self, context):
        self.notifier_roles = context.roles
        queue_name = self._create_queue()
        subscription = self._create_subscription(queue_name)

        self.channel = {
            'queue_name': queue_name,
            'subscription': subscription.subscription_id
        }
        return self.channel

    def release_channel(self, context):
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

    def notify(self, context, params=None):
        queue_name = self.channel['queue_name']
        # Claim message(s) from queue
        # TODO(Yanyanhu) carefully handling claim ttl to avoid
        # potential race condition.
        try:
            claim = self.zaqar().claim_create(queue_name)
            messages = claim.messages
        except exc.InternalError as ex:
            LOG.error(_('Failed in claiming message: %s'), str(ex))
            return

        # Build actions
        actions = []
        if messages:
            for message in messages:
                try:
                    action_id = self._build_action(context, message)
                    actions.append(action_id)
                except exc.InternalError as ex:
                    LOG.error(_('Failed in building action: %s'), ex.message)
                try:
                    self.zaqar().message_delete(queue_name, message['id'],
                                                claim.id)
                except exc.InternalError as ex:
                    LOG.error(_('Failed in deleting message %(id)s: %(reason)s'
                                ), {'id': message['id'],
                                    'reason': ex.message})

            self.zaqar().claim_delete(queue_name, claim.id)

            msg = _('Actions %(actions)s were successfully built.'
                    ) % {'actions': actions}
            LOG.info(msg)

            dispatcher.start_action()

        return actions

    def to_dict(self):
        message = super(Message, self).to_dict()
        # Pop subscription from channel info since it
        # should be invisible for user.
        message['channel'].pop('subscription')

        return message
