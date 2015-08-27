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
from oslo_log import log as logging
from oslo_utils import timeutils
from oslo_utils import uuidutils
from six.moves.urllib import parse

from senlin.common import context
from senlin.common import exception
from senlin.common.i18n import _
from senlin.common import utils
from senlin.db import api as db_api
from senlin.drivers import base as driver_base

LOG = logging.getLogger(__name__)

CONF = cfg.CONF


class Webhook(object):
    """Create a Webhook which is used to trigger an object action.

    Note: we enforce user to include a persistent credential,
    e.g. password into the request when creating Webhook.
    This credential info will be stored in DB and then be used
    to generate the API request to object action(e.g. cluster scaleout)
    when the webhook is triggered later.
    """

    def __init__(self, obj_id, obj_type, action, context=None, **kwargs):

        self.id = kwargs.get('id', uuidutils.generate_uuid())
        self.name = kwargs.get('name', None)
        self.user = kwargs.get('user', '')
        self.project = kwargs.get('project', '')
        self.domain = kwargs.get('domain', '')

        self.created_time = kwargs.get('created_time', None)
        self.deleted_time = kwargs.get('deleted_time', None)

        self.obj_id = obj_id
        self.obj_type = obj_type
        self.action = action

        # A credential should include the user identity, which could be a user
        # id or a username accompanied by a user_domain_id. A credential also
        # contains the password and the auth_url for WebhookMiddleware to do
        # authentication.
        self.credential = kwargs.get('credential', None)
        self.params = kwargs.get('params', {})

        if context is not None:
            if self.user == '':
                self.user = context.user
            if self.project == '':
                self.project = context.project
            if self.domain == '':
                self.domain = context.domain

    def store(self, context):
        """Store the webhook in database and return its ID.

        :param context: Security context for DB operations.
        """
        self.created_time = timeutils.utcnow()
        values = {
            'id': self.id,
            'name': self.name,
            'user': self.user,
            'project': self.project,
            'domain': self.domain,
            'created_time': self.created_time,
            'deleted_time': self.deleted_time,
            'obj_id': self.obj_id,
            'obj_type': self.obj_type,
            'action': self.action,
            'credential': self.credential,
            'params': self.params
        }

        webhook = db_api.webhook_create(context, values)
        self.id = webhook.id

        return self.id

    @classmethod
    def _from_db_record(cls, record):
        """Construct a webhook object from database record.

        :param record: a DB webhook object that will receive all fields.
        """
        kwargs = {
            'id': record.id,
            'name': record.name,
            'user': record.user,
            'project': record.project,
            'domain': record.domain,
            'created_time': record.created_time,
            'deleted_time': record.deleted_time,
            'credential': record.credential,
            'params': record.params,
        }

        return cls(record.obj_id, record.obj_type, record.action, **kwargs)

    @classmethod
    def load(cls, context, webhook_id, show_deleted=False):
        """Retrieve a webhook from database.

        :param context: the security context for db operations.
        :param webhook_id: the unique ID of the webhook to retrieve.
        :param show_deleted: boolean indicating whether deleted objects
                             should be returned or not. Default is False.
        """
        webhook = db_api.webhook_get(context, webhook_id,
                                     show_deleted=show_deleted)
        if webhook is None:
            raise exception.WebhookNotFound(webhook=webhook_id)

        return cls._from_db_record(webhook)

    @classmethod
    def load_all(cls, context, limit=None, marker=None, sort_keys=None,
                 sort_dir=None, filters=None, project_safe=True,
                 show_deleted=False):
        """Retrieve all webhooks from database."""

        records = db_api.webhook_get_all(context, show_deleted=show_deleted,
                                         limit=limit, marker=marker,
                                         sort_keys=sort_keys,
                                         sort_dir=sort_dir,
                                         filters=filters,
                                         project_safe=project_safe)

        for record in records:
            webhook = cls._from_db_record(record)
            yield webhook

    def to_dict(self):
        def _fmt_time(value):
            return value and value.isoformat()

        info = {
            'id': self.id,
            'name': self.name,
            'user': self.user,
            'project': self.project,
            'domain': self.domain,
            'created_time': _fmt_time(self.created_time),
            'deleted_time': _fmt_time(self.deleted_time),
            'obj_id': self.obj_id,
            'obj_type': self.obj_type,
            'action': self.action,
            'credential': self.credential,
            'params': self.params,
        }
        return info

    @classmethod
    def from_dict(cls, context=None, **kwargs):
        obj_id = kwargs.pop('obj_id')
        obj_type = kwargs.pop('obj_type')
        action = kwargs.pop('action')
        return cls(obj_id, obj_type, action, context, **kwargs)

    def encrypt_credential(self):
        cipher, key = utils.encrypt(self.credential)
        self.credential = cipher
        return key

    def generate_url(self, key):
        """Generate webhook URL with proper format.

        :param key: Key string to be used for decrypt the credentials.
        """
        senlin_creds = context.get_service_context()
        kc = driver_base.SenlinDriver().identity(senlin_creds)
        senlin_service = kc.service_get('clustering', 'senlin')
        if not senlin_service:
            resource = _('service:type=clustering,name=senlin')
            raise exception.ResourceNotFound(resource=resource)
        senlin_service_id = senlin_service['id']
        region = cfg.CONF.region_name_for_services
        endpoint = kc.endpoint_get(senlin_service_id, region, 'public')
        if not endpoint:
            resource = _('endpoint: service=%(service)s,region='
                         '%(region)s,visibility=%(interface)s'
                         ) % {'service': senlin_service_id,
                              'region': region,
                              'interface': 'public'}
            raise exception.ResourceNotFound(resource=resource)

        endpoint_url = endpoint['url'].replace('$(tenant_id)s', self.project)
        location = endpoint_url + '/webhooks/%s/trigger' % self.id
        location += "?%s" % parse.urlencode({'key': key})

        return location, key

    @classmethod
    def delete(cls, context, webhook_id):
        db_api.webhook_delete(context, webhook_id)
