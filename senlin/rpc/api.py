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

ENGINE_TOPIC = 'senlin-engine'
ENGINE_DISPATCHER_TOPIC = 'engine-dispatcher'
RPC_API_VERSION = '1.0'

CLUSTER_KEYS = (
    CLUSTER_NAME, CLUSTER_PROFILE,
    CLUSTER_ID, CLUSTER_PARENT,
    CLUSTER_DOMAIN, CLUSTER_PROJECT, CLUSTER_USER,
    CLUSTER_CREATED_TIME, CLUSTER_UPDATED_TIME, CLUSTER_DELETED_TIME,
    CLUSTER_STATUS, CLUSTER_STATUS_REASON, CLUSTER_TIMEOUT,
    CLUSTER_TAGS,
) = (
    'name', 'profile_id',
    'id', 'parent',
    'domain', 'project', 'user',
    'created_time', 'updated_time', 'deleted_time',
    'status', 'status_reason', 'timeout',
    'tags',
)

NODE_KEYS = (
    NODE_INDEX, NODE_NAME,
    NODE_CREATED_TIME, NODE_UPDATED_TIME, NODE_DELETED_TIME,
    NODE_STATUS,
) = (
    'index', 'name',
    'created_time', 'updated_time', 'deleted_time',
    'status',
)

PROFILE_KEYS = (
    PROFILE_ID, PROFILE_NAME, PROFILE_TYPE, PROFILE_PERMISSION,
    PROFILE_CREATED_TIME, PROFILE_UPDATED_TIME, PROFILE_DELETED_TIME,
    PROFILE_TAGS,
) = (
    'id', 'name', 'type', 'permission',
    'created_time', 'updated_time', 'deleted_time',
    'tags',
)

EVENT_KEYS = (
    EVENT_TIMESTAMP, EVENT_OBJ_ID, EVENT_OBJ_NAME, EVENT_OBJ_TYPE,
    EVENT_USER, EVENT_ACTION, EVENT_STATUS, EVENT_STATUS_REASON,
) = (
    'timestamp', 'obj_id', 'obj_name', 'obj_type',
    'user', 'action', 'status', 'status_reason',
)

ACTION_KEYS = (
    ACTION_NAME, ACTION_TARGET, ACTION_ACTION, ACTION_CAUSE,
    ACTION_INTERVAL, ACTION_START_TIME, ACTION_END_TIME,
    ACTION_TIMEOUT, ACTION_STATUS, ACTION_STATUS_REASON,
    ACTION_INPUTS, ACTION_OUTPUTS, ACTION_DEPENDS_ON, ACTION_DEPENDED_BY,
) = (
    'name', 'target', 'action', 'cause',
    'interval', 'start_time', 'end_time',
    'timeout', 'status', 'status_reason',
    'inputs', 'outputs', 'depends_on', 'depended_by',
)
