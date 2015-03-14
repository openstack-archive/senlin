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

from oslo_log import log as logging

from senlin.common import sdk
from senlin.common import wsgi
from senlin.openstack.identity.v3 import trust

LOG = logging.getLogger(__name__)


class SenlinTrust(object):
    '''Stores information about the trust of requester.
       e.g. roles, trustor_user_id, trustee_user_id.
    '''

    def __init__(self, id=None, project_id=None,
                 expires_at=None, impersonation=None,
                 trustee_user_id=None, trustor_user_id=None,
                 roles=None):

        self.id = id
        self.project_id = project_id
        self.expires_at = expires_at
        self.impersonation = impersonation
        self.trustee_user_id = trustee_user_id
        self.trustor_user_id = trustor_user_id
        self.roles = roles

    def to_dict(self):
        return {
            'id': self.id,
            'project_id': self.project_id,
            'expires_at': self.expires_at,
            'impersonation': self.impersonation,
            'trustee_user_id': self.trustee_user_id,
            'trustor_user_id': self.trustor_user_id,
            'roles': self.roles
        }

    @classmethod
    def from_dict(cls, values):
        return cls(**values)


def get_trust(context, trust_id):
    '''Get trust detail information.'''
    conn = sdk.create_connection(context)
    session = conn.session

    params = {
        'id': trust_id
    }
    obj = trust.Trust.new(**params)
    result = obj.get(session)

    return result


def list_trust(context, trustee_user_id=None, trustor_user_id=None):
    conn = sdk.create_connection(context)
    session = conn.session

    trusts = []
    params = {}
    if trustee_user_id is not None:
        params['trustee_user_id'] = trustee_user_id

    if trustor_user_id is not None:
        params['trustor_user_id'] = trustor_user_id

    result = trust.Trust.list(session, **params)
    for obj in result:
        trust_item = {
            'id': obj.id,
            'project_id': obj.project_id,
            'expires_at': obj.expires_at,
            'impersonation': obj.impersonation,
            'trustee_user_id': obj.trustee_user_id,
            'trustor_user_id': obj.trustor_user_id
        }

        # Get roles information of trust
        trust_detail = get_trust(context, obj.id)
        trust_item['roles'] = trust_detail.roles

        trusts.append(trust_item)

    return trusts


class TrustMiddleware(wsgi.Middleware):
    """This middleware gets trusts information of the requester
       and fill it into request context. This information will
       be used by senlin engine later to support privilege
       management.
    """
    def process_request(self, req):
        # Query trust list with detail information
        trusts = list_trust(req.context, req.context.user_id)
        LOG.debug('Trust list of user %s is %s' %
                  (req.context.user_id, str(trusts)))
        req.context.trusts = trusts


def TrustMiddleware_filter_factory(global_conf, **local_conf):
    '''Factory method for paste.deploy.'''

    conf = global_conf.copy()
    conf.update(local_conf)

    def filter(app):
        return TrustMiddleware(app)

    return filter
