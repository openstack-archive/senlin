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

import routes

from senlin.api.openstack.v1 import actions
from senlin.api.openstack.v1 import build_info
from senlin.api.openstack.v1 import clusters
from senlin.common import wsgi


class API(wsgi.Router):

    """
    WSGI router for Cluster v1 ReST API requests.
    """

    def __init__(self, conf, **local_conf):
        self.conf = conf
        mapper = routes.Mapper()

        # Clusters
        clusters_resource = clusters.create_resource(conf)
        with mapper.submapper(controller=clusters_resource,
                              path_prefix="/{tenant_id}") as cluster_mapper:
            # Cluster collection
            cluster_mapper.connect("cluster_index",
                                 "/clusters",
                                 action="index",
                                 conditions={'method': 'GET'})
            cluster_mapper.connect("cluster_create",
                                 "/clusters",
                                 action="create",
                                 conditions={'method': 'POST'})
            cluster_mapper.connect("cluster_preview",
                                 "/clusters/preview",
                                 action="preview",
                                 conditions={'method': 'POST'})
            cluster_mapper.connect("cluster_detail",
                                 "/clusters/detail",
                                 action="detail",
                                 conditions={'method': 'GET'})

            # Cluster update/delete
            cluster_mapper.connect("cluster_update",
                                 "/clusters/{cluster_name}/{cluster_id}",
                                 action="update",
                                 conditions={'method': 'PUT'})
            cluster_mapper.connect("cluster_update_patch",
                                 "/clusters/{cluster_name}/{cluster_id}",
                                 action="update_patch",
                                 conditions={'method': 'PATCH'})
            cluster_mapper.connect("cluster_delete",
                                 "/clusters/{cluster_name}/{cluster_id}",
                                 action="delete",
                                 conditions={'method': 'DELETE'})

        # Actions
        actions_resource = actions.create_resource(conf)
        with mapper.submapper(controller=actions_resource,
                              path_prefix=stack_path) as ac_mapper:

            ac_mapper.connect("action_cluster",
                              "/actions",
                              action="action",
                              conditions={'method': 'POST'})

        # Info
        info_resource = build_info.create_resource(conf)
        with mapper.submapper(controller=info_resource,
                              path_prefix="/{tenant_id}") as info_mapper:

            info_mapper.connect('build_info',
                                '/build_info',
                                action='build_info',
                                conditions={'method': 'GET'})

        super(API, self).__init__(mapper)
