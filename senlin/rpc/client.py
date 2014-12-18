#
# Copyright 2012, Red Hat, Inc.
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

"""
Client side of the senlin engine RPC API.
"""

from senlin.common import messaging
from senlin.rpc import api as rpc_api


class EngineClient(object):
    '''Client side of the senlin engine rpc API.

    API version history::

        1.0 - Initial version.
    '''

    BASE_RPC_API_VERSION = '1.0'

    def __init__(self):
        self._client = messaging.get_rpc_client(
            topic=rpc_api.ENGINE_TOPIC,
            server=rpc_api.ENGINE_SERVER,
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

    def list_clusters(self, ctxt, limit=None, marker=None, sort_keys=None,
                    sort_dir=None, filters=None, tenant_safe=True,
                    show_deleted=False, show_nested=False):
        """
        The list_clusters method returns attributes of all clusters.  It supports
        pagination (``limit`` and ``marker``), sorting (``sort_keys`` and
        ``sort_dir``) and filtering (``filters``) of the results.

        :param ctxt: RPC context.
        :param limit: the number of clusters to list (integer or string)
        :param marker: the ID of the last item in the previous page
        :param sort_keys: an array of fields used to sort the list
        :param sort_dir: the direction of the sort ('asc' or 'desc')
        :param filters: a dict with attribute:value to filter the list
        :param tenant_safe: if true, scope the request by the current tenant
        :param show_deleted: if true, show soft-deleted clusters
        :param show_nested: if true, show nested clusters
        :returns: a list of clusters
        """
        return self.call(ctxt,
                         self.make_msg('list_clusters', limit=limit,
                                       sort_keys=sort_keys, marker=marker,
                                       sort_dir=sort_dir, filters=filters,
                                       tenant_safe=tenant_safe,
                                       show_deleted=show_deleted,
                                       show_nested=show_nested))

    def show_cluster(self, ctxt, cluster_identity):
        """
        Return detailed information about one or all clusters.
        :param ctxt: RPC context.
        :param cluster_identity: Name of the cluster you want to show, or None to
        show all
        """
        return self.call(ctxt, self.make_msg('show_cluster',
                                             cluster_identity=cluster_identity))

    def create_cluster(self, ctxt, cluster_name, size, profile):
        """
        The create_cluster method creates a new cluster using the args
        provided.

        :param ctxt: RPC context.
        :param cluster_name: Name of the cluster you want to create.
        :param size: Size of the cluster you want to create.
        :param profile: Profile used to create the cluster
        """
        return self._create_cluster(ctxt, cluster_name, size, profile)

    def _create_cluster(self, ctxt, cluster_name, size, profile,
                      owner_id=None, nested_depth=0, user_creds_id=None,
                      cluster_user_project_id=None):
        """
        Internal create_cluster interface for engine-to-engine communication via
        RPC.  Allows some additional options which should not be exposed to
        users via the API:
        :param owner_id: parent cluster ID for nested clusters
        :param nested_depth: nested depth for nested clusters
        :param user_creds_id: user_creds record for nested cluster
        :param cluster_user_project_id: cluster user project for nested cluster
        """
        return self.call(
            ctxt, self.make_msg('create_cluster', cluster_name=cluster_name,
                                size=size,
                                profile=profile,
                                owner_id=owner_id,
                                nested_depth=nested_depth,
                                user_creds_id=user_creds_id,
                                cluster_user_project_id=cluster_user_project_id))

    def update_cluster(self, ctxt, cluster_identity, profile):
        """
        The update_cluster method updates an existing cluster based on the
        provided template and parameters.

        :param ctxt: RPC context.
        :param cluster_identity: Identity of the cluster you want to update.
        :param size: Size of the cluster you want to create.
        :param profile: Profile used to create the cluster
        """
        return self.call(ctxt, self.make_msg('update_cluster',
                                             cluster_identity=cluster_identity,
                                             profile=profile))

    def delete_cluster(self, ctxt, cluster_identity, cast=True):
        """
        The delete_cluster method deletes a given cluster.

        :param ctxt: RPC context.
        :param cluster_identity: Name of the cluster you want to delete.
        :param cast: cast the message or use call (default: True)
        """
        rpc_method = self.cast if cast else self.call
        return rpc_method(ctxt,
                          self.make_msg('delete_cluster',
                                        cluster_identity=cluster_identity))

    def list_cluster_members(self, ctxt, cluster_identity, nested_depth=0):
        """
        List the members belonging to a cluster.
        :param ctxt: RPC context.
        :param cluster_identity: Name of the cluster.
        :param nested_depth: Levels of nested clusters of which list members.
        """
        return self.call(ctxt, self.make_msg('list_cluster_members',
                                             cluster_identity=cluster_identity,
                                             nested_depth=nested_depth))

    def cluster_suspend(self, ctxt, cluster_identity):
        return self.call(ctxt, self.make_msg('cluster_suspend',
                                             cluster_identity=cluster_identity))

    def cluster_resume(self, ctxt, cluster_identity):
        return self.call(ctxt, self.make_msg('cluster_resume',
                                             cluster_identity=cluster_identity))

    def get_revision(self, ctxt):
        return self.call(ctxt, self.make_msg('get_revision'))
