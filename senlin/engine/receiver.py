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
from oslo_utils import timeutils
from oslo_utils import uuidutils
from six.moves.urllib import parse

from senlin.common import consts
from senlin.common import exception
from senlin.common import utils
from senlin.objects import credential as co
from senlin.objects import receiver as ro

CONF = cfg.CONF


class Receiver(object):
    """Create a Receiver which is used to trigger a cluster action."""

    def __new__(cls, rtype, cluster_id, action, **kwargs):
        """Create a new receiver object.

        :param rtype: Type name of receiver.
        :param cluster_id: ID of the targeted cluster.
        :param action: Targeted action for execution.
        :param kwargs: A dict containing optional parameters.
        :returns: An instance of a specific sub-class of Receiver.
        """
        if rtype == consts.RECEIVER_WEBHOOK:
            ReceiverClass = Webhook
        else:
            ReceiverClass = Receiver

        return super(Receiver, cls).__new__(ReceiverClass)

    def __init__(self, rtype, cluster_id, action, **kwargs):

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

    def store(self, context):
        """Store the receiver in database and return its ID.

        :param context: Context for DB operations.
        """
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

        # TODO(Qiming): Add support to update
        receiver = ro.Receiver.create(context, values)
        self.id = receiver.id

        return self.id

    @classmethod
    def create(cls, context, rtype, cluster, action, **kwargs):
        cdata = dict()
        if context.is_admin:
            # use object owner if request is from admin
            cred = co.Credential.get(context, cluster.user, cluster.project)
            trust_id = cred['cred']['openstack']['trust']
            cdata['trust_id'] = trust_id
        else:
            # otherwise, use context user
            cdata['trust_id'] = context.trusts

        kwargs['id'] = uuidutils.generate_uuid()
        kwargs['actor'] = cdata
        kwargs['user'] = context.user
        kwargs['project'] = context.project
        kwargs['domain'] = context.domain
        obj = cls(rtype, cluster.id, action, **kwargs)
        obj.initialize_channel()
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
                raise exception.ReceiverNotFound(receiver=receiver_id)

        return cls._from_object(receiver_obj)

    @classmethod
    def load_all(cls, context, limit=None, marker=None, sort=None,
                 filters=None, project_safe=True):
        """Retrieve all receivers from database."""

        objs = ro.Receiver.get_all(context, limit=limit, marker=marker,
                                   sort=sort, filters=filters,
                                   project_safe=project_safe)

        for obj in objs:
            yield cls._from_object(obj)

    def to_dict(self):
        info = {
            'id': self.id,
            'name': self.name,
            'type': self.type,
            'user': self.user,
            'project': self.project,
            'domain': self.domain,
            'created_at': utils.format_time(self.created_at),
            'updated_at': utils.format_time(self.updated_at),
            'cluster_id': self.cluster_id,
            'actor': self.actor,
            'action': self.action,
            'params': self.params,
            'channel': self.channel,
        }
        return info

    def initialize_channel(self):
        return {}


class Webhook(Receiver):
    """Webhook flavor of receivers."""

    def initialize_channel(self):
        host = CONF.webhook.host
        port = CONF.webhook.port
        base = "http://%(h)s:%(p)s/v1" % {'h': host, 'p': port}
        webhook = "/webhooks/%(id)s/trigger" % {'id': self.id}
        if self.params:
            normalized = sorted(self.params.items(), key=lambda d: d[0])
            qstr = parse.urlencode(normalized)
            url = "".join([base, webhook, '?V=1&', qstr])
        else:
            url = "".join([base, webhook, '?V=1'])

        self.channel = {
            'alarm_url': url
        }
        return self.channel
