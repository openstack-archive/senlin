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

EVENT_KEYS = (
    EVENT_TIMESTAMP, EVENT_OBJ_ID, EVENT_OBJ_NAME, EVENT_OBJ_TYPE,
    EVENT_USER, EVENT_ACTION, EVENT_STATUS, EVENT_STATUS_REASON,
) = (
    'timestamp', 'obj_id', 'obj_name', 'obj_type',
    'user', 'action', 'status', 'status_reason',
)
