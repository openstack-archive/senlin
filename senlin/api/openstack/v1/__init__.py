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
from senlin.api.openstack.v1 import cluster_policies
from senlin.api.openstack.v1 import clusters
from senlin.api.openstack.v1 import events
from senlin.api.openstack.v1 import nodes
from senlin.api.openstack.v1 import policies
from senlin.api.openstack.v1 import policy_types
from senlin.api.openstack.v1 import profile_types
from senlin.api.openstack.v1 import profiles
from senlin.api.openstack.v1 import triggers
from senlin.api.openstack.v1 import webhooks
from senlin.common import wsgi


class API(wsgi.Router):
    '''WSGI router for Cluster v1 ReST API requests.'''

    def __init__(self, conf, **local_conf):
        self.conf = conf
        mapper = routes.Mapper()

        # Profile_types
        profile_types_resource = profile_types.create_resource(conf)
        with mapper.submapper(controller=profile_types_resource,
                              path_prefix="/{tenant_id}") as sub_mapper:

            sub_mapper.connect("profile_type_index",
                               "/profile_types",
                               action="index",
                               conditions={'method': 'GET'})
            sub_mapper.connect("profile_type_schema",
                               "/profile_types/{type_name}",
                               action="schema",
                               conditions={'method': 'GET'})

        # Profiles
        profiles_resource = profiles.create_resource(conf)
        with mapper.submapper(controller=profiles_resource,
                              path_prefix="/{tenant_id}") as sub_mapper:

            sub_mapper.connect("profile_index",
                               "/profiles",
                               action="index",
                               conditions={'method': 'GET'})
            sub_mapper.connect("profile_create",
                               "/profiles",
                               action="create",
                               conditions={'method': 'POST'})
            sub_mapper.connect("profile_get",
                               "/profiles/{profile_id}",
                               action="get",
                               conditions={'method': 'GET'})
            sub_mapper.connect("profile_update",
                               "/profiles/{profile_id}",
                               action="update",
                               conditions={'method': 'PATCH'})
            sub_mapper.connect("profile_delete",
                               "/profiles/{profile_id}",
                               action="delete",
                               conditions={'method': 'DELETE'})

        # Policy Types
        policy_types_resource = policy_types.create_resource(conf)
        with mapper.submapper(controller=policy_types_resource,
                              path_prefix="/{tenant_id}") as sub_mapper:
            # Policy collection
            sub_mapper.connect("policy_type_index",
                               "/policy_types",
                               action="index",
                               conditions={'method': 'GET'})
            sub_mapper.connect("policy_type_schema",
                               "/policy_types/{type_name}",
                               action="schema",
                               conditions={'method': 'GET'})

        # Policies
        policies_resource = policies.create_resource(conf)
        with mapper.submapper(controller=policies_resource,
                              path_prefix="/{tenant_id}") as sub_mapper:

            sub_mapper.connect("policy_index",
                               "/policies",
                               action="index",
                               conditions={'method': 'GET'})
            sub_mapper.connect("policy_create",
                               "/policies",
                               action="create",
                               conditions={'method': 'POST'})
            sub_mapper.connect("policy_get",
                               "/policies/{policy_id}",
                               action="get",
                               conditions={'method': 'GET'})
            sub_mapper.connect("policy_update",
                               "/policies/{policy_id}",
                               action="update",
                               conditions={'method': 'PATCH'})
            sub_mapper.connect("policy_delete",
                               "/policies/{policy_id}",
                               action="delete",
                               conditions={'method': 'DELETE'})

        # Clusters
        clusters_resource = clusters.create_resource(conf)
        with mapper.submapper(controller=clusters_resource,
                              path_prefix="/{tenant_id}") as sub_mapper:

            sub_mapper.connect("cluster_index",
                               "/clusters",
                               action="index",
                               conditions={'method': 'GET'})
            sub_mapper.connect("cluster_create",
                               "/clusters",
                               action="create",
                               conditions={'method': 'POST'})
            sub_mapper.connect("cluster_get",
                               "/clusters/{cluster_id}",
                               action="get",
                               conditions={'method': 'GET'})
            sub_mapper.connect("cluster_update",
                               "/clusters/{cluster_id}",
                               action="update",
                               conditions={'method': 'PATCH'})
            sub_mapper.connect("cluster_action",
                               "/clusters/{cluster_id}/action",
                               action="action",
                               conditions={'method': 'PUT'})
            sub_mapper.connect("cluster_delete",
                               "/clusters/{cluster_id}",
                               action="delete",
                               conditions={'method': 'DELETE'})

        # Nodes
        nodes_resource = nodes.create_resource(conf)
        with mapper.submapper(controller=nodes_resource,
                              path_prefix="/{tenant_id}") as sub_mapper:

            sub_mapper.connect("node_index",
                               "/nodes",
                               action="index",
                               conditions={'method': 'GET'})
            sub_mapper.connect("node_create",
                               "/nodes",
                               action="create",
                               conditions={'method': 'POST'})
            sub_mapper.connect("node_get",
                               "/nodes/{node_id}",
                               action="get",
                               conditions={'method': 'GET'})
            sub_mapper.connect("node_update",
                               "/nodes/{node_id}",
                               action="update",
                               conditions={'method': 'PATCH'})
            sub_mapper.connect("node_action",
                               "/nodes/{node_id}/action",
                               action="action",
                               conditions={'method': 'PUT'})
            sub_mapper.connect("node_delete",
                               "/nodes/{node_id}",
                               action="delete",
                               conditions={'method': 'DELETE'})

        # Cluster Policies
        cluster_policies_resource = cluster_policies.create_resource(conf)
        policies_path = "/{tenant_id}/clusters/{cluster_id}"
        with mapper.submapper(controller=cluster_policies_resource,
                              path_prefix=policies_path) as sub_mapper:
            sub_mapper.connect("cluster_policy_list",
                               "/policies",
                               action="index",
                               conditions={'method': 'GET'})
            sub_mapper.connect("cluster_policy_show",
                               "/policies/{policy_id}",
                               action="get",
                               conditions={'method': 'GET'})

        # Actions
        actions_resource = actions.create_resource(conf)
        with mapper.submapper(controller=actions_resource,
                              path_prefix="/{tenant_id}") as sub_mapper:

            sub_mapper.connect("action_index",
                               "/actions",
                               action="index",
                               conditions={'method': 'GET'})
            sub_mapper.connect("action_create",
                               "/actions",
                               action="create",
                               conditions={'method': 'POST'})
            sub_mapper.connect("action_get",
                               "/actions/{action_id}",
                               action="get",
                               conditions={'method': 'GET'})

        # Webhooks
        webhooks_resource = webhooks.create_resource(conf)
        with mapper.submapper(controller=webhooks_resource,
                              path_prefix="/{tenant_id}") as sub_mapper:

            sub_mapper.connect("webhook_index",
                               "/webhooks",
                               action="index",
                               conditions={'method': 'GET'})
            sub_mapper.connect("webhook_create",
                               "/webhooks",
                               action="create",
                               conditions={'method': 'POST'})
            sub_mapper.connect("webhook_get",
                               "/webhooks/{webhook_id}",
                               action="get",
                               conditions={'method': 'GET'})
            sub_mapper.connect("webhook_trigger",
                               "/webhooks/{webhook_id}/trigger",
                               action="trigger",
                               conditions={'method': 'POST'})
            sub_mapper.connect("webhook_delete",
                               "/webhooks/{webhook_id}",
                               action="delete",
                               conditions={'method': 'DELETE'})

        # Triggers
        triggers_resource = triggers.create_resource(conf)
        with mapper.submapper(controller=triggers_resource,
                              path_prefix="/{tenant_id}") as sub_mapper:

            sub_mapper.connect("trigger_index",
                               "/triggers",
                               action="index",
                               conditions={'method': 'GET'})
            sub_mapper.connect("trigger_create",
                               "/triggers",
                               action="create",
                               conditions={'method': 'POST'})
            sub_mapper.connect("trigger_get",
                               "/triggers/{trigger_id}",
                               action="get",
                               conditions={'method': 'GET'})
            sub_mapper.connect("trigger_delete",
                               "/triggers/{trigger_id}",
                               action="delete",
                               conditions={'method': 'DELETE'})

        # Events
        events_resource = events.create_resource(conf)
        with mapper.submapper(controller=events_resource,
                              path_prefix="/{tenant_id}") as sub_mapper:

            sub_mapper.connect("event_index",
                               "/events",
                               action="index",
                               conditions={'method': 'GET'})
            sub_mapper.connect("event_get",
                               "/events/{event_id}",
                               action="get",
                               conditions={'method': 'GET'})

        # Info
        info_resource = build_info.create_resource(conf)
        with mapper.submapper(controller=info_resource,
                              path_prefix="/{tenant_id}") as sub_mapper:

            sub_mapper.connect("build_info",
                               "/build_info",
                               action="build_info",
                               conditions={'method': 'GET'})

        super(API, self).__init__(mapper)
