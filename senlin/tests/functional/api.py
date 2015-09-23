# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

from oslo_serialization import jsonutils
import requests


def create_cluster(client, name, profile_id, desired_capacity,
                   min_size=0, max_size=-1, parent=None,
                   metadata={}, timeout=120):
    rel_url = 'clusters'
    status = [200]
    data = {
        'cluster': {
            'name': name,
            'profile_id': profile_id,
            'desired_capacity': desired_capacity,
            'min_size': min_size,
            'max_size': max_size,
            'parent': parent,
            'metadata': metadata,
            'timeout': timeout,
        }
    }
    body = jsonutils.dumps(data)
    resp = client.api_request('POST', rel_url, body=body,
                              resp_status=status)
    cluster = resp.body['cluster']
    return cluster


def get_cluster(client, cluster_id, ignore_missing=False):
    rel_url = 'clusters/%(id)s' % {'id': cluster_id}
    status = [200, 404] if ignore_missing else [200]
    resp = client.api_request('GET', rel_url, resp_status=status)
    return resp if ignore_missing else resp.body['cluster']


def list_clusters(client, **query):
    rel_url = 'clusters'
    status = [200]
    resp = client.api_request('GET', rel_url, resp_status=status)
    return resp.body['clusters']


def action_cluster(client, cluster_id, action_name, params=None):
    rel_url = 'clusters/%(id)s/action' % {'id': cluster_id}
    status = [200]
    data = {
        action_name: {} if params is None else params
    }
    body = jsonutils.dumps(data)
    resp = client.api_request('PUT', rel_url, body=body,
                              resp_status=status)
    action_id = resp.body['action']
    return action_id


def delete_cluster(client, cluster_id):
    rel_url = 'clusters/%(id)s' % {'id': cluster_id}
    status = [204]
    client.api_request('DELETE', rel_url, resp_status=status)
    return


def create_node(client, name, profile_id, cluster_id=None, role=None,
                metadata=None):
    rel_url = 'nodes'
    status = [200]
    data = {
        'node': {
            'name': name,
            'profile_id': profile_id,
            'cluster_id': cluster_id,
            'role': role,
            'metadata': metadata
        }
    }
    body = jsonutils.dumps(data)
    resp = client.api_request('POST', rel_url, body=body,
                              resp_status=status)
    node = resp.body['node']
    return node


def get_node(client, node_id, ignore_missing=False):
    rel_url = 'nodes/%(id)s' % {'id': node_id}
    status = [200, 404] if ignore_missing else [200]
    resp = client.api_request('GET', rel_url, resp_status=status)
    return resp if ignore_missing else resp.body['node']


def list_nodes(client, **query):
    rel_url = 'nodes'
    status = [200]
    resp = client.api_request('GET', rel_url, resp_status=status)
    return resp.body['nodes']


def action_node(client, node_id, action_name, params=None):
    rel_url = 'nodes/%(id)s/action' % {'id': node_id}
    status = [200]
    data = {
        action_name: {} if params is None else params
    }
    body = jsonutils.dumps(data)
    resp = client.api_request('PUT', rel_url, body=body,
                              resp_status=status)
    action_id = resp.body['action']
    return action_id


def delete_node(client, node_id):
    rel_url = 'nodes/%(id)s' % {'id': node_id}
    status = [200]
    client.api_request('DELETE', rel_url, resp_status=status)
    return


def create_profile(client, name, spec, permission=None, metadata={}):
    rel_url = 'profiles'
    status = [200]
    data = {
        'profile': {
            'name': name,
            'spec': spec,
            'permission': permission,
            'metadata': metadata,
        }
    }
    body = jsonutils.dumps(data)
    resp = client.api_request('POST', rel_url, body=body,
                              resp_status=status)
    profile = resp.body['profile']
    return profile


def delete_profile(client, profile_id):
    rel_url = 'profiles/%(id)s' % {'id': profile_id}
    status = [204]
    client.api_request('DELETE', rel_url, resp_status=status)
    return


def list_policy_types(client, **query):
    rel_url = 'policy_types'
    status = [200]
    resp = client.api_request('GET', rel_url, resp_status=status)
    return resp.body['policy_types']


def create_policy(client, name, spec, level=0, cooldown=0):
    rel_url = 'policies'
    status = [200]
    data = {
        'policy': {
            'name': name,
            'spec': spec,
            'level': level,
            'cooldown': cooldown,
        }
    }
    body = jsonutils.dumps(data)
    resp = client.api_request('POST', rel_url, body=body,
                              resp_status=status)
    policy = resp.body['policy']
    return policy


def delete_policy(client, policy_id):
    rel_url = 'policies/%(id)s' % {'id': policy_id}
    status = [204]
    client.api_request('DELETE', rel_url, resp_status=status)
    return


def create_webhook(client, name, obj_type, obj_id, action,
                   credential=None, params=None):
    rel_url = 'webhooks'
    status = [200]
    data = {
        'webhook': {
            'name': name,
            'obj_type': obj_type,
            'obj_id': obj_id,
            'action': action,
            'credential': credential,
            'params': params
        }
    }
    body = jsonutils.dumps(data)
    resp = client.api_request('POST', rel_url, body=body,
                              resp_status=status)

    webhook = resp.body['webhook']
    return webhook


def get_webhook(client, webhook_id, ignore_missing=False):
    rel_url = 'webhooks/%(id)s' % {'id': webhook_id}
    status = [200, 404] if ignore_missing else [200]
    resp = client.api_request('GET', rel_url, resp_status=status)
    return resp if ignore_missing else resp.body['webhook']


def trigger_webhook(webhook_url, params=None):
    body = None
    if params is not None:
        body = jsonutils.dumps(params)
    resp = requests.request('POST', webhook_url, data=body)
    if resp.content:
        resp_body = jsonutils.loads(resp.content)
        if 'action' in resp_body:
            return resp_body['action']

    raise Exception('Webhook %s triggering failed.' % webhook_url)


def delete_webhook(client, webhook_id):
    rel_url = 'webhooks/%(id)s' % {'id': webhook_id}
    status = [204]
    client.api_request('DELETE', rel_url, resp_status=status)
    return


def get_action(client, action_id, ignore_missing=False):
    rel_url = 'actions/%(id)s' % {'id': action_id}
    status = [200, 404] if ignore_missing else [200]
    resp = client.api_request('GET', rel_url, resp_status=status)
    return resp if ignore_missing else resp.body['action']
