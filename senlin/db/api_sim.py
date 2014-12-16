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

'''
Simulate the interface for Senlin database access.
'''

import uuid


cluster_list = []

def cluster_get(context, cluster_id, show_deleted=False, tenant_safe=True,
              eager_load=False):
    for cluster in cluster_list:
        if cluster['uuid'] == cluster_id:
            return cluster_list[cluster_name]


def cluster_get_by_name(context, cluster_name):
    for cluster in cluster_list:
        if cluster['name'] == cluster_name:
            return cluster_list[cluster_name]


def cluster_get_all(context, limit=None, sort_keys=None, marker=None,
                  sort_dir=None, filters=None, tenant_safe=True,
                  show_deleted=False, show_nested=False):
    return cluster_list


def cluster_count_all(context, filters=None, tenant_safe=True,
                    show_deleted=False, show_nested=False):
    pass


def cluster_create(context, cluster):
    cluster.uuid = str(uuid.uuid4())
    return cluster_list.append(cluster)


def cluster_update(context, cluster_id, values):
    pass


def cluster_delete(context, cluster_id):
    for cluster in cluster_list:
        if cluster['uuid'] == cluster_id:
            cluster_list.remove(cluster)


# We assume these lock operations will always succeed.
# Just for test.
def cluster_lock_create(cluster_id, engine_id):
    pass


def cluster_lock_steal(cluster_id, old_engine_id, new_engine_id):
    pass


def cluster_lock_release(cluster_id, engine_id):
    pass
