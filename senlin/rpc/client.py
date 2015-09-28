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
from oslo_log import log as logging

from senlin.common import consts
from senlin.common import messaging

LOG = logging.getLogger(__name__)


class EngineClient(object):
    '''Client side of the senlin engine rpc API.'''

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

    def local_error_name(self, error):
        '''Returns the name of the error with any _Remote postfix removed.

        :param error: Remote raised error to derive the name from.
        '''

        error_name = error.__class__.__name__
        return error_name.split('_Remote')[0]

    def ignore_error_named(self, error, name):
        '''Raises the error unless its local name matches the supplied name

        :param error: Remote raised error to derive the local name from.
        :param name: Name to compare local name to.
        '''
        if self.local_error_name(error) != name:
            raise error

    def profile_type_list(self, ctxt):
        return self.call(ctxt, self.make_msg('profile_type_list'))

    def profile_type_schema(self, ctxt, type_name):
        return self.call(ctxt, self.make_msg('profile_type_schema',
                                             type_name=type_name))

    def profile_list(self, ctxt, limit=None, marker=None, sort_keys=None,
                     sort_dir=None, filters=None, show_deleted=False):
        return self.call(ctxt,
                         self.make_msg('profile_list', limit=limit,
                                       marker=marker, sort_keys=sort_keys,
                                       sort_dir=sort_dir, filters=filters,
                                       show_deleted=show_deleted))

    def profile_create(self, ctxt, name, spec, permission, metadata):
        return self.call(ctxt,
                         self.make_msg('profile_create', name=name,
                                       spec=spec, permission=permission,
                                       metadata=metadata))

    def profile_get(self, ctxt, identity):
        return self.call(ctxt,
                         self.make_msg('profile_get', identity=identity))

    def profile_update(self, ctxt, profile_id, name, spec, permission,
                       metadata):
        return self.call(ctxt,
                         self.make_msg('profile_update',
                                       profile_id=profile_id,
                                       name=name, spec=spec,
                                       permission=permission,
                                       metadata=metadata))

    def profile_delete(self, ctxt, identity, cast=True):
        rpc_method = self.cast if cast else self.call
        return rpc_method(ctxt,
                          self.make_msg('profile_delete',
                                        identity=identity))

    def policy_type_list(self, ctxt):
        return self.call(ctxt, self.make_msg('policy_type_list'))

    def policy_type_schema(self, ctxt, type_name):
        return self.call(ctxt, self.make_msg('policy_type_schema',
                                             type_name=type_name))

    def policy_list(self, ctxt, limit=None, marker=None, sort_keys=None,
                    sort_dir=None, filters=None, show_deleted=False):
        return self.call(ctxt,
                         self.make_msg('policy_list', limit=limit,
                                       marker=marker, sort_keys=sort_keys,
                                       sort_dir=sort_dir, filters=filters,
                                       show_deleted=show_deleted))

    def policy_create(self, ctxt, name, spec, level, cooldown):
        return self.call(ctxt,
                         self.make_msg('policy_create', name=name, spec=spec,
                                       level=level, cooldown=cooldown))

    def policy_get(self, ctxt, identity):
        return self.call(ctxt,
                         self.make_msg('policy_get', identity=identity))

    def policy_update(self, ctxt, identity, name, level, cooldown):
        return self.call(ctxt,
                         self.make_msg('policy_update', identity=identity,
                                       name=name, level=level,
                                       cooldown=cooldown))

    def policy_delete(self, ctxt, identity, cast=True):
        rpc_method = self.cast if cast else self.call
        return rpc_method(ctxt,
                          self.make_msg('policy_delete',
                                        identity=identity))

    def cluster_list(self, ctxt, limit=None, marker=None, sort_keys=None,
                     sort_dir=None, filters=None, project_safe=True,
                     show_deleted=False, show_nested=False):
        # We keep the project_safe param here for the moment
        return self.call(ctxt,
                         self.make_msg('cluster_list',
                                       limit=limit, marker=marker,
                                       sort_keys=sort_keys, sort_dir=sort_dir,
                                       filters=filters,
                                       project_safe=project_safe,
                                       show_deleted=show_deleted,
                                       show_nested=show_nested))

    def cluster_get(self, ctxt, identity):
        return self.call(ctxt,
                         self.make_msg('cluster_get', identity=identity))

    def cluster_create(self, ctxt, name, desired_capacity, profile_id,
                       min_size=None, max_size=None, parent=None,
                       metadata=None, timeout=None):
        return self.call(ctxt, self.make_msg('cluster_create',
                                             name=name,
                                             desired_capacity=desired_capacity,
                                             profile_id=profile_id,
                                             min_size=min_size,
                                             max_size=max_size,
                                             parent=parent,
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
                       parent=None, metadata=None, timeout=None):
        return self.call(ctxt, self.make_msg('cluster_update',
                                             identity=identity, name=name,
                                             profile_id=profile_id,
                                             parent=parent, metadata=metadata,
                                             timeout=timeout))

    def cluster_delete(self, ctxt, identity, cast=True):
        rpc_method = self.cast if cast else self.call
        return rpc_method(ctxt,
                          self.make_msg('cluster_delete',
                                        identity=identity))

    def node_list(self, ctxt, cluster_id=None, show_deleted=False,
                  limit=None, marker=None,
                  sort_keys=None, sort_dir=None,
                  filters=None, project_safe=True):
        return self.call(ctxt,
                         self.make_msg('node_list', cluster_id=cluster_id,
                                       show_deleted=show_deleted,
                                       limit=limit, marker=marker,
                                       sort_keys=sort_keys, sort_dir=sort_dir,
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

    def node_join(self, ctxt, identity, cluster_id):
        return self.call(ctxt,
                         self.make_msg('node_join', identity=identity,
                                       cluster_id=cluster_id))

    def node_leave(self, ctxt, identity):
        return self.call(ctxt,
                         self.make_msg('node_leave', identity=identity))

    def node_delete(self, ctxt, identity, force=False, cast=True):
        rpc_method = self.cast if cast else self.call
        return rpc_method(ctxt,
                          self.make_msg('node_delete', identity=identity,
                                        force=force))

    def action_list(self, ctxt, filters=None, limit=None, marker=None,
                    sort_keys=None, sort_dir=None, show_deleted=False):
        return self.call(ctxt,
                         self.make_msg('action_list', filters=filters,
                                       limit=limit, marker=marker,
                                       sort_keys=sort_keys, sort_dir=sort_dir,
                                       show_deleted=show_deleted))

    def cluster_policy_list(self, ctxt, cluster_id, filters=None,
                            sort_dir=None, sort_keys=None):
        return self.call(ctxt, self.make_msg('cluster_policy_list',
                                             identity=cluster_id,
                                             filters=filters,
                                             sort_keys=sort_keys,
                                             sort_dir=sort_dir))

    def cluster_policy_attach(self, ctxt, cluster_id, policy_id, priority=50,
                              level=None, cooldown=None, enabled=True):
        return self.call(ctxt, self.make_msg('cluster_policy_attach',
                                             identity=cluster_id,
                                             policy=policy_id,
                                             priority=priority,
                                             level=level,
                                             cooldown=cooldown,
                                             enabled=enabled))

    def cluster_policy_detach(self, ctxt, cluster_id, policy_id):
        return self.call(ctxt, self.make_msg('cluster_policy_detach',
                                             identity=cluster_id,
                                             policy=policy_id))

    def cluster_policy_get(self, ctxt, cluster_id, policy_id):
        return self.call(ctxt, self.make_msg('cluster_policy_get',
                                             identity=cluster_id,
                                             policy_id=policy_id))

    def cluster_policy_update(self, ctxt, cluster_id, policy_id, priority=None,
                              level=None, cooldown=None, enabled=None):
        return self.call(ctxt, self.make_msg('cluster_policy_update',
                                             identity=cluster_id,
                                             policy=policy_id,
                                             priority=priority,
                                             level=level,
                                             cooldown=cooldown,
                                             enabled=enabled))

    def action_create(self, ctxt, name, target, action, params):
        return self.call(ctxt,
                         self.make_msg('action_create',
                                       name=name, target=target,
                                       action=action, params=params))

    def action_get(self, ctxt, identity):
        return self.call(ctxt,
                         self.make_msg('action_get', identity=identity))

    def webhook_list(self, ctxt, show_deleted=False, limit=None,
                     marker=None, sort_keys=None, sort_dir=None,
                     filters=None, project_safe=True):
        return self.call(ctxt,
                         self.make_msg('webhook_list',
                                       limit=limit, marker=marker,
                                       sort_keys=sort_keys, sort_dir=sort_dir,
                                       filters=filters,
                                       project_safe=project_safe,
                                       show_deleted=show_deleted))

    def webhook_create(self, ctxt, name, obj_id, obj_type, action,
                       credential, params):
        return self.call(ctxt,
                         self.make_msg('webhook_create',
                                       obj_id=obj_id,
                                       obj_type=obj_type,
                                       action=action,
                                       credential=credential,
                                       params=params,
                                       name=name))

    def webhook_get(self, ctxt, identity):
        return self.call(ctxt,
                         self.make_msg('webhook_get', identity=identity))

    def webhook_trigger(self, ctxt, identity, params=None):
        return self.call(ctxt,
                         self.make_msg('webhook_trigger', identity=identity,
                                       params=params))

    def webhook_delete(self, ctxt, identity, cast=True):
        rpc_method = self.cast if cast else self.call
        return rpc_method(ctxt,
                          self.make_msg('webhook_delete', identity=identity))

    def trigger_list(self, ctxt, limit=None, marker=None, sort_keys=None,
                     sort_dir=None, filters=None, project_safe=True,
                     show_deleted=False):
        return self.call(ctxt,
                         self.make_msg('trigger_list',
                                       limit=limit, marker=marker,
                                       sort_keys=sort_keys, sort_dir=sort_dir,
                                       filters=filters,
                                       project_safe=project_safe,
                                       show_deleted=show_deleted))

    def trigger_create(self, ctxt, name, spec, description=None, enabled=None,
                       state=None, severity=None):
        return self.call(ctxt,
                         self.make_msg('trigger_create', name=name, spec=spec,
                                       description=description,
                                       enabled=enabled, state=state,
                                       severity=severity))

    def trigger_get(self, ctxt, identity):
        return self.call(ctxt,
                         self.make_msg('trigger_get', identity=identity))

    def trigger_delete(self, ctxt, identity, force=False, cast=True):
        rpc_method = self.cast if cast else self.call
        return rpc_method(ctxt,
                          self.make_msg('trigger_delete', identity=identity,
                                        force=force))

    def event_list(self, ctxt, filters=None, limit=None, marker=None,
                   sort_keys=None, sort_dir=None, project_safe=True,
                   show_deleted=False):
        return self.call(ctxt,
                         self.make_msg('event_list', filters=filters,
                                       limit=limit, marker=marker,
                                       sort_keys=sort_keys, sort_dir=sort_dir,
                                       project_safe=project_safe,
                                       show_deleted=show_deleted))

    def event_get(self, ctxt, identity):
        return self.call(ctxt,
                         self.make_msg('event_get', identity=identity))

    def get_revision(self, ctxt):
        return self.call(ctxt, self.make_msg('get_revision'))
