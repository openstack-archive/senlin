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

# When objects are registered, an attribute is set on this module
# automatically, pointing to the latest version of the object.


def register_all():
    # Objects should be imported here in order to be registered by services
    # that may need to receive it via RPC.
    __import__('senlin.objects.action')
    __import__('senlin.objects.cluster')
    __import__('senlin.objects.cluster_lock')
    __import__('senlin.objects.cluster_policy')
    __import__('senlin.objects.credential')
    __import__('senlin.objects.dependency')
    __import__('senlin.objects.event')
    __import__('senlin.objects.health_registry')
    __import__('senlin.objects.node')
    __import__('senlin.objects.node_lock')
    __import__('senlin.objects.notification')
    __import__('senlin.objects.policy')
    __import__('senlin.objects.profile')
    __import__('senlin.objects.receiver')
    __import__('senlin.objects.requests.actions')
    __import__('senlin.objects.requests.build_info')
    __import__('senlin.objects.requests.clusters')
    __import__('senlin.objects.requests.cluster_policies')
    __import__('senlin.objects.requests.credentials')
    __import__('senlin.objects.requests.events')
    __import__('senlin.objects.requests.nodes')
    __import__('senlin.objects.requests.policies')
    __import__('senlin.objects.requests.policy_type')
    __import__('senlin.objects.requests.profiles')
    __import__('senlin.objects.requests.profile_type')
    __import__('senlin.objects.requests.receivers')
    __import__('senlin.objects.requests.webhooks')
    __import__('senlin.objects.service')
