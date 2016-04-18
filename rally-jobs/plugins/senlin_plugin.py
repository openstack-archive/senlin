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

from oslo_config import cfg

from rally.common import logging
from rally import consts
from rally import exceptions
from rally.plugins.openstack import scenario
from rally.task import atomic
from rally.task import utils
from rally.task import validation

LOG = logging.getLogger(__name__)

SENLIN_BENCHMARK_OPTS = [
    cfg.FloatOpt("senlin_action_timeout",
                 default=3600,
                 help="Time in seconds to wait for senlin action to finish."),
]

CONF = cfg.CONF
benchmark_group = cfg.OptGroup(name="benchmark", title="benchmark options")
CONF.register_opts(SENLIN_BENCHMARK_OPTS, group=benchmark_group)


class SenlinScenario(scenario.OpenStackScenario):
    """Base class for Senlin scenarios with basic atomic actions."""

    @atomic.action_timer("senlin.get_action")
    def _get_action(self, action_id):
        """Get action details.

        :param action_id: ID of action to get

        :returns: object of action
        """
        return self.admin_clients("senlin").get_action(action_id)

    @atomic.action_timer("senlin.list_clusters")
    def _list_clusters(self):
        """Return user cluster list."""

        return list(self.admin_clients("senlin").clusters())

    @atomic.action_timer("senlin.create_cluster")
    def _create_cluster(self, profile_id, desired_capacity=0, min_size=0,
                        max_size=-1, timeout=None, metadata=None):
        """Create a new cluster from attributes.

        :param profile_id: ID of profile used to create cluster
        :param desired_capacity: The capacity or initial number of nodes
                                 owned by the cluster
        :param min_size: The minimum number of nodes owned by the cluster
        :param max_size: The maximum number of nodes owned by the cluster.
                         -1 means no limit
        :param timeout: The timeout value in minutes for cluster creation
        :param metadata: A set of key value pairs to associate with the cluster

        :returns: object of cluster created.
        """
        attrs = {}
        attrs["profile_id"] = profile_id
        attrs["name"] = self.generate_random_name()
        attrs["desired_capacity"] = desired_capacity
        attrs["min_size"] = min_size
        attrs["max_size"] = max_size
        attrs["metadata"] = metadata
        if timeout:
            attrs["timeout"] = timeout

        cluster = self.admin_clients("senlin").create_cluster(**attrs)
        cluster = utils.wait_for_status(
            cluster,
            ready_statuses=["ACTIVE"],
            failure_statuses=["ERROR"],
            update_resource=self._get_cluster,
            timeout=CONF.benchmark.senlin_action_timeout)

        return cluster

    @atomic.action_timer("senlin.get_cluster")
    def _get_cluster(self, cluster):
        """Get cluster details.

        :param cluster: cluster to get

        :returns: object of cluster
        """
        try:
            return self.admin_clients("senlin").get_cluster(cluster.id)
        except Exception as e:
            if getattr(e, "code", getattr(e, "http_status", 400)) == 404:
                raise exceptions.GetResourceNotFound(resource=cluster.id)
            raise exceptions.GetResourceFailure(resource=cluster.id, err=e)

    @atomic.action_timer("senlin.delete_cluster")
    def _delete_cluster(self, cluster):
        """Delete given cluster.

        Returns after the cluster is successfully deleted.

        :param cluster: cluster object to delete
        """
        cluster = self.admin_clients("senlin").delete_cluster(cluster)
        utils.wait_for_status(
            cluster,
            # FIXME(Yanyan Hu): ready_statuses is actually useless
            # for deleting Senlin cluster since cluster db item will
            # be removed once cluster is deleted successfully.
            ready_statuses=["DELETED"],
            failure_statuses=["ERROR"],
            check_deletion=True,
            update_resource=self._get_cluster,
            timeout=CONF.benchmark.senlin_action_timeout)

    @atomic.action_timer("senlin.create_profile")
    def _create_profile(self, spec, metadata=None):
        """Create a new profile from attributes.

        :param spec: spec dictionary used to create profile
        :param metadata: A set of key value pairs to associate with the
                         profile

        :returns: object of profile created
        """
        attrs = {}
        attrs["spec"] = spec
        attrs["name"] = self.generate_random_name()
        if metadata:
            attrs["metadata"] = metadata

        return self.admin_clients("senlin").create_profile(**attrs)

    @atomic.action_timer("senlin.get_profile")
    def _get_profile(self, profile_id):
        """Get profile details.

        :param profile_id: ID of profile to get

        :returns: object of profile
        """
        return self.admin_clients("senlin").get_profile(profile_id)

    @atomic.action_timer("senlin.delete_profile")
    def _delete_profile(self, profile):
        """Delete given profile.

        Returns after the profile is successfully deleted.

        :param profile: profile object to be deleted
        """
        self.admin_clients("senlin").delete_profile(profile)

    @validation.required_openstack(admin=True)
    @validation.required_services(consts.Service.SENLIN)
    @scenario.configure(context={"cleanup": ["senlin"]})
    def create_and_delete_profile_cluster(self, profile_spec,
                                          desired_capacity=0, min_size=0,
                                          max_size=-1, timeout=120,
                                          metadata=None):
        """Create a profile and a cluster and then delete them.

        Measure the "senlin profile-create", "senlin profile-delete",
        "senlin cluster-create" and "senlin cluster-delete" commands
        performance.

        :param profile_spec: spec dictionary used to create profile
        :param desired_capacity: The capacity or initial number of nodes
                                 owned by the cluster
        :param min_size: The minimum number of nodes owned by the cluster
        :param max_size: The maximum number of nodes owned by the cluster.
                         -1 means no limit
        :param timeout: The timeout value in minutes for cluster creation
        :param metadata: A set of key value pairs to associate with the cluster
        """
        profile = self._create_profile(profile_spec)
        cluster = self._create_cluster(profile.id, desired_capacity,
                                       min_size, max_size, timeout, metadata)
        self._delete_cluster(cluster.id)
        self._delete_profile(profile)
