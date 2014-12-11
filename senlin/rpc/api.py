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

ENGINE_TOPIC = 'engine'

PARAM_KEYS = (
    PARAM_TIMEOUT,
) = (
    'timeout_mins',
)

CLUSTER_KEYS = (
    CLUSTER_NAME, CLUSTER_ID,
    CLUSTER_CREATION_TIME, CLUSTER_UPDATED_TIME, CLUSTER_DELETION_TIME,
    CLUSTER_NOTIFICATION_TOPICS,
    CLUSTER_DESCRIPTION, CLUSTER_ACTION,
    CLUSTER_STATUS, CLUSTER_STATUS_DATA, CLUSTER_CAPABILITIES,
    CLUSTER_TIMEOUT, CLUSTER_OWNER,
    CLUSTER_PARENT
) = (
    'cluster_name', 'cluster_identity',
    'creation_time', 'updated_time', 'deletion_time',
    'notification_topics',
    'description', 'cluster_action',
    'cluster_status', 'cluster_status_reason', 'capabilities',
    'timeout_mins', 'cluster_owner',
    'parent'
)

THREAD_MESSAGES = (THREAD_CANCEL,) = ('cancel',)
