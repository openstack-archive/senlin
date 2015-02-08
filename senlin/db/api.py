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

'''
Interface for database access.

SQLAlchemy is currently the only supported backend.
'''

from oslo_config import cfg
from oslo_db import api

CONF = cfg.CONF


_BACKEND_MAPPING = {'sqlalchemy': 'senlin.db.sqlalchemy.api'}

IMPL = api.DBAPI.from_config(CONF, backend_mapping=_BACKEND_MAPPING)


def get_engine():
    return IMPL.get_engine()


def get_session():
    return IMPL.get_session()


# Clusters
def cluster_create(context, values):
    return IMPL.cluster_create(context, values)


def cluster_get(context, cluster_id, show_deleted=False, tenant_safe=True):
    return IMPL.cluster_get(context, cluster_id, show_deleted=show_deleted,
                            tenant_safe=tenant_safe)


def cluster_get_by_name(context, cluster_name):
    return IMPL.cluster_get_by_name(context, cluster_name)


def cluster_get_by_short_id(context, short_id):
    return IMPL.cluster_get_by_short_id(context, short_id)


def cluster_get_next_index(context, cluster_id):
    return IMPL.cluster_get_next_index(context, cluster_id)


def cluster_get_by_name_and_parent(context, cluster_name, parent):
    return IMPL.cluster_get_by_name_and_parent(context, cluster_name, parent)


def cluster_get_all(context, limit=None, marker=None, sort_keys=None,
                    sort_dir=None, filters=None, tenant_safe=True,
                    show_deleted=False, show_nested=False):
    return IMPL.cluster_get_all(context, limit, marker, sort_keys, sort_dir,
                                filters, tenant_safe, show_deleted,
                                show_nested)


def cluster_get_all_by_parent(context, parent):
    return IMPL.cluster_get_all_by_parent(context, parent)


def cluster_count_all(context, filters=None, tenant_safe=True,
                      show_deleted=False, show_nested=False):
    return IMPL.cluster_count_all(context, filters=filters,
                                  tenant_safe=tenant_safe,
                                  show_deleted=show_deleted,
                                  show_nested=show_nested)


def cluster_update(context, cluster_id, values):
    return IMPL.cluster_update(context, cluster_id, values)


def cluster_delete(context, cluster_id):
    return IMPL.cluster_delete(context, cluster_id)


# Nodes
def node_create(context, values):
    return IMPL.node_create(context, values)


def node_get(context, node_id, show_deleted=False):
    return IMPL.node_get(context, node_id, show_deleted=show_deleted)


def node_get_by_name(context, name, show_deleted=False):
    return IMPL.node_get_by_name(context, name, show_deleted=show_deleted)


def node_get_by_short_id(context, short_id):
    return IMPL.node_get_by_short_id(context, short_id)


def node_get_all(context, cluster_id=None, show_deleted=False,
                 limit=None, marker=None, sort_keys=None, sort_dir=None,
                 filters=None, tenant_safe=True):
    return IMPL.node_get_all(context, cluster_id=cluster_id,
                             show_deleted=show_deleted,
                             limit=limit, marker=marker,
                             sort_keys=sort_keys, sort_dir=sort_dir,
                             filters=filters, tenant_safe=tenant_safe)


def node_get_all_by_cluster(context, cluster_id):
    return IMPL.node_get_all_by_cluster(context, cluster_id)


def node_get_by_name_and_cluster(context, node_name, cluster_id):
    return IMPL.node_get_by_name_and_cluster(context,
                                             node_name, cluster_id)


def node_get_by_physical_id(context, physical_id):
    return IMPL.node_get_by_physical_id(context, physical_id)


def node_update(context, node_id, values):
    return IMPL.node_update(context, node_id, values)


def node_migrate(context, node_id, to_cluster, timestamp):
    return IMPL.node_migrate(context, node_id, to_cluster, timestamp)


def node_delete(context, node_id, force=False):
    return IMPL.node_delete(context, node_id, force)


# Locks
def cluster_lock_acquire(cluster_id, action_id, scope):
    return IMPL.cluster_lock_acquire(cluster_id, action_id, scope)


def cluster_lock_release(cluster_id, action_id, scope):
    return IMPL.cluster_lock_release(cluster_id, action_id, scope)


def cluster_lock_steal(node_id, action_id):
    return IMPL.cluster_lock_steal(node_id, action_id)


def node_lock_acquire(node_id, action_id):
    return IMPL.node_lock_acquire(node_id, action_id)


def node_lock_release(node_id, action_id):
    return IMPL.node_lock_release(node_id, action_id)


def node_lock_steal(node_id, action_id):
    return IMPL.node_lock_steal(node_id, action_id)


# Policies
def policy_create(context, values):
    return IMPL.policy_create(context, values)


def policy_get(context, policy_id, show_deleted=False):
    return IMPL.policy_get(context, policy_id, show_deleted=show_deleted)


def policy_get_by_name(context, name, show_deleted=False):
    return IMPL.policy_get_by_name(context, name, show_deleted=show_deleted)


def policy_get_by_short_id(context, short_id):
    return IMPL.policy_get_by_short_id(context, short_id)


def policy_get_all(context, limit=None, marker=None, sort_keys=None,
                   sort_dir=None, filters=None, show_deleted=False):
    return IMPL.policy_get_all(context, limit=limit, marker=marker,
                               sort_keys=sort_keys, sort_dir=sort_dir,
                               filters=filters, show_deleted=show_deleted)


def policy_update(context, policy_id, values):
    return IMPL.policy_update(context, policy_id, values)


def policy_delete(context, policy_id, force=False):
    return IMPL.policy_delete(context, policy_id, force)


# Cluster-Policy Associations
def cluster_attach_policy(context, cluster_id, policy_id, values):
    return IMPL.cluster_attach_policy(context, cluster_id, policy_id, values)


def cluster_get_policies(context, cluster_id):
    return IMPL.cluster_get_policies(context, cluster_id)


def cluster_detach_policy(context, cluster_id, policy_id):
    return IMPL.cluster_detach_policy(context, cluster_id, policy_id)


def cluster_enable_policy(context, cluster_id, policy_id):
    return IMPL.cluster_get_policies(context, cluster_id, policy_id)


def cluster_disable_policy(context, cluster_id, policy_id):
    return IMPL.cluster_disable_policy(context, cluster_id, policy_id)


# Profiles
def profile_create(context, values):
    return IMPL.profile_create(context, values)


def profile_get(context, profile_id):
    return IMPL.profile_get(context, profile_id)


def profile_get_by_name(context, name, show_deleted=False):
    return IMPL.profile_get_by_name(context, name, show_deleted=show_deleted)


def profile_get_by_short_id(context, short_id):
    return IMPL.profile_get_by_short_id(context, short_id)


def profile_get_all(context, limit=None, marker=None, sort_keys=None,
                    sort_dir=None, filters=None, show_deleted=False):
    return IMPL.profile_get_all(context, limit=limit, marker=marker,
                                sort_keys=sort_keys, sort_dir=sort_dir,
                                filters=filters, show_deleted=show_deleted)


def profile_update(context, profile_id, values):
    return IMPL.profile_update(context, profile_id, values)


def profile_delete(context, profile_id):
    return IMPL.profile_delete(context, profile_id)


# Events
def event_create(context, values):
    return IMPL.event_create(context, values)


def event_get(context, event_id):
    return IMPL.event_get(context, event_id)


def event_get_by_short_id(context, short_id):
    return IMPL.event_get_by_short_id(context, short_id)


def event_get_all(context):
    return IMPL.event_get_all(context)


def event_count_by_cluster(context, cluster_id):
    return IMPL.event_count_by_cluster(context, cluster_id)


def event_get_all_by_cluster(context, cluster_id, limit=None, marker=None,
                             sort_keys=None, sort_dir=None, filters=None):
    return IMPL.event_get_all_by_cluster(context, cluster_id,
                                         limit=limit, marker=marker,
                                         sort_keys=sort_keys,
                                         sort_dir=sort_dir,
                                         filters=filters)


# Actions
def action_create(context, values):
    return IMPL.action_create(context, values)


def action_get(context, action_id):
    return IMPL.action_get(context, action_id)


def action_get_by_name(context, name):
    return IMPL.action_get_by_name(context, name)


def action_get_by_short_id(context, short_id):
    return IMPL.action_get_by_short_id(context, short_id)


def action_get_1st_ready(context):
    return IMPL.action_get_1st_ready(context)


def action_get_all_ready(context):
    return IMPL.action_get_all_ready(context)


def action_get_all_by_owner(context, owner):
    return IMPL.action_get_all_by_owner(context, owner)


def action_get_all(context, filters=None, limit=None, marker=None,
                   sort_keys=None, sort_dir=None, show_deleted=False):
    return IMPL.action_get_all(context, filters=filters,
                               limit=limit, marker=marker,
                               sort_keys=sort_keys, sort_dir=sort_dir,
                               show_deleted=show_deleted)


def action_add_dependency(context, depended, dependent):
    return IMPL.action_add_dependency(context, depended, dependent)


def action_del_dependency(context, depended, dependent):
    return IMPL.action_del_dependency(context, depended, dependent)


def action_mark_succeeded(context, action_id, timestamp):
    return IMPL.action_mark_succeeded(context, action_id, timestamp)


def action_mark_failed(context, action_id, timestamp, reason=None):
    return IMPL.action_mark_failed(context, action_id, timestamp, reason)


def action_mark_cancelled(context, action_id, timestamp):
    return IMPL.action_mark_cancelled(context, action_id, timestamp)


def action_acquire(context, action_id, owner, timestamp):
    return IMPL.action_acquire(context, action_id, owner, timestamp)


def action_abandon(context, action_id):
    return IMPL.action_abandon(context, action_id)


def action_lock_check(context, action_id, owner=None):
    '''Check whether an action has been locked(by a owner).'''
    return IMPL.action_lock_check(context, action_id, owner)


def action_signal(context, action_id, value):
    '''Send signal to an action via DB.'''
    return IMPL.action_signal(context, action_id, value)


def action_signal_query(context, action_id):
    '''Query signal status for the sepcified action.'''
    return IMPL.action_signal_query(context, action_id)


def action_delete(context, action_id, force=False):
    return IMPL.action_delete(context, action_id, force)


def db_sync(engine, version=None):
    """Migrate the database to `version` or the most recent version."""
    return IMPL.db_sync(engine, version=version)


def db_version(engine):
    """Display the current database version."""
    return IMPL.db_version(engine)
