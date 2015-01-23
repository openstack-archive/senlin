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

'''
Client side of the senlin engine RPC API.
'''

from oslo_config import cfg

from senlin.common import messaging
from senlin.openstack.common import log as logging
from senlin.rpc import api as rpc_api

LOG = logging.getLogger(__name__)


class EngineClient(object):
    '''Client side of the senlin engine rpc API.

    API version history::
        1.0 - Initial version.
    '''

    BASE_RPC_API_VERSION = '1.0'

    def __init__(self):
        self._client = messaging.get_rpc_client(
            topic=rpc_api.ENGINE_TOPIC,
            server=cfg.CONF.host,
            version=self.BASE_RPC_API_VERSION)

    @staticmethod
    def make_msg(method, **kwargs):
        return method, kwargs

    def call(self, ctxt, msg, version=None):
        method, kwargs = msg
        if version is not None:
            client = self._client.prepare(version=version)
        else:
            client = self._client
        return client.call(ctxt, method, **kwargs)

    def cast(self, ctxt, msg, version=None):
        method, kwargs = msg
        if version is not None:
            client = self._client.prepare(version=version)
        else:
            client = self._client
        return client.cast(ctxt, method, **kwargs)

    def local_error_name(self, error):
        """
        Returns the name of the error with any _Remote postfix removed.

        :param error: Remote raised error to derive the name from.
        """
        error_name = error.__class__.__name__
        return error_name.split('_Remote')[0]

    def ignore_error_named(self, error, name):
        """
        Raises the error unless its local name matches the supplied name

        :param error: Remote raised error to derive the local name from.
        :param name: Name to compare local name to.
        """
        if self.local_error_name(error) != name:
            raise error

    def profile_type_list(self, ctxt):
        return self.call(ctxt, self.make_msg('profile_type_list'))

    def profile_type_spec(self, ctxt, type_name):
        return self.call(ctxt, self.make_msg('profile_type_spec',
                                             type_name=type_name))

    def profile_type_template(self, ctxt, type_name):
        return self.call(ctxt, self.make_msg('profile_type_template',
                                             type_name=type_name))

    def profile_list(self, ctxt, limit=None, marker=None, sort_keys=None,
                     sort_dir=None, filters=None, show_deleted=False):
        return self.call(ctxt,
                         self.make_msg('profile_list', limit=limit,
                                       marker=marker, sort_keys=sort_keys,
                                       sort_dir=sort_dir, filters=filters,
                                       show_deleted=show_deleted))

    def profile_create(self, ctxt, name, type, spec, perm, tags):
        return self.call(ctxt,
                         self.make_msg('profile_create',
                                       name=name, type=type, spec=spec,
                                       perm=perm, tags=tags))

    def profile_get(self, ctxt, profile_id):
        return self.call(ctxt,
                         self.make_msg('profile_get', profile_id=profile_id))

    def profile_update(self, ctxt, profile_id, name, spec, perm, tags):
        return self.call(ctxt,
                         self.make_msg('profile_update',
                                       profile_id=profile_id,
                                       name=name, spec=spec,
                                       perm=perm, tags=tags))

    def profile_delete(self, ctxt, profile_id, cast=True):
        rpc_method = self.cast if cast else self.call
        return rpc_method(ctxt,
                          self.make_msg('profile_delete',
                                        profile_id=profile_id))

    def policy_type_list(self, ctxt):
        return self.call(ctxt, self.make_msg('policy_type_list'))

    def policy_type_spec(self, ctxt, type_name):
        return self.call(ctxt, self.make_msg('policy_type_spec',
                                             type_name=type_name))

    def policy_type_template(self, ctxt, type_name):
        return self.call(ctxt, self.make_msg('policy_type_template',
                                             type_name=type_name))

    def identify_cluster(self, ctxt, cluster_name):
        """
        The identify_cluster method returns the full cluster identifier for a
        single, live cluster given the cluster name.

        :param ctxt: RPC context.
        :param cluster_name: Name of the cluster you want to see,
                           or None to see all
        """
        return self.call(ctxt, self.make_msg('identify_cluster',
                                             cluster_name=cluster_name))

    def cluster_list(self, ctxt, limit=None, marker=None, sort_keys=None,
                     sort_dir=None, filters=None, tenant_safe=True,
                     show_deleted=False, show_nested=False):
        # We keep the tenant_safe param here for the moment
        return self.call(ctxt,
                         self.make_msg('cluster_list',
                                       limit=limit, marker=marker,
                                       sort_keys=sort_keys, sort_dir=sort_dir,
                                       filters=filters,
                                       tenant_safe=tenant_safe,
                                       show_deleted=show_deleted,
                                       show_nested=show_nested))

    def cluster_get(self, ctxt, cluster_id):
        return self.call(ctxt,
                         self.make_msg('cluster_get', cluster_id=cluster_id))

    def cluster_create(self, ctxt, name, size, profile_id, args):
        return self.call(ctxt, self.make_msg('cluster_create',
                                             name=name, size=size,
                                             profile_id=profile_id,
                                             args=args))

    def cluster_update(self, ctxt, identity, size, profile_id):
        return self.call(ctxt, self.make_msg('cluster_update',
                                             identity=identity,
                                             size=size,
                                             profile_id=profile_id))

    def cluster_delete(self, ctxt, cluster_id, cast=True):
        rpc_method = self.cast if cast else self.call
        return rpc_method(ctxt,
                          self.make_msg('cluster_delete',
                                        cluster_id=cluster_id))

    def node_list(self, ctxt, cluster_id=None, show_deleted=False,
                  limit=None, marker=None,
                  sort_keys=None, sort_dir=None,
                  filters=None, tenant_safe=True):
        # We keep the tenant_safe param here for the moment
        return self.call(ctxt,
                         self.make_msg('node_list', cluster_id=cluster_id,
                                       show_deleted=show_deleted,
                                       limit=limit, marker=marker,
                                       sort_keys=sort_keys, sort_dir=sort_dir,
                                       filters=filters,
                                       tenant_safe=tenant_safe))

    def node_create(self, ctxt, name, cluster_id, profile_id, role, tags):
        return self.call(ctxt,
                         self.make_msg('node_create', name=name,
                                       cluster_id=cluster_id,
                                       profile_id=profile_id,
                                       role=role, tags=tags))

    def node_get(self, ctxt, identity):
        # TODO(Anyone): check if a conversion from name to ID is needed
        return self.call(ctxt,
                         self.make_msg('node_get', node_id=identity))

    def node_update(self, ctxt, identity, name, profile_id, role, tags):
        # TODO(Anyone): check if a conversion from name to ID is needed
        return self.call(ctxt,
                         self.make_msg('node_update', node_id=identity,
                                       name=name, profile_id=profile_id,
                                       role=role, tags=tags))

    def node_delete(self, ctxt, identity, force=False, cast=True):
        rpc_method = self.cast if cast else self.call
        return rpc_method(ctxt,
                          self.make_msg('node_delete',
                                        node_id=identity,
                                        force=force))

    def get_revision(self, ctxt):
        return self.call(ctxt, self.make_msg('get_revision'))
