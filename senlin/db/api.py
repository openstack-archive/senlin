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


# Clusters
def cluster_create(context, values):
    return IMPL.cluster_create(context, values)


def cluster_get(context, cluster_id, project_safe=True):
    return IMPL.cluster_get(context, cluster_id, project_safe=project_safe)


def cluster_get_by_name(context, cluster_name, project_safe=True):
    return IMPL.cluster_get_by_name(context, cluster_name,
                                    project_safe=project_safe)


def cluster_get_by_short_id(context, short_id, project_safe=True):
    return IMPL.cluster_get_by_short_id(context, short_id,
                                        project_safe=project_safe)


def cluster_get_all(context, limit=None, marker=None, sort=None, filters=None,
                    project_safe=True):
    return IMPL.cluster_get_all(context, limit=limit, marker=marker, sort=sort,
                                filters=filters, project_safe=project_safe)


def cluster_next_index(context, cluster_id):
    return IMPL.cluster_next_index(context, cluster_id)


def cluster_count_all(context, filters=None, project_safe=True):
    return IMPL.cluster_count_all(context, filters=filters,
                                  project_safe=project_safe)


def cluster_update(context, cluster_id, values):
    return IMPL.cluster_update(context, cluster_id, values)


def cluster_delete(context, cluster_id):
    return IMPL.cluster_delete(context, cluster_id)


# Nodes
def node_create(context, values):
    return IMPL.node_create(context, values)


def node_get(context, node_id, project_safe=True):
    return IMPL.node_get(context, node_id, project_safe=project_safe)


def node_get_by_name(context, name, project_safe=True):
    return IMPL.node_get_by_name(context, name, project_safe=project_safe)


def node_get_by_short_id(context, short_id, project_safe=True):
    return IMPL.node_get_by_short_id(context, short_id,
                                     project_safe=project_safe)


def node_get_all(context, cluster_id=None, limit=None, marker=None, sort=None,
                 filters=None, project_safe=True):
    return IMPL.node_get_all(context, cluster_id=cluster_id, filters=filters,
                             limit=limit, marker=marker, sort=sort,
                             project_safe=project_safe)


def node_get_all_by_cluster(context, cluster_id, filters=None,
                            project_safe=True):
    return IMPL.node_get_all_by_cluster(context, cluster_id, filters=filters,
                                        project_safe=project_safe)


def node_ids_by_cluster(context, cluster_id, filters=None):
    return IMPL.node_ids_by_cluster(context, cluster_id, filters=None)


def node_count_by_cluster(context, cluster_id, **kwargs):
    return IMPL.node_count_by_cluster(context, cluster_id, **kwargs)


def node_update(context, node_id, values):
    return IMPL.node_update(context, node_id, values)


def node_migrate(context, node_id, to_cluster, timestamp, role=None):
    return IMPL.node_migrate(context, node_id, to_cluster, timestamp, role)


def node_delete(context, node_id):
    return IMPL.node_delete(context, node_id)


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


def policy_get(context, policy_id, project_safe=True):
    return IMPL.policy_get(context, policy_id, project_safe=project_safe)


def policy_get_by_name(context, name, project_safe=True):
    return IMPL.policy_get_by_name(context, name, project_safe=project_safe)


def policy_get_by_short_id(context, short_id, project_safe=True):
    return IMPL.policy_get_by_short_id(context, short_id,
                                       project_safe=project_safe)


def policy_get_all(context, limit=None, marker=None, sort=None, filters=None,
                   project_safe=True):
    return IMPL.policy_get_all(context, limit=limit, marker=marker, sort=sort,
                               filters=filters, project_safe=project_safe)


def policy_update(context, policy_id, values):
    return IMPL.policy_update(context, policy_id, values)


def policy_delete(context, policy_id):
    return IMPL.policy_delete(context, policy_id)


# Cluster-Policy Associations
def cluster_policy_get(context, cluster_id, policy_id):
    return IMPL.cluster_policy_get(context, cluster_id, policy_id)


def cluster_policy_get_all(context, cluster_id, filters=None, sort=None):
    return IMPL.cluster_policy_get_all(context, cluster_id, filters=filters,
                                       sort=sort)


def cluster_policy_ids_by_cluster(context, cluster_id):
    return IMPL.cluster_policy_ids_by_cluster(context, cluster_id)


def cluster_policy_get_by_type(context, cluster_id, policy_type, filters=None):
    return IMPL.cluster_policy_get_by_type(context, cluster_id, policy_type,
                                           filters=filters)


def cluster_policy_get_by_name(context, cluster_id, policy_name, filters=None):
    return IMPL.cluster_policy_get_by_name(context, cluster_id, policy_name,
                                           filters=filters)


def cluster_policy_attach(context, cluster_id, policy_id, values):
    return IMPL.cluster_policy_attach(context, cluster_id, policy_id, values)


def cluster_policy_detach(context, cluster_id, policy_id):
    return IMPL.cluster_policy_detach(context, cluster_id, policy_id)


def cluster_policy_update(context, cluster_id, policy_id, values):
    return IMPL.cluster_policy_update(context, cluster_id, policy_id, values)


# Profiles
def profile_create(context, values):
    return IMPL.profile_create(context, values)


def profile_get(context, profile_id, project_safe=True):
    return IMPL.profile_get(context, profile_id, project_safe=project_safe)


def profile_get_by_name(context, name, project_safe=True):
    return IMPL.profile_get_by_name(context, name, project_safe=project_safe)


def profile_get_by_short_id(context, short_id, project_safe=True):
    return IMPL.profile_get_by_short_id(context, short_id,
                                        project_safe=project_safe)


def profile_get_all(context, limit=None, marker=None, sort=None, filters=None,
                    project_safe=True):
    return IMPL.profile_get_all(context, limit=limit, marker=marker,
                                sort=sort, filters=filters,
                                project_safe=project_safe)


def profile_update(context, profile_id, values):
    return IMPL.profile_update(context, profile_id, values)


def profile_delete(context, profile_id):
    return IMPL.profile_delete(context, profile_id)


# Credential
def cred_create(context, values):
    return IMPL.cred_create(context, values)


def cred_get(context, user, project):
    return IMPL.cred_get(context, user, project)


def cred_update(context, user, project, values):
    return IMPL.cred_update(context, user, project, values)


def cred_delete(context, user, project):
    return IMPL.cred_delete(context, user, project)


def cred_create_update(context, values):
    return IMPL.cred_create_update(context, values)


# Events
def event_create(context, values):
    return IMPL.event_create(context, values)


def event_get(context, event_id, project_safe=True):
    return IMPL.event_get(context, event_id, project_safe=project_safe)


def event_get_by_short_id(context, short_id, project_safe=True):
    return IMPL.event_get_by_short_id(context, short_id,
                                      project_safe=project_safe)


def event_get_all(context, limit=None, marker=None, sort=None, filters=None,
                  project_safe=True):
    return IMPL.event_get_all(context, limit=limit, marker=marker, sort=sort,
                              filters=filters, project_safe=project_safe)


def event_count_by_cluster(context, cluster_id, project_safe=True):
    return IMPL.event_count_by_cluster(context, cluster_id,
                                       project_safe=project_safe)


def event_get_all_by_cluster(context, cluster_id, limit=None, marker=None,
                             sort=None, filters=None, project_safe=True):
    return IMPL.event_get_all_by_cluster(context, cluster_id, filters=filters,
                                         limit=limit, marker=marker, sort=sort,
                                         project_safe=project_safe)


def event_prune(context, cluster_id, project_safe=True):
    return IMPL.event_prune(context, cluster_id, project_safe=project_safe)


# Actions
def action_create(context, values):
    return IMPL.action_create(context, values)


def action_update(context, action_id, values):
    return IMPL.action_update(context, action_id, values)


def action_get(context, action_id, project_safe=True, refresh=False):
    return IMPL.action_get(context, action_id, project_safe=project_safe,
                           refresh=refresh)


def action_get_by_name(context, name, project_safe=True):
    return IMPL.action_get_by_name(context, name, project_safe=project_safe)


def action_get_by_short_id(context, short_id, project_safe=True):
    return IMPL.action_get_by_short_id(context, short_id,
                                       project_safe=project_safe)


def action_get_all_by_owner(context, owner):
    return IMPL.action_get_all_by_owner(context, owner)


def action_get_all(context, filters=None, limit=None, marker=None, sort=None,
                   project_safe=True):
    return IMPL.action_get_all(context, filters=filters, sort=sort,
                               limit=limit, marker=marker,
                               project_safe=project_safe)


def action_check_status(context, action_id, timestamp):
    return IMPL.action_check_status(context, action_id, timestamp)


def action_delete_by_target(context, target, action=None,
                            action_excluded=None, status=None):
    return IMPL.action_delete_by_target(context, target, action=action,
                                        action_excluded=action_excluded,
                                        status=status)


def dependency_add(context, depended, dependent):
    return IMPL.dependency_add(context, depended, dependent)


def dependency_get_depended(context, action_id):
    return IMPL.dependency_get_depended(context, action_id)


def dependency_get_dependents(context, action_id):
    return IMPL.dependency_get_dependents(context, action_id)


def action_mark_succeeded(context, action_id, timestamp):
    return IMPL.action_mark_succeeded(context, action_id, timestamp)


def action_mark_ready(context, action_id, timestamp):
    return IMPL.action_mark_ready(context, action_id, timestamp)


def action_mark_failed(context, action_id, timestamp, reason=None):
    return IMPL.action_mark_failed(context, action_id, timestamp, reason)


def action_mark_cancelled(context, action_id, timestamp):
    return IMPL.action_mark_cancelled(context, action_id, timestamp)


def action_acquire(context, action_id, owner, timestamp):
    return IMPL.action_acquire(context, action_id, owner, timestamp)


def action_acquire_random_ready(context, owner, timestamp):
    return IMPL.action_acquire_random_ready(context, owner, timestamp)


def action_acquire_first_ready(context, owner, timestamp):
    return IMPL.action_acquire_first_ready(context, owner, timestamp)


def action_abandon(context, action_id, values=None):
    return IMPL.action_abandon(context, action_id, values)


def action_lock_check(context, action_id, owner=None):
    '''Check whether an action has been locked(by a owner).'''
    return IMPL.action_lock_check(context, action_id, owner)


def action_signal(context, action_id, value):
    '''Send signal to an action via DB.'''
    return IMPL.action_signal(context, action_id, value)


def action_signal_query(context, action_id):
    '''Query signal status for the specified action.'''
    return IMPL.action_signal_query(context, action_id)


def action_delete(context, action_id):
    return IMPL.action_delete(context, action_id)


def receiver_create(context, values):
    return IMPL.receiver_create(context, values)


def receiver_get(context, receiver_id, project_safe=True):
    return IMPL.receiver_get(context, receiver_id, project_safe=project_safe)


def receiver_get_by_name(context, name, project_safe=True):
    return IMPL.receiver_get_by_name(context, name, project_safe=project_safe)


def receiver_get_by_short_id(context, short_id, project_safe=True):
    return IMPL.receiver_get_by_short_id(context, short_id,
                                         project_safe=project_safe)


def receiver_get_all(context, limit=None, marker=None, filters=None, sort=None,
                     project_safe=True):
    return IMPL.receiver_get_all(context, limit=limit, marker=marker,
                                 sort=sort, filters=filters,
                                 project_safe=project_safe)


def receiver_delete(context, receiver_id):
    return IMPL.receiver_delete(context, receiver_id)


def receiver_update(context, receiver_id, values):
    return IMPL.receiver_update(context, receiver_id, values)


def service_create(service_id, host=None, binary=None, topic=None):
    return IMPL.service_create(service_id, host=host, binary=binary,
                               topic=topic)


def service_update(service_id, values=None):
    return IMPL.service_update(service_id, values=values)


def service_delete(service_id):
    return IMPL.service_delete(service_id)


def service_get(service_id):
    return IMPL.service_get(service_id)


def service_get_all():
    return IMPL.service_get_all()


def gc_by_engine(engine_id):
    return IMPL.gc_by_engine(engine_id)


def registry_create(context, cluster_id, check_type, interval, params,
                    engine_id, enabled=True):
    return IMPL.registry_create(context, cluster_id, check_type, interval,
                                params, engine_id, enabled=enabled)


def registry_update(context, cluster_id, values):
    return IMPL.registry_update(context, cluster_id, values)


def registry_delete(context, cluster_id):
    return IMPL.registry_delete(context, cluster_id)


def registry_claim(context, engine_id):
    return IMPL.registry_claim(context, engine_id)


def registry_get(context, cluster_id):
    return IMPL.registry_get(context, cluster_id)


def registry_get_by_param(context, params):
    return IMPL.registry_get_by_param(context, params)


def db_sync(engine, version=None):
    """Migrate the database to `version` or the most recent version."""
    return IMPL.db_sync(engine, version=version)


def db_version(engine):
    """Display the current database version."""
    return IMPL.db_version(engine)


def event_purge(engine, project, granularity, age):
    """Purge the event records in database."""
    return IMPL.event_purge(project, granularity, age)
