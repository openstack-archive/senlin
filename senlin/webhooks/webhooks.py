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

import datetime

from oslo_config import cfg
from oslo_log import log as logging
from oslo_utils import timeutils

from senlin.common import exception
from senlin.common.i18n import _
from senlin.common.i18n import _LI
from senlin.common import utils
from senlin.db import api as db_api
from senlin.drivers.openstack import keystone_v3

LOG = logging.getLogger(__name__)

CONF = cfg.CONF


class Webhook(object):
    '''Create a Webhook which is used to trigger an object action

    Note: we enforce user to include a persistent credential,
    e.g. password into the request when creating Webhook.
    This credential info will be stored in DB and then be used
    to generate the API request to object action(e.g. cluster scaleout)
    when the webhook is triggered later.
    '''

    def __init__(self, context, obj_id, obj_type, action, **kwargs):
        self.id = kwargs.get('id', None)
        self.name = kwargs.get('name', None)
        self.user = context.user
        self.project = context.project
        self.domain = context.domain

        self.created_time = datetime.datetime.utcnow()
        self.deleted_time = None

        self.obj_id = obj_id
        self.obj_type = obj_type
        self.action = action

        # A credential should include either userid or username
        # and user_domain_id to identify a unique user. It also
        # contains the password and auth_url for WebhookMiddleware
        # to do authentication.
        self.credential = kwargs.get('credential', None)
        self.params = kwargs.get('params', {})

    def store(self, context):
        '''Store the webhook in database and return its ID.'''

        values = {
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

        if not self.id:
            webhook = db_api.webhook_create(context, values)
            self.id = webhook.id
        else:
            # The webhook has already existed, return directly
            # since webhook doesn't support updating.
            return self.id

        return self.id

    @classmethod
    def _from_db_record(cls, context, record):
        '''Construct a webhook object from database record.

        :param context: the context used for DB operations;
        :param record: a DB cluster object that will receive all fields;
        '''
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

        return cls(context, record.obj_id, record.obj_type,
                   record.action, **kwargs)

    @classmethod
    def load(cls, context, webhook_id=None, show_deleted=False):
        '''Retrieve a webhook from database.'''
        webhook = db_api.webhook_get(context, webhook_id,
                                     show_deleted=show_deleted)
        if webhook is None:
            msg = "Webhook %s is not found" % webhook_id
            LOG.warn(msg)
            raise exception.WebhookNotFound(webhook=webhook_id)

        LOG.debug(_("Webhook %(id)s found,"), {'id': webhook_id})
        return cls._from_db_record(context, webhook)

    @classmethod
    def load_all(cls, context, limit=None, marker=None, sort_keys=None,
                 sort_dir=None, filters=None, project_safe=True,
                 show_deleted=False):
        '''Retrieve all webhooks from database.'''

        records = db_api.webhook_get_all(context, show_deleted=show_deleted,
                                         limit=limit, marker=marker,
                                         sort_keys=sort_keys,
                                         sort_dir=sort_dir,
                                         filters=filters,
                                         project_safe=project_safe)

        for record in records:
            webhook = cls._from_db_record(context, record)
            yield webhook

    def to_dict(self):
        def _fmt_time(value):
            return value and timeutils.isotime(value)

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
    def from_dict(cls, **kwargs):
        return cls(**kwargs)

    def encrypt_credential(self, context):
        password, key = utils.encrypt(self.credential['password'])
        self.credential['password'] = password
        return key

    def generate_url(self, context, key):
        '''Generate webhook URL with proper format.'''
        senlin_creds = keystone_v3.get_service_credentials()
        kc = keystone_v3.KeystoneClient(senlin_creds)
        senlin_service = kc.service_get('clustering',
                                        'senlin')
        if senlin_service:
            senlin_service_id = senlin_service[0]['id']
        else:
            raise exception.ResourceNotFound(resource='service:senlin')

        region = cfg.CONF.region_name_for_services
        endpoints = kc.endpoint_get(senlin_service_id,
                                    region,
                                    'public')
        url_endpoint = endpoints[0]['url'].replace('$(tenant_id)s',
                                                   self.project)
        webhook_part = '/webhooks/%s/trigger' % self.id
        basic_url = ''.join([url_endpoint, webhook_part])

        webhook_url = "%s?key=%s" % (basic_url, key)
        LOG.info(_LI("Generate url for webhook %(id)s") % {'id': self.id})

        return webhook_url, key

    @classmethod
    def delete(cls, context, webhook_id):
        db_api.webhook_delete(context, webhook_id)
