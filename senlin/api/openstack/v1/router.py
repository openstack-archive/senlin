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

from senlin.api.common import wsgi
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
from senlin.api.openstack.v1 import receivers
from senlin.api.openstack.v1 import services
from senlin.api.openstack.v1 import version
from senlin.api.openstack.v1 import webhooks


class API(wsgi.Router):
    '''WSGI router for Cluster v1 REST API requests.'''

    def __init__(self, conf, **local_conf):
        self.conf = conf
        mapper = routes.Mapper()

        # version
        res = wsgi.Resource(version.VersionController(conf))
        with mapper.submapper(controller=res) as sub_mapper:

            sub_mapper.connect("version",
                               "/",
                               action="version",
                               conditions={'method': 'GET'})

        # Profile_types
        res = wsgi.Resource(profile_types.ProfileTypeController(conf))
        with mapper.submapper(controller=res) as sub_mapper:

            sub_mapper.connect("profile_type_index",
                               "/profile-types",
                               action="index",
                               conditions={'method': 'GET'})
            sub_mapper.connect("profile_type_get",
                               "/profile-types/{type_name}",
                               action="get",
                               conditions={'method': 'GET'})
            sub_mapper.connect("profile_type_ops",
                               "/profile-types/{type_name}/ops",
                               action="ops",
                               conditions={'method': 'GET'})

        # Profiles
        res = wsgi.Resource(profiles.ProfileController(conf))
        with mapper.submapper(controller=res) as sub_mapper:

            sub_mapper.connect("profile_index",
                               "/profiles",
                               action="index",
                               conditions={'method': 'GET'})
            sub_mapper.connect("profile_create",
                               "/profiles",
                               action="create",
                               conditions={'method': 'POST'},
                               success=201)
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
            sub_mapper.connect("profile_validate",
                               "/profiles/validate",
                               action="validate",
                               conditions={'method': 'POST'})

        # Policy Types
        res = wsgi.Resource(policy_types.PolicyTypeController(conf))
        with mapper.submapper(controller=res) as sub_mapper:
            # Policy collection
            sub_mapper.connect("policy_type_index",
                               "/policy-types",
                               action="index",
                               conditions={'method': 'GET'})
            sub_mapper.connect("policy_type_get",
                               "/policy-types/{type_name}",
                               action="get",
                               conditions={'method': 'GET'})

        # Policies
        res = wsgi.Resource(policies.PolicyController(conf))
        with mapper.submapper(controller=res) as sub_mapper:

            sub_mapper.connect("policy_index",
                               "/policies",
                               action="index",
                               conditions={'method': 'GET'})
            sub_mapper.connect("policy_create",
                               "/policies",
                               action="create",
                               conditions={'method': 'POST'},
                               success=201)
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
            sub_mapper.connect("policy_validate",
                               "/policies/validate",
                               action="validate",
                               conditions={'method': 'POST'})

        # Clusters
        res = wsgi.Resource(clusters.ClusterController(conf))
        with mapper.submapper(controller=res) as sub_mapper:

            sub_mapper.connect("cluster_index",
                               "/clusters",
                               action="index",
                               conditions={'method': 'GET'})
            sub_mapper.connect("cluster_create",
                               "/clusters",
                               action="create",
                               conditions={'method': 'POST'},
                               success=202)
            sub_mapper.connect("cluster_get",
                               "/clusters/{cluster_id}",
                               action="get",
                               conditions={'method': 'GET'})
            sub_mapper.connect("cluster_update",
                               "/clusters/{cluster_id}",
                               action="update",
                               conditions={'method': 'PATCH'},
                               success=202)
            sub_mapper.connect("cluster_action",
                               "/clusters/{cluster_id}/actions",
                               action="action",
                               conditions={'method': 'POST'},
                               success=202)
            sub_mapper.connect("cluster_collect",
                               "/clusters/{cluster_id}/attrs/{path}",
                               action="collect",
                               conditions={'method': 'GET'})
            sub_mapper.connect("cluster_delete",
                               "/clusters/{cluster_id}",
                               action="delete",
                               conditions={'method': 'DELETE'},
                               success=202)
            sub_mapper.connect("cluster_operation",
                               "/clusters/{cluster_id}/ops",
                               action="operation",
                               conditions={'method': 'POST'},
                               success=202)

        # Nodes
        res = wsgi.Resource(nodes.NodeController(conf))
        with mapper.submapper(controller=res) as sub_mapper:

            sub_mapper.connect("node_index",
                               "/nodes",
                               action="index",
                               conditions={'method': 'GET'})
            sub_mapper.connect("node_create",
                               "/nodes",
                               action="create",
                               conditions={'method': 'POST'},
                               success=202)
            sub_mapper.connect("node_adopt",
                               "/nodes/adopt",
                               action="adopt",
                               conditions={'method': 'POST'})
            sub_mapper.connect("node_adopt_preview",
                               "/nodes/adopt-preview",
                               action="adopt_preview",
                               conditions={'method': 'POST'})
            sub_mapper.connect("node_get",
                               "/nodes/{node_id}",
                               action="get",
                               conditions={'method': 'GET'})
            sub_mapper.connect("node_update",
                               "/nodes/{node_id}",
                               action="update",
                               conditions={'method': 'PATCH'},
                               success=202)
            sub_mapper.connect("node_action",
                               "/nodes/{node_id}/actions",
                               action="action",
                               conditions={'method': 'POST'},
                               success=202)
            sub_mapper.connect("node_delete",
                               "/nodes/{node_id}",
                               action="delete",
                               conditions={'method': 'DELETE'},
                               success=202)
            sub_mapper.connect("node_operation",
                               "/nodes/{node_id}/ops",
                               action="operation",
                               conditions={'method': 'POST'},
                               success=202)

        # Cluster Policies
        res = wsgi.Resource(cluster_policies.ClusterPolicyController(conf))
        policies_path = "/clusters/{cluster_id}"
        with mapper.submapper(controller=res,
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
        res = wsgi.Resource(actions.ActionController(conf))
        with mapper.submapper(controller=res) as sub_mapper:

            sub_mapper.connect("action_index",
                               "/actions",
                               action="index",
                               conditions={'method': 'GET'})
            sub_mapper.connect("action_create",
                               "/actions",
                               action="create",
                               conditions={'method': 'POST'},
                               success=201)
            sub_mapper.connect("action_get",
                               "/actions/{action_id}",
                               action="get",
                               conditions={'method': 'GET'})

        # Receivers
        res = wsgi.Resource(receivers.ReceiverController(conf))
        with mapper.submapper(controller=res) as sub_mapper:

            sub_mapper.connect("receivers_index",
                               "/receivers",
                               action="index",
                               conditions={'method': 'GET'})
            sub_mapper.connect("receiver_create",
                               "/receivers",
                               action="create",
                               conditions={'method': 'POST'},
                               success=201)
            sub_mapper.connect("receiver_get",
                               "/receivers/{receiver_id}",
                               action="get",
                               conditions={'method': 'GET'})
            sub_mapper.connect("receiver_update",
                               "/receivers/{receiver_id}",
                               action="update",
                               conditions={'method': 'PATCH'})
            sub_mapper.connect("receiver_delete",
                               "/receivers/{receiver_id}",
                               action="delete",
                               conditions={'method': 'DELETE'})
            sub_mapper.connect("receiver_notify",
                               "/receivers/{receiver_id}/notify",
                               action="notify",
                               conditions={'method': 'POST'})

        # Webhooks
        res = wsgi.Resource(webhooks.WebhookController(conf))
        with mapper.submapper(controller=res) as sub_mapper:

            sub_mapper.connect("webhook_trigger",
                               "/webhooks/{webhook_id}/trigger",
                               action="trigger",
                               conditions={'method': 'POST'},
                               success=202)

        # Events
        res = wsgi.Resource(events.EventController(conf))
        with mapper.submapper(controller=res) as sub_mapper:

            sub_mapper.connect("event_index",
                               "/events",
                               action="index",
                               conditions={'method': 'GET'})
            sub_mapper.connect("event_get",
                               "/events/{event_id}",
                               action="get",
                               conditions={'method': 'GET'})

        # Info
        res = wsgi.Resource(build_info.BuildInfoController(conf))
        with mapper.submapper(controller=res) as sub_mapper:

            sub_mapper.connect("build_info",
                               "/build-info",
                               action="build_info",
                               conditions={'method': 'GET'})

        super(API, self).__init__(mapper)

        # Services
        res = wsgi.Resource(services.ServiceController(conf))
        with mapper.submapper(controller=res) as sub_mapper:

            sub_mapper.connect("service_index",
                               "/services",
                               action="index",
                               conditions={'method': 'GET'})

        super(API, self).__init__(mapper)
