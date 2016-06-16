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

from senlin.common import consts
from senlin.common import messaging


class EngineClient(object):
    """Client side of the senlin engine rpc API.

    Version History:

      1.0 - Initial version (Mitaka 1.0 release)
      1.1 - Add cluster-collect call.
    """

    BASE_RPC_API_VERSION = '1.0'

    def __init__(self):
        self._client = messaging.get_rpc_client(
            topic=consts.ENGINE_TOPIC,
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

    def credential_create(self, ctxt, cred, attrs=None):
        return self.call(ctxt, self.make_msg('credential_create', cred=cred,
                                             attrs=attrs))

    def credential_get(self, ctxt, query=None):
        return self.call(ctxt, self.make_msg('credential_get', query=query))

    def credential_update(self, ctxt, cred, attrs=None):
        return self.call(ctxt, self.make_msg('credential_update', cred=cred,
                                             attrs=attrs))

    def profile_type_list(self, ctxt):
        return self.call(ctxt, self.make_msg('profile_type_list'))

    def profile_type_get(self, ctxt, type_name):
        return self.call(ctxt, self.make_msg('profile_type_get',
                                             type_name=type_name))

    def profile_list(self, ctxt, limit=None, marker=None, sort=None,
                     filters=None, project_safe=True):
        return self.call(ctxt,
                         self.make_msg('profile_list', filters=filters,
                                       limit=limit, marker=marker, sort=sort,
                                       project_safe=project_safe))

    def profile_create(self, ctxt, name, spec, metadata):
        return self.call(ctxt,
                         self.make_msg('profile_create', name=name,
                                       spec=spec, metadata=metadata))

    def profile_get(self, ctxt, identity):
        return self.call(ctxt,
                         self.make_msg('profile_get', identity=identity))

    def profile_update(self, ctxt, profile_id, name, metadata):
        return self.call(ctxt,
                         self.make_msg('profile_update',
                                       profile_id=profile_id,
                                       name=name, metadata=metadata))

    def profile_delete(self, ctxt, identity, cast=True):
        rpc_method = self.cast if cast else self.call
        return rpc_method(ctxt,
                          self.make_msg('profile_delete',
                                        identity=identity))

    def policy_type_list(self, ctxt):
        return self.call(ctxt, self.make_msg('policy_type_list'))

    def policy_type_get(self, ctxt, type_name):
        return self.call(ctxt, self.make_msg('policy_type_get',
                                             type_name=type_name))

    def policy_list(self, ctxt, limit=None, marker=None, sort=None,
                    filters=None, project_safe=True):
        return self.call(ctxt,
                         self.make_msg('policy_list', filters=filters,
                                       limit=limit, marker=marker, sort=sort,
                                       project_safe=project_safe))

    def policy_create(self, ctxt, name, spec):
        return self.call(ctxt,
                         self.make_msg('policy_create', name=name, spec=spec))

    def policy_get(self, ctxt, identity):
        return self.call(ctxt,
                         self.make_msg('policy_get', identity=identity))

    def policy_update(self, ctxt, identity, name):
        return self.call(ctxt,
                         self.make_msg('policy_update', identity=identity,
                                       name=name))

    def policy_delete(self, ctxt, identity, cast=True):
        rpc_method = self.cast if cast else self.call
        return rpc_method(ctxt,
                          self.make_msg('policy_delete',
                                        identity=identity))

    def cluster_list(self, ctxt, limit=None, marker=None, sort=None,
                     filters=None, project_safe=True):
        return self.call(ctxt,
                         self.make_msg('cluster_list', filters=filters,
                                       limit=limit, marker=marker, sort=sort,
                                       project_safe=project_safe))

    def cluster_get(self, ctxt, identity):
        return self.call(ctxt,
                         self.make_msg('cluster_get', identity=identity))

    def cluster_create(self, ctxt, name, desired_capacity, profile_id,
                       min_size=None, max_size=None, metadata=None,
                       timeout=None):
        return self.call(ctxt, self.make_msg('cluster_create',
                                             name=name,
                                             desired_capacity=desired_capacity,
                                             profile_id=profile_id,
                                             min_size=min_size,
                                             max_size=max_size,
                                             metadata=metadata,
                                             timeout=timeout))

    def cluster_add_nodes(self, ctxt, identity, nodes):
        return self.call(ctxt, self.make_msg('cluster_add_nodes',
                                             identity=identity,
                                             nodes=nodes))

    def cluster_del_nodes(self, ctxt, identity, nodes):
        return self.call(ctxt, self.make_msg('cluster_del_nodes',
                                             identity=identity,
                                             nodes=nodes))

    def cluster_resize(self, ctxt, identity, adj_type=None, number=None,
                       min_size=None, max_size=None, min_step=None,
                       strict=True):
        return self.call(ctxt, self.make_msg('cluster_resize',
                                             identity=identity,
                                             adj_type=adj_type,
                                             number=number,
                                             min_size=min_size,
                                             max_size=max_size,
                                             min_step=min_step,
                                             strict=strict))

    def cluster_scale_out(self, ctxt, identity, count=None):
        return self.call(ctxt, self.make_msg('cluster_scale_out',
                                             identity=identity,
                                             count=count))

    def cluster_scale_in(self, ctxt, identity, count=None):
        return self.call(ctxt, self.make_msg('cluster_scale_in',
                                             identity=identity,
                                             count=count))

    def cluster_update(self, ctxt, identity, name=None, profile_id=None,
                       metadata=None, timeout=None):
        return self.call(ctxt, self.make_msg('cluster_update',
                                             identity=identity, name=name,
                                             profile_id=profile_id,
                                             metadata=metadata,
                                             timeout=timeout))

    def cluster_delete(self, ctxt, identity, cast=True):
        rpc_method = self.cast if cast else self.call
        return rpc_method(ctxt,
                          self.make_msg('cluster_delete',
                                        identity=identity))

    def cluster_collect(self, ctxt, identity, path, project_safe=True):
        return self.call(ctxt, self.make_msg('cluster_collect',
                                             identity=identity, path=path,
                                             project_safe=project_safe),
                         version='1.1')

    def cluster_check(self, ctxt, identity, params=None):
        return self.call(ctxt, self.make_msg('cluster_check',
                                             identity=identity,
                                             params=params))

    def cluster_recover(self, ctxt, identity, params=None):
        return self.call(ctxt, self.make_msg('cluster_recover',
                                             identity=identity,
                                             params=params))

    def node_list(self, ctxt, cluster_id=None, limit=None, marker=None,
                  sort=None, filters=None, project_safe=True):
        return self.call(ctxt,
                         self.make_msg('node_list', cluster_id=cluster_id,
                                       limit=limit, marker=marker, sort=sort,
                                       filters=filters,
                                       project_safe=project_safe))

    def node_create(self, ctxt, name, cluster_id, profile_id, role, metadata):
        return self.call(ctxt,
                         self.make_msg('node_create', name=name,
                                       profile_id=profile_id,
                                       cluster_id=cluster_id,
                                       role=role, metadata=metadata))

    def node_get(self, ctxt, identity, show_details=False):
        return self.call(ctxt,
                         self.make_msg('node_get', identity=identity,
                                       show_details=show_details))

    def node_update(self, ctxt, identity, name, profile_id, role, metadata):
        return self.call(ctxt,
                         self.make_msg('node_update', identity=identity,
                                       name=name, profile_id=profile_id,
                                       role=role, metadata=metadata))

    def node_delete(self, ctxt, identity, cast=True):
        rpc_method = self.cast if cast else self.call
        return rpc_method(ctxt,
                          self.make_msg('node_delete', identity=identity))

    def node_check(self, ctxt, identity, params=None):
        return self.call(ctxt, self.make_msg('node_check',
                                             identity=identity,
                                             params=params))

    def node_recover(self, ctxt, identity, params=None):
        return self.call(ctxt, self.make_msg('node_recover',
                                             identity=identity,
                                             params=params))

    def action_list(self, ctxt, filters=None, limit=None, marker=None,
                    sort=None, project_safe=True):
        return self.call(ctxt,
                         self.make_msg('action_list', filters=filters,
                                       limit=limit, marker=marker,
                                       sort=sort, project_safe=project_safe))

    def cluster_policy_list(self, ctxt, cluster_id, filters=None, sort=None):
        return self.call(ctxt, self.make_msg('cluster_policy_list',
                                             identity=cluster_id,
                                             filters=filters, sort=sort))

    def cluster_policy_attach(self, ctxt, cluster_id, policy_id, enabled=True):
        return self.call(ctxt, self.make_msg('cluster_policy_attach',
                                             identity=cluster_id,
                                             policy=policy_id,
                                             enabled=enabled))

    def cluster_policy_detach(self, ctxt, cluster_id, policy_id):
        return self.call(ctxt, self.make_msg('cluster_policy_detach',
                                             identity=cluster_id,
                                             policy=policy_id))

    def cluster_policy_get(self, ctxt, cluster_id, policy_id):
        return self.call(ctxt, self.make_msg('cluster_policy_get',
                                             identity=cluster_id,
                                             policy_id=policy_id))

    def cluster_policy_update(self, ctxt, cluster_id, policy_id, enabled=None):
        return self.call(ctxt, self.make_msg('cluster_policy_update',
                                             identity=cluster_id,
                                             policy=policy_id,
                                             enabled=enabled))

    def action_create(self, ctxt, name, cluster, action, params):
        return self.call(ctxt,
                         self.make_msg('action_create',
                                       name=name, cluster=cluster,
                                       action=action, params=params))

    def action_get(self, ctxt, identity):
        return self.call(ctxt,
                         self.make_msg('action_get', identity=identity))

    def receiver_list(self, ctxt, limit=None, marker=None, filters=None,
                      sort=None, project_safe=True):
        return self.call(ctxt,
                         self.make_msg('receiver_list', filters=filters,
                                       limit=limit, marker=marker,
                                       sort=sort, project_safe=project_safe))

    def receiver_create(self, ctxt, name, type_name, cluster_id, action,
                        actor=None, params=None):
        return self.call(ctxt,
                         self.make_msg('receiver_create',
                                       name=name, type_name=type_name,
                                       cluster_id=cluster_id, action=action,
                                       actor=actor, params=params))

    def receiver_get(self, ctxt, identity, project_safe=True):
        return self.call(ctxt, self.make_msg('receiver_get', identity=identity,
                                             project_safe=project_safe))

    def receiver_delete(self, ctxt, identity, cast=True):
        rpc_method = self.cast if cast else self.call
        return rpc_method(ctxt, self.make_msg('receiver_delete',
                                              identity=identity))

    def webhook_trigger(self, ctxt, identity, params=None):
        return self.call(ctxt,
                         self.make_msg('webhook_trigger', identity=identity,
                                       params=params))

    def event_list(self, ctxt, filters=None, limit=None, marker=None,
                   sort=None, project_safe=True):
        return self.call(ctxt,
                         self.make_msg('event_list', filters=filters,
                                       limit=limit, marker=marker,
                                       sort=sort, project_safe=project_safe))

    def event_get(self, ctxt, identity):
        return self.call(ctxt,
                         self.make_msg('event_get', identity=identity))

    def get_revision(self, ctxt):
        return self.call(ctxt, self.make_msg('get_revision'))
