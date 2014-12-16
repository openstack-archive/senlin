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

from oslo.config import cfg
from oslo.db import api

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


def cluster_get_all(context, limit=None, sort_keys=None, marker=None,
                    sort_dir=None, filters=None, tenant_safe=True,
                    show_deleted=False, show_nested=False):
    return IMPL.cluster_get_all(context, limit, sort_keys,
                                marker, sort_dir, filters, tenant_safe,
                                show_deleted, show_nested)


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


def node_get(context, node_id):
    return IMPL.node_get(context, node_id)


def node_get_all(context):
    return IMPL.node_get_all(context)


def node_get_all_by_cluster(context, cluster_id):
    return IMPL.node_get_all_by_cluster(context, cluster_id)


def node_get_by_name_and_cluster(context, node_name, cluster_id):
    return IMPL.node_get_by_name_and_cluster(context,
                                             node_name, cluster_id)


def node_get_by_physical_id(context, physical_id):
    return IMPL.node_get_by_physical_id(context, physical_id)


# Locks
def cluster_lock_create(cluster_id, engine_id):
    return IMPL.cluster_lock_create(cluster_id, engine_id)


def cluster_lock_steal(cluster_id, old_engine_id, new_engine_id):
    return IMPL.cluster_lock_steal(cluster_id, old_engine_id, new_engine_id)


def cluster_lock_release(cluster_id, engine_id):
    return IMPL.cluster_lock_release(cluster_id, engine_id)


# Profiles
def profile_create(context, values):
    return IMPL.profile_create(context, values)


def profile_get(context, profile_id):
    return IMPL.profile_get(context, profile_id)


# TODO(Qiming): decide if this is needed at all
def profile_update(context, profile_id, values):
    return IMPL.profile_update(context, profile_id, values)


# Policies
def policy_create(context, values):
    return IMPL.policy_create(context, values)


def policy_get(context, policy_id):
    return IMPL.policy_get(context, policy_id)


def policy_update(context, policy_id, values):
    return IMPL.policy_update(context, policy_id, values)


# Events
def event_create(context, values):
    return IMPL.event_create(context, values)


def event_get(context, event_id):
    return IMPL.event_get(context, event_id)


def event_get_all(context):
    return IMPL.event_get_all(context)


def event_count_all_by_cluster(context, cluster_id):
    return IMPL.event_count_all_by_cluster(context, cluster_id)


def event_get_all_by_tenant(context, limit=None, marker=None,
                            sort_keys=None, sort_dir=None, filters=None):
    return IMPL.event_get_all_by_tenant(context,
                                        limit=limit,
                                        marker=marker,
                                        sort_keys=sort_keys,
                                        sort_dir=sort_dir,
                                        filters=filters)


def event_get_all_by_cluster(context, cluster_id, limit=None, marker=None,
                           sort_keys=None, sort_dir=None, filters=None):
    return IMPL.event_get_all_by_cluster(context, cluster_id,
                                       limit=limit,
                                       marker=marker,
                                       sort_keys=sort_keys,
                                       sort_dir=sort_dir,
                                       filters=filters)


def db_sync(engine, version=None):
    """Migrate the database to `version` or the most recent version."""
    return IMPL.db_sync(engine, version=version)


def db_version(engine):
    """Display the current database version."""
    return IMPL.db_version(engine)
