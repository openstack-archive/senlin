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

from senlin.common import context
from senlin.common import exception
from senlin.common.i18n import _
from senlin.common.i18n import _LE
from senlin.common.i18n import _LI
from senlin.common import sdk
from senlin.common import utils
from senlin.common import wsgi
from senlin.db import api as db_api

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

    def __init__(self, obj_id, obj_type, action, context, **kwargs):
        self.id = None
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
        self.params = kwargs.get('params', None)

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
            LOG.warning("Try to update webhook %(id)s" % {'id': self.id})
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

        return cls(record.obj_id, record.obj_type, record.action,
                   context=context, **kwargs)

    @classmethod
    def load(cls, context, webhook_id=None, show_deleted=False):
        '''Retrieve a webhook from database.'''
        webhook = db_api.webhook_get(context, webhook_id,
                                     show_deleted=show_deleted)
        if webhook is None:
            msg = "Webhook %s is not found" % webhook_id
            LOG.warn(msg)
            raise exception.WebhookNotFound(webhook=webhook_id)

        LOG.error(_LE("Webhook %(id)s found,"), {'id': webhook_id})
        return cls._from_db_record(context, webhook)

    @classmethod
    def load_all(cls, context, limit=None, marker=None, sort_keys=None,
                 sort_dir=None, filters=None, project_safe=True,
                 show_deleted=False, show_nested=False):
        '''Retrieve all webhooks from database.'''

        records = db_api.webhook_get_all(context, limit, marker, sort_keys,
                                         sort_dir, filters, project_safe,
                                         show_deleted, show_nested)

        for record in records:
            webhook = cls._from_db_record(context, record)
            yield webhook

    def to_dict(self):
        info = {
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
            'params': self.params,
        }
        return info

    @classmethod
    def from_dict(cls, **kwargs):
        return cls(**kwargs)

    def generate_url(self):
        '''Generate webhook URL with proper format.'''
        senlin_host = cfg.CONF.senlin_api.bind_host
        senlin_port = cfg.CONF.senlin_api.bind_port
        basic_url = 'http://%s:%s/%s/webhooks/%s/trigger' % \
            (senlin_host, senlin_port, self.project, self.id)

        # Encryt the password of credential
        password, key = utils.encrypt(self.credential['password'])
        self.credential['password'] = password

        webhook_url = "%s?key=%s" % (basic_url, key)
        LOG.info(_LI("Generate url for webhook %(id)s") % {'id': self.id})

        return webhook_url, key


class WebhookMiddleware(wsgi.Middleware):
    '''Middleware to do authentication for webhook triggering

    This middleware gets authentication for request to a webhook
    based on information embedded inside url and then rebuild the
    request header.
    '''
    def process_request(self, req):
        self._authenticate(req)

    def _authenticate(self, req):
        LOG.debug("Checking credentials of webhook request")
        credential = self._get_credential(req)
        if not credential:
            return

        # Get a valid token based on credential
        # and fill into the request header
        token_id = self._get_token(credential)
        req.headers['X-Auth-Token'] = token_id

    def _get_credential(self, req):
        try:
            url_bottom = req.url.rsplit('webhooks')[1]
            webhook_id = url_bottom.rsplit('/')[1]
            trigger = url_bottom.rsplit('/')[2].startswith('trigger')
            if trigger is not True or 'key' not in req.params:
                raise Exception()
        except Exception:
            LOG.debug(_("%(url)s is not a webhook trigger url,"
                        " pass."), {'url': req.url})
            return

        if req.method != 'POST':
            LOG.debug(_("Not a post request to webhook trigger url"
                        " %(url)s, pass."), {'url': req.url})
            return

        # This is a webhook triggering, we need to fill in valid
        # credential info into the http headers to ensure this
        # request can pass keystone auth_token validation.
        #
        # Get the credential stored in DB based on webhook ID.
        # TODO(Anyone): Use Barbican to store these credential.
        LOG.debug(_("Get credential of webhook %(id)s"), webhook_id)
        senlin_context = context.RequestContext.get_service_context()
        webhook_obj = Webhook.load(senlin_context, webhook_id)
        credential = webhook_obj.credential
        credential['webhook_id'] = webhook_id

        # Decrypt the credential password with key embedded in req params
        try:
            password = str(utils.decrypt(str(credential['password']),
                                         str(req.params['key'])))
            credential['password'] = password
        except Exception:
            msg = 'Invalid key for webhook(%s) credential decryption' % \
                webhook_id
            LOG.error(msg)
            raise exception.SenlinBadRequest(msg=msg)

        return credential

    def _get_token(self, credential):
        '''Get a valid token based on credential'''

        try:
            access_info = sdk.authenticate(**credential)
            token_id = access_info.auth_token
        except Exception as ex:
            msg = 'Webhook get token failed: %s' % ex.message
            LOG.error(msg)
            raise exception.WebhookCredentialInvalid(
                webhook=credential['webhook_id'])

        # Get token successfully!
        return token_id


def WebhookMiddleware_filter_factory(global_conf, **local_conf):
    '''Factory method for paste.deploy.'''

    conf = global_conf.copy()
    conf.update(local_conf)

    def filter(app):
        return WebhookMiddleware(app)

    return filter
