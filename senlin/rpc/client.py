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
from senlin.objects import base as object_base


class EngineClient(object):
    """Client side of the senlin engine rpc API.

    Version History:

      1.0 - Initial version (Mitaka 1.0 release)
      1.1 - Add cluster-collect call.
    """

    def __init__(self):
        if cfg.CONF.rpc_use_object:
            serializer = object_base.VersionedObjectSerializer()
        else:
            serializer = None
        self._client = messaging.get_rpc_client(consts.ENGINE_TOPIC,
                                                cfg.CONF.host,
                                                serializer=serializer)

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

    def call2(self, ctxt, method, req, version=None):
        """The main entry for invoking engine service.

        :param ctxt: The request context object.
        :param method: The name of the method to be invoked.
        :param req: A dict containing a request object.
        :param version: The engine RPC API version requested.
        """
        if version is not None:
            client = self._client.prepare(version=version)
        else:
            client = self._client

        return client.call(ctxt, method, req=req)

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

    def profile_update(self, ctxt, identity, name, metadata):
        return self.call(ctxt,
                         self.make_msg('profile_update',
                                       identity=identity,
                                       name=name, metadata=metadata))

    def profile_delete(self, ctxt, identity, cast=True):
        rpc_method = self.cast if cast else self.call
        return rpc_method(ctxt,
                          self.make_msg('profile_delete',
                                        identity=identity))

    def profile_validate(self, ctxt, spec):
        return self.call(ctxt,
                         self.make_msg('profile_validate', spec=spec))

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

    def cluster_policy_get(self, ctxt, cluster_id, policy_id):
        return self.call(ctxt, self.make_msg('cluster_policy_get',
                                             identity=cluster_id,
                                             policy_id=policy_id))

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

    def receiver_notify(self, ctxt, identity, params=None):
        return self.call(ctxt,
                         self.make_msg('receiver_notify', identity=identity,
                                       params=params))

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
