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

from oslo_context import context as oslo_context
from oslo_log import log as logging
from oslo_utils import timeutils
from oslo_utils import uuidutils

from senlin.common import consts
from senlin.common import context as senlin_context
from senlin.common import exception
from senlin.common.i18n import _
from senlin.common import utils
from senlin.drivers import base as driver_base
from senlin.objects import credential as co
from senlin.objects import receiver as ro

LOG = logging.getLogger(__name__)


class Receiver(object):
    """Create a Receiver which is used to trigger a cluster action."""

    def __new__(cls, rtype, cluster_id=None, action=None, **kwargs):
        """Create a new receiver object.

        :param rtype: Type name of receiver.
        :param cluster_id: ID of the targeted cluster.
        :param action: Targeted action for execution.
        :param kwargs: A dict containing optional parameters.
        :returns: An instance of a specific sub-class of Receiver.
        """
        if rtype == consts.RECEIVER_WEBHOOK:
            from senlin.engine.receivers import webhook
            ReceiverClass = webhook.Webhook
        elif rtype == consts.RECEIVER_MESSAGE:
            from senlin.engine.receivers import message
            ReceiverClass = message.Message
        else:
            ReceiverClass = Receiver

        return super(Receiver, cls).__new__(ReceiverClass)

    def __init__(self, rtype, cluster_id=None, action=None, **kwargs):

        self.id = kwargs.get('id', None)
        self.name = kwargs.get('name', None)
        self.type = rtype
        self.user = kwargs.get('user', '')
        self.project = kwargs.get('project', '')
        self.domain = kwargs.get('domain', '')

        self.created_at = kwargs.get('created_at', None)
        self.updated_at = kwargs.get('updated_at', None)

        self.cluster_id = cluster_id
        self.action = action
        self.actor = kwargs.get('actor', {})
        self.params = kwargs.get('params', {})
        self.channel = kwargs.get('channel', {})

    def store(self, context, update=False):
        """Store the receiver in database and return its ID.

        :param context: Context for DB operations.
        """
        timestamp = timeutils.utcnow(True)
        self.created_at = timeutils.utcnow(True)
        values = {
            'id': self.id,
            'name': self.name,
            'type': self.type,
            'user': self.user,
            'project': self.project,
            'domain': self.domain,
            'created_at': self.created_at,
            'updated_at': self.updated_at,
            'cluster_id': self.cluster_id,
            'actor': self.actor,
            'action': self.action,
            'params': self.params,
            'channel': self.channel,
        }

        if update:
            self.updated_at = timestamp
            values['updated_at'] = timestamp
            ro.Receiver.update(context, self.id, values)
        else:
            self.created_at = timestamp
            values['created_at'] = timestamp
            receiver = ro.Receiver.create(context, values)
            self.id = receiver.id

        return self.id

    @classmethod
    def create(cls, context, rtype, cluster, action, **kwargs):
        cdata = dict()
        if rtype == consts.RECEIVER_WEBHOOK and context.is_admin:
            # use object owner if request is from admin
            cred = co.Credential.get(context, cluster.user, cluster.project)
            trust_id = cred['cred']['openstack']['trust']
            cdata['trust_id'] = trust_id
        else:
            # otherwise, use context user
            cdata['trust_id'] = context.trusts

        kwargs['actor'] = cdata
        kwargs['user'] = context.user_id
        kwargs['project'] = context.project_id
        kwargs['domain'] = context.domain_id
        kwargs['id'] = uuidutils.generate_uuid()
        cluster_id = cluster.id if cluster else None
        obj = cls(rtype, cluster_id, action, **kwargs)
        obj.initialize_channel(context)
        obj.store(context)

        return obj

    @classmethod
    def _from_object(cls, receiver):
        """Construct a receiver from receiver object.

        @param cls: The target class.
        @param receiver: a receiver object that contains all fields.
        """
        kwargs = {
            'id': receiver.id,
            'name': receiver.name,
            'user': receiver.user,
            'project': receiver.project,
            'domain': receiver.domain,
            'created_at': receiver.created_at,
            'updated_at': receiver.updated_at,
            'actor': receiver.actor,
            'params': receiver.params,
            'channel': receiver.channel,
        }

        return cls(receiver.type, receiver.cluster_id, receiver.action,
                   **kwargs)

    @classmethod
    def load(cls, context, receiver_id=None, receiver_obj=None,
             project_safe=True):
        """Retrieve a receiver from database.

        @param context: the context for db operations.
        @param receiver_id: the unique ID of the receiver to retrieve.
        @param receiver_obj: the DB object of a receiver to retrieve.
        @param project_safe: Optional parameter specifying whether only
                             receiver belong to the context.project will be
                             loaded.
        """
        if receiver_obj is None:
            receiver_obj = ro.Receiver.get(context, receiver_id,
                                           project_safe=project_safe)
            if receiver_obj is None:
                raise exception.ResourceNotFound(type='receiver',
                                                 id=receiver_id)

        return cls._from_object(receiver_obj)

    def to_dict(self):
        info = {
            'id': self.id,
            'name': self.name,
            'type': self.type,
            'user': self.user,
            'project': self.project,
            'domain': self.domain,
            'created_at': utils.isotime(self.created_at),
            'updated_at': utils.isotime(self.updated_at),
            'cluster_id': self.cluster_id,
            'actor': self.actor,
            'action': self.action,
            'params': self.params,
            'channel': self.channel,
        }
        return info

    def initialize_channel(self, context):
        return {}

    def release_channel(self, context):
        return

    def notify(self, context, params=None):
        return

    @classmethod
    def delete(cls, context, receiver_id):
        """Delete a receiver.

        @param context: the context for db operations.
        @param receiver_id: the unique ID of the receiver to delete.
        """
        receiver_obj = cls.load(context, receiver_id=receiver_id)
        receiver_obj.release_channel(context)
        ro.Receiver.delete(context, receiver_obj.id)

        return

    def _get_base_url(self):
        base = None
        service_cred = senlin_context.get_service_credentials()
        kc = driver_base.SenlinDriver().identity(service_cred)
        try:
            base = kc.get_senlin_endpoint()
        except exception.InternalError as ex:
            msg = _('Senlin endpoint can not be found: %s.') % ex.message
            LOG.warning(msg)

        return base

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
