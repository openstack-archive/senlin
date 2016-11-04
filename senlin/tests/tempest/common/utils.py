# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import functools

from tempest.lib.common.utils import data_utils
from tempest.lib import exceptions

from senlin.tests.tempest.common import constants


def api_microversion(api_microversion):
    """Decorator used to specify api_microversion for test."""
    def decorator(func):
        @functools.wraps(func)
        def wrapped(self):
            old = self.client.api_microversion
            self.client.api_microversion = api_microversion
            func(self)
            self.client.api_microversion = old
        return wrapped
    return decorator


def create_a_profile(base, spec=None, name=None, metadata=None):
    """Utility function that generates a Senlin profile."""

    if spec is None:
        spec = constants.spec_nova_server

    if name is None:
        name = data_utils.rand_name("tempest-created-profile")

    params = {
        'profile': {
            'name': name,
            'spec': spec,
            'metadata': metadata,
        }
    }
    res = base.client.create_obj('profiles', params)
    return res['body']['id']


def delete_a_profile(base, profile_id, ignore_missing=False):
    """Utility function that deletes a Senlin profile."""
    res = base.client.delete_obj('profiles', profile_id)
    if res['status'] == 404:
        if ignore_missing:
            return
        raise exceptions.NotFound()


def create_a_cluster(base, profile_id, desired_capacity=0, min_size=0,
                     max_size=-1, timeout=None, metadata=None, name=None,
                     wait_timeout=None):
    """Utility function that generates a Senlin cluster.

    Create a cluster and return it after it is ACTIVE. The function is used for
    deduplicate code in API tests where an 'existing' cluster is needed.
    """
    if name is None:
        name = data_utils.rand_name("tempest-created-cluster")
    params = {
        'cluster': {
            'profile_id': profile_id,
            'desired_capacity': desired_capacity,
            'min_size': min_size,
            'max_size': max_size,
            'timeout': timeout,
            'metadata': metadata,
            'name': name
        }
    }
    res = base.client.create_obj('clusters', params)
    cluster_id = res['body']['id']
    action_id = res['location'].split('/actions/')[1]
    base.client.wait_for_status('actions', action_id, 'SUCCEEDED',
                                wait_timeout)

    return cluster_id


def update_a_cluster(base, cluster_id, profile_id=None, name=None,
                     expected_status='SUCCEEDED', metadata=None,
                     timeout=None, wait_timeout=None):
    """Utility function that updates a Senlin cluster.

    Update a cluster and return it after it is ACTIVE.
    """
    params = {
        'cluster': {
            'profile_id': profile_id,
            'metadata': metadata,
            'name': name,
            'timeout': timeout
        }
    }
    res = base.client.update_obj('clusters', cluster_id, params)
    action_id = res['location'].split('/actions/')[1]
    base.client.wait_for_status('actions', action_id, expected_status,
                                wait_timeout)
    return res['body']


def get_a_cluster(base, cluster_id):
    """Utility function that gets a Senlin cluster."""
    res = base.client.get_obj('clusters', cluster_id)
    return res['body']


def list_clusters(base):
    """Utility function that lists Senlin clusters."""
    res = base.client.list_objs('clusters')
    return res['body']


def delete_a_cluster(base, cluster_id, wait_timeout=None):
    """Utility function that deletes a Senlin cluster."""
    res = base.client.delete_obj('clusters', cluster_id)
    action_id = res['location'].split('/actions/')[1]
    base.client.wait_for_status('actions', action_id, 'SUCCEEDED',
                                wait_timeout)
    return


def create_a_node(base, profile_id, cluster_id=None, metadata=None,
                  role=None, name=None, wait_timeout=None):
    """Utility function that creates a node.

    Create a node and return it after it is ACTIVE. This function is for
    minimizing the code duplication that could happen in API tests where
    an 'existing' Senlin node is needed.
    """
    if name is None:
        name = data_utils.rand_name("tempest-created-node")

    params = {
        'node': {
            'profile_id': profile_id,
            'cluster_id': cluster_id,
            'metadata': metadata,
            'role': role,
            'name': name
        }
    }
    res = base.client.create_obj('nodes', params)
    node_id = res['body']['id']
    action_id = res['location'].split('/actions/')[1]
    base.client.wait_for_status('actions', action_id, 'SUCCEEDED',
                                wait_timeout)
    res = base.client.get_obj('nodes', node_id)
    return res['body']['id']


def get_a_node(base, node_id, show_details=False):
    """Utility function that gets a Senlin node."""
    params = None
    if show_details:
        params = {'show_details': True}
    res = base.client.get_obj('nodes', node_id, params)
    return res['body']


def list_nodes(base):
    """Utility function that lists Senlin nodes."""
    res = base.client.list_objs('nodes')
    return res['body']


def update_a_node(base, node_id, profile_id=None, name=None,
                  metadata=None, role=None, wait_timeout=None):
    """Utility function that updates a Senlin node.

    Update a node and return it after it is ACTIVE.
    """
    params = {
        'node': {
            'profile_id': profile_id,
            'metadata': metadata,
            'name': name,
            'role': role
        }
    }
    res = base.client.update_obj('nodes', node_id, params)
    action_id = res['location'].split('/actions/')[1]
    base.client.wait_for_status('actions', action_id, 'SUCCEEDED',
                                wait_timeout)

    return res['body']['status_reason']


def delete_a_node(base, node_id, wait_timeout=None):
    """Utility function that deletes a Senlin node."""
    res = base.client.delete_obj('nodes', node_id)
    action_id = res['location'].split('/actions/')[1]
    base.client.wait_for_status('actions', action_id, 'SUCCEEDED',
                                wait_timeout)
    return


def create_a_policy(base, spec=None, name=None):
    """Utility function that generates a Senlin policy."""

    params = {
        'policy': {
            'name': name or data_utils.rand_name("tempest-created-policy"),
            'spec': spec or constants.spec_scaling_policy
        }
    }
    res = base.client.create_obj('policies', params)
    return res['body']['id']


def get_a_policy(base, policy_id):
    """Utility function that gets a Senlin policy."""
    res = base.client.get_obj('policies', policy_id)
    return res['body']


def delete_a_policy(base, policy_id, ignore_missing=False):
    """Utility function that deletes a policy."""
    res = base.client.delete_obj('policies', policy_id)
    if res['status'] == 404:
        if ignore_missing:
            return
        raise exceptions.NotFound()
    return


def cluster_attach_policy(base, cluster_id, policy_id,
                          expected_status='SUCCEEDED', wait_timeout=None):
    """Utility function that attach a policy to cluster."""

    params = {
        'policy_attach': {
            'enabled': True,
            'policy_id': policy_id
        }
    }
    res = base.client.trigger_action('clusters', cluster_id, params=params)
    action_id = res['location'].split('/actions/')[1]
    res = base.client.wait_for_status('actions', action_id, expected_status,
                                      wait_timeout)

    return res['body']['status_reason']


def cluster_detach_policy(base, cluster_id, policy_id,
                          expected_status='SUCCEEDED', wait_timeout=None):
    """Utility function that detach a policy from cluster."""

    params = {
        'policy_detach': {
            'policy_id': policy_id
        }
    }
    res = base.client.trigger_action('clusters', cluster_id, params=params)
    action_id = res['location'].split('/actions/')[1]
    res = base.client.wait_for_status('actions', action_id, expected_status,
                                      wait_timeout)
    return res['body']['status_reason']


def cluster_replace_nodes(base, cluster_id, nodes,
                          expected_status='SUCCEEDED', wait_timeout=None):
    """Utility function that replace nodes of cluster."""

    params = {
        'replace_nodes': {
            'nodes': nodes
        }
    }
    res = base.client.cluster_replace_nodes('clusters', cluster_id,
                                            params=params)
    action_id = res['location'].split('/actions/')[1]
    res = base.client.wait_for_status('actions', action_id, expected_status,
                                      wait_timeout)
    return res['body']['status_reason']


def cluster_add_nodes(base, cluster_id, nodes, expected_status='SUCCEEDED',
                      wait_timeout=None):
    """Utility function that add nodes to cluster."""

    params = {
        'add_nodes': {
            'nodes': nodes
        }
    }
    res = base.client.trigger_action('clusters', cluster_id, params=params)
    action_id = res['location'].split('/actions/')[1]
    res = base.client.wait_for_status('actions', action_id, expected_status,
                                      wait_timeout)
    return res['body']['status_reason']


def cluster_del_nodes(base, cluster_id, nodes, expected_status='SUCCEEDED',
                      wait_timeout=None):
    """Utility function that delete nodes from cluster."""

    params = {
        'del_nodes': {
            'nodes': nodes
        }
    }
    res = base.client.trigger_action('clusters', cluster_id, params=params)
    action_id = res['location'].split('/actions/')[1]
    res = base.client.wait_for_status('actions', action_id, expected_status,
                                      wait_timeout)
    return res['body']['status_reason']


def cluster_scale_out(base, cluster_id, count=None,
                      expected_status='SUCCEEDED', wait_timeout=None):
    """Utility function that scale out cluster."""

    params = {
        'scale_out': {
            'count': count
        }
    }
    res = base.client.trigger_action('clusters', cluster_id, params=params)
    action_id = res['location'].split('/actions/')[1]
    res = base.client.wait_for_status('actions', action_id, expected_status,
                                      wait_timeout)
    return res['body']['status_reason']


def cluster_scale_in(base, cluster_id, count=None,
                     expected_status='SUCCEEDED', wait_timeout=None):
    """Utility function that scale in cluster."""

    params = {
        'scale_in': {
            'count': count
        }
    }
    res = base.client.trigger_action('clusters', cluster_id, params=params)
    action_id = res['location'].split('/actions/')[1]
    res = base.client.wait_for_status('actions', action_id, expected_status,
                                      wait_timeout)
    return res['body']['status_reason']


def cluster_resize(base, cluster_id, adj_type=None, number=None, min_size=None,
                   max_size=None, min_step=None, strict=True,
                   expected_status='SUCCEEDED', wait_timeout=None):
    """Utility function that resize cluster."""

    params = {
        'resize': {
            'adjustment_type': adj_type,
            'number': number,
            'min_size': min_size,
            'max_size': max_size,
            'min_step': min_step,
            'strict': strict
        }
    }
    res = base.client.trigger_action('clusters', cluster_id, params=params)
    action_id = res['location'].split('/actions/')[1]
    res = base.client.wait_for_status('actions', action_id, expected_status,
                                      wait_timeout)
    return res['body']['status_reason']


def create_a_receiver(base, cluster_id, action, r_type=None, name=None,
                      params=None):
    """Utility function that generates a Senlin receiver."""

    if name is None:
        name = data_utils.rand_name("tempest-created-receiver")

    body = {
        'receiver': {
            'name': name,
            'cluster_id': cluster_id,
            'type': r_type or 'webhook',
            'action': action,
            'params': params or {}
        }
    }
    res = base.client.create_obj('receivers', body)
    return res['body']['id']


def get_a_receiver(base, receiver_id):
    """Utility function that gets a Senlin receiver."""
    res = base.client.get_obj('receivers', receiver_id)
    return res['body']


def delete_a_receiver(base, receiver_id, ignore_missing=False):
    """Utility function that deletes a Senlin receiver."""
    res = base.client.delete_obj('receivers', receiver_id)
    if res['status'] == 404:
        if ignore_missing:
            return
        raise exceptions.NotFound()


def create_a_keypair(base, name=None):
    """Utility function that creates a Nova keypair."""
    if name is None:
        name = data_utils.rand_name("tempest-created-keypair")
    body = base.admin_manager.keypairs_client.create_keypair(name=name)
    return body['keypair']['name']


def delete_a_keypair(base, name):
    """Utility function that deletes a Nova keypair."""
    base.admin_manager.keypairs_client.delete_keypair(name)


def post_messages(base, queue_name, messages):
    """Utility function that posts message(s) to Zaqar queue."""
    res = base.messaging_client.post_messages(queue_name,
                                              {'messages': messages})
    if res['status'] != 201:
        msg = 'Failed in posting messages to Zaqar queue %s' % queue_name
        raise Exception(msg)
