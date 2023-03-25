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

"""
Implementation of SQLAlchemy backend.
"""

import datetime
import sys
import threading
import time

from oslo_config import cfg
from oslo_db import api as oslo_db_api
from oslo_db import exception as db_exc
from oslo_db import options as db_options
from oslo_db.sqlalchemy import enginefacade
from oslo_db.sqlalchemy import utils as sa_utils
from oslo_log import log as logging
from oslo_utils import importutils
from oslo_utils import timeutils
from osprofiler import opts as profiler
import sqlalchemy
from sqlalchemy import and_
from sqlalchemy.orm import joinedload
from sqlalchemy.sql.expression import func

from senlin.common import consts
from senlin.common import exception
from senlin.db.sqlalchemy import migration
from senlin.db.sqlalchemy import models
from senlin.db.sqlalchemy import utils

osprofiler_sqlalchemy = importutils.try_import('osprofiler.sqlalchemy')

LOG = logging.getLogger(__name__)
CONF = cfg.CONF

_CONTEXT = None
_LOCK = threading.Lock()
_MAIN_CONTEXT_MANAGER = None

CONF.import_opt('database_retry_limit', 'senlin.conf')
CONF.import_opt('database_retry_interval', 'senlin.conf')
CONF.import_opt('database_max_retry_interval', 'senlin.conf')

try:
    CONF.import_group('profiler', 'senlin.conf')
except cfg.NoSuchGroupError:
    pass


def initialize():
    connection = CONF['database'].connection
    db_options.set_defaults(
        CONF, connection=connection
    )
    profiler.set_defaults(CONF, enabled=False, trace_sqlalchemy=False)


def _get_main_context_manager():
    global _LOCK
    global _MAIN_CONTEXT_MANAGER

    with _LOCK:
        if not _MAIN_CONTEXT_MANAGER:
            initialize()
            _MAIN_CONTEXT_MANAGER = enginefacade.transaction_context()
            _MAIN_CONTEXT_MANAGER.configure(__autocommit=True)

    return _MAIN_CONTEXT_MANAGER


def _get_context():
    global _CONTEXT
    if _CONTEXT is None:
        import threading
        _CONTEXT = threading.local()
    return _CONTEXT


def _wrap_session(sess):
    if not osprofiler_sqlalchemy:
        return sess
    if CONF.profiler.enabled and CONF.profiler.trace_sqlalchemy:
        sess = osprofiler_sqlalchemy.wrap_session(sqlalchemy, sess)
    return sess


def session_for_read():
    reader = _get_main_context_manager().reader
    return _wrap_session(reader.using(_get_context()))


def session_for_write():
    writer = _get_main_context_manager().writer
    return _wrap_session(writer.using(_get_context()))


def service_expired_time():
    return (timeutils.utcnow() -
            datetime.timedelta(seconds=2.2 * CONF.periodic_interval))


def get_engine():
    return _get_main_context_manager().writer.get_engine()


def get_backend():
    """The backend is this module itself."""
    return sys.modules[__name__]


def retry_on_deadlock(f):
    return oslo_db_api.wrap_db_retry(
        retry_on_deadlock=True,
        max_retries=CONF.database_retry_limit,
        retry_interval=CONF.database_retry_interval,
        inc_retry_interval=True,
        max_retry_interval=CONF.database_max_retry_interval)(f)


def query_by_short_id(context, model_query, model, short_id,
                      project_safe=True):
    q = model_query()
    q = q.filter(model.id.like('%s%%' % short_id))
    q = utils.filter_query_by_project(q, project_safe, context)

    if q.count() == 1:
        return q.first()
    elif q.count() == 0:
        return None
    else:
        raise exception.MultipleChoices(arg=short_id)


def query_by_name(context, model_query, name, project_safe=True):
    q = model_query()
    q = q.filter_by(name=name)
    q = utils.filter_query_by_project(q, project_safe, context)

    if q.count() == 1:
        return q.first()
    elif q.count() == 0:
        return None
    else:
        raise exception.MultipleChoices(arg=name)


# Clusters
def cluster_model_query():
    with session_for_read() as session:
        query = session.query(models.Cluster).options(
            joinedload(models.Cluster.nodes),
            joinedload(models.Cluster.profile),
            joinedload(models.Cluster.policies)
        )
        return query


@retry_on_deadlock
def cluster_create(context, values):
    with session_for_write() as session:
        cluster_ref = models.Cluster()
        cluster_ref.update(values)
        session.add(cluster_ref)
    return cluster_get(context, cluster_ref.id)


def cluster_get(context, cluster_id, project_safe=True):
    cluster = cluster_model_query().get(cluster_id)

    if cluster is None:
        return None

    return utils.check_resource_project(context, cluster, project_safe)


def cluster_get_by_name(context, name, project_safe=True):
    return query_by_name(context, cluster_model_query, name,
                         project_safe=project_safe)


def cluster_get_by_short_id(context, short_id, project_safe=True):
    return query_by_short_id(context, cluster_model_query, models.Cluster,
                             short_id, project_safe=project_safe)


def _query_cluster_get_all(context, project_safe=True):
    query = cluster_model_query()
    query = utils.filter_query_by_project(query, project_safe, context)

    return query


def cluster_get_all(context, limit=None, marker=None, sort=None, filters=None,
                    project_safe=True):
    query = _query_cluster_get_all(context, project_safe=project_safe)
    if filters:
        query = utils.exact_filter(query, models.Cluster, filters)

    keys, dirs = utils.get_sort_params(sort, consts.CLUSTER_INIT_AT)
    if marker:
        marker = cluster_model_query().get(marker)

    return sa_utils.paginate_query(query, models.Cluster, limit, keys,
                                   marker=marker, sort_dirs=dirs).all()


@retry_on_deadlock
def cluster_next_index(context, cluster_id):
    with session_for_write() as session:
        cluster = session.query(models.Cluster).with_for_update().get(
            cluster_id)
        if cluster is None:
            return 0

        next_index = cluster.next_index
        cluster.next_index = cluster.next_index + 1
        cluster.save(session)
        return next_index


def cluster_count_all(context, filters=None, project_safe=True):
    query = _query_cluster_get_all(context, project_safe=project_safe)
    query = utils.exact_filter(query, models.Cluster, filters)
    return query.count()


@retry_on_deadlock
def cluster_update(context, cluster_id, values):
    with session_for_write() as session:
        cluster = session.query(
            models.Cluster).with_for_update().get(cluster_id)

        if not cluster:
            raise exception.ResourceNotFound(type='cluster', id=cluster_id)

        cluster.update(values)
        cluster.save(session)


@retry_on_deadlock
def cluster_delete(context, cluster_id):
    with session_for_write() as session:
        cluster = session.query(models.Cluster).get(cluster_id)
        if cluster is None:
            raise exception.ResourceNotFound(type='cluster', id=cluster_id)

        query = session.query(models.Node).filter_by(cluster_id=cluster_id)
        nodes = query.all()

        if len(nodes) != 0:
            for node in nodes:
                session.delete(node)

        # Delete all related cluster_policies records
        for cp in cluster.policies:
            session.delete(cp)

        # Delete cluster
        session.delete(cluster)


# Nodes
def node_model_query():
    with session_for_read() as session:
        query = session.query(models.Node).options(
            joinedload(models.Node.profile)
        )
        return query


@retry_on_deadlock
def node_create(context, values):
    # This operation is always called with cluster and node locked
    with session_for_write() as session:
        node = models.Node()
        node.update(values)
        session.add(node)
        return node


def node_get(context, node_id, project_safe=True):
    node = node_model_query().get(node_id)
    if not node:
        return None

    return utils.check_resource_project(context, node, project_safe)


def node_get_by_name(context, name, project_safe=True):
    return query_by_name(context, node_model_query, name,
                         project_safe=project_safe)


def node_get_by_short_id(context, short_id, project_safe=True):
    return query_by_short_id(context, node_model_query, models.Node, short_id,
                             project_safe=project_safe)


def _query_node_get_all(context, project_safe=True, cluster_id=None):
    query = node_model_query()

    if cluster_id is not None:
        query = query.filter_by(cluster_id=cluster_id)

    query = utils.filter_query_by_project(query, project_safe, context)

    return query


def node_get_all(context, cluster_id=None, limit=None, marker=None, sort=None,
                 filters=None, project_safe=True):
    query = _query_node_get_all(context, project_safe=project_safe,
                                cluster_id=cluster_id)

    if filters:
        query = utils.exact_filter(query, models.Node, filters)

    keys, dirs = utils.get_sort_params(sort, consts.NODE_INIT_AT)
    if marker:
        marker = node_model_query().get(marker)
    return sa_utils.paginate_query(query, models.Node, limit, keys,
                                   marker=marker, sort_dirs=dirs).all()


def node_get_all_by_cluster(context, cluster_id, filters=None,
                            project_safe=True):

    query = _query_node_get_all(context, cluster_id=cluster_id,
                                project_safe=project_safe)
    if filters:
        query = utils.exact_filter(query, models.Node, filters)

    return query.all()


def node_ids_by_cluster(context, cluster_id, filters=None):
    """an internal API for getting node IDs."""
    with session_for_read() as session:
        query = session.query(models.Node.id).filter_by(cluster_id=cluster_id)
        if filters:
            query = utils.exact_filter(query, models.Node, filters)

        return [n[0] for n in query.all()]


def node_count_by_cluster(context, cluster_id, **kwargs):
    project_safe = kwargs.pop('project_safe', True)
    query = node_model_query()
    query = query.filter_by(cluster_id=cluster_id)
    query = query.filter_by(**kwargs)
    query = utils.filter_query_by_project(query, project_safe, context)

    return query.count()


@retry_on_deadlock
def node_update(context, node_id, values):
    """Update a node with new property values.

    :param node_id: ID of the node to be updated.
    :param values: A dictionary of values to be updated on the node.
    :raises ResourceNotFound: The specified node does not exist in database.
    """
    with session_for_write() as session:
        node = session.query(models.Node).get(node_id)
        if not node:
            raise exception.ResourceNotFound(type='node', id=node_id)

        node.update(values)
        node.save(session)
        if 'status' in values and node.cluster_id is not None:
            cluster = session.query(models.Cluster).get(node.cluster_id)
            if cluster is not None:
                if values['status'] == 'ERROR':
                    cluster.status = consts.CS_WARNING
                if 'status_reason' in values:
                    cluster.status_reason = 'Node %(node)s: %(reason)s' % {
                        'node': node.name, 'reason': values['status_reason']}
                cluster.save(session)


@retry_on_deadlock
def node_add_dependents(context, depended, dependent, dep_type=None):
    """Add dependency between nodes.

    :param depended: ID of the depended dependent.
    :param dependent: ID of the dependent node or profile which has
                     dependencies on depended node.
    :param dep_type: The type of dependency. It can be 'node' indicating a
                     dependency between two nodes; or 'profile' indicating a
                     dependency from profile to node.
    :raises ResourceNotFound: The specified node does not exist in database.
    """
    with session_for_write() as session:
        dep_node = session.query(models.Node).get(depended)
        if not dep_node:
            raise exception.ResourceNotFound(type='node', id=depended)

        if dep_type is None or dep_type == 'node':
            key = 'nodes'
        else:
            key = 'profiles'
        dependents = dep_node.dependents.get(key, [])
        dependents.append(dependent)
        dep_node.dependents.update({key: dependents})
        dep_node.save(session)


@retry_on_deadlock
def node_remove_dependents(context, depended, dependent, dep_type=None):
    """Remove dependency between nodes.

    :param depended: ID of the depended node.
    :param dependent: ID of the node or profile which has dependencies on
                     the depended node.
    :param dep_type: The type of dependency. It can be 'node' indicating a
                     dependency between two nodes; or 'profile' indicating a
                     dependency from profile to node.

    :raises ResourceNotFound: The specified node does not exist in database.
    """
    with session_for_write() as session:
        dep_node = session.query(models.Node).get(depended)
        if not dep_node:
            raise exception.ResourceNotFound(type='node', id=depended)

        if dep_type is None or dep_type == 'node':
            key = 'nodes'
        else:
            key = 'profiles'

        dependents = dep_node.dependents.get(key, [])
        if dependent in dependents:
            dependents.remove(dependent)
            if len(dependents) > 0:
                dep_node.dependents.update({key: dependents})
            else:
                dep_node.dependents.pop(key)
            dep_node.save(session)


@retry_on_deadlock
def node_migrate(context, node_id, to_cluster, timestamp, role=None):
    with session_for_write() as session:
        node = session.query(models.Node).get(node_id)
        from_cluster = node.cluster_id
        if from_cluster:
            node.index = -1
        if to_cluster:
            node.index = cluster_next_index(context, to_cluster)
        node.cluster_id = to_cluster if to_cluster else ''
        node.updated_at = timestamp
        node.role = role
        node.save(session)
        return node


@retry_on_deadlock
def node_delete(context, node_id):
    with session_for_write() as session:
        node = session.query(models.Node).get(node_id)
        if not node:
            # Note: this is okay, because the node may have already gone
            return
        session.delete(node)


# Locks
@retry_on_deadlock
def cluster_lock_acquire(cluster_id, action_id, scope):
    """Acquire lock on a cluster.

    :param cluster_id: ID of the cluster.
    :param action_id: ID of the action that attempts to lock the cluster.
    :param scope: +1 means a node-level operation lock; -1 indicates
                  a cluster-level lock.
    :return: A list of action IDs that currently works on the cluster.
    """
    with session_for_write() as session:
        query = session.query(models.ClusterLock).with_for_update()
        lock = query.get(cluster_id)
        if lock is not None:
            if scope == 1 and lock.semaphore > 0:
                if action_id not in lock.action_ids:
                    lock.action_ids.append(str(action_id))
                    lock.semaphore += 1
                    lock.save(session)
        else:
            lock = models.ClusterLock(cluster_id=cluster_id,
                                      action_ids=[str(action_id)],
                                      semaphore=scope)
            session.add(lock)
        return lock.action_ids


@retry_on_deadlock
def cluster_is_locked(cluster_id):
    with session_for_read() as session:
        query = session.query(models.ClusterLock)
        lock = query.get(cluster_id)
        return lock is not None


@retry_on_deadlock
def _release_cluster_lock(session, lock, action_id, scope):
    success = False
    if (scope == -1 and lock.semaphore < 0) or lock.semaphore == 1:
        if str(action_id) in lock.action_ids:
            session.delete(lock)
            success = True
    elif str(action_id) in lock.action_ids:
        if lock.semaphore == 1:
            session.delete(lock)
        else:
            lock.action_ids.remove(str(action_id))
            lock.semaphore -= 1
            lock.save(session)
        success = True
    return success


@retry_on_deadlock
def cluster_lock_release(cluster_id, action_id, scope):
    """Release lock on a cluster.

    :param cluster_id: ID of the cluster.
    :param action_id: ID of the action that attempts to release the cluster.
    :param scope: +1 means a node-level operation lock; -1 indicates
                  a cluster-level lock.
    :return: True indicates successful release, False indicates failure.
    """
    with session_for_write() as session:
        lock = session.query(
            models.ClusterLock).with_for_update().get(cluster_id)
        if lock is None:
            return False

        return _release_cluster_lock(session, lock, action_id, scope)


@retry_on_deadlock
def cluster_lock_steal(cluster_id, action_id):
    with session_for_write() as session:
        lock = session.query(
            models.ClusterLock).with_for_update().get(cluster_id)
        if lock is not None:
            lock.action_ids = [action_id]
            lock.semaphore = -1
            lock.save(session)
        else:
            lock = models.ClusterLock(cluster_id=cluster_id,
                                      action_ids=[action_id],
                                      semaphore=-1)
            session.add(lock)

        return lock.action_ids


@retry_on_deadlock
def node_lock_acquire(node_id, action_id):
    with session_for_write() as session:
        lock = session.query(
            models.NodeLock).with_for_update().get(node_id)
        if lock is None:
            lock = models.NodeLock(node_id=node_id, action_id=action_id)
            session.add(lock)

        return lock.action_id


@retry_on_deadlock
def node_is_locked(node_id):
    with session_for_read() as session:
        query = session.query(models.NodeLock)
        lock = query.get(node_id)

        return lock is not None


@retry_on_deadlock
def node_lock_release(node_id, action_id):
    with session_for_write() as session:
        success = False
        lock = session.query(
            models.NodeLock).with_for_update().get(node_id)
        if lock is not None and lock.action_id == action_id:
            session.delete(lock)
            success = True

        return success


@retry_on_deadlock
def node_lock_steal(node_id, action_id):
    with session_for_write() as session:
        lock = session.query(
            models.NodeLock).with_for_update().get(node_id)
        if lock is not None:
            lock.action_id = action_id
            lock.save(session)
        else:
            lock = models.NodeLock(node_id=node_id, action_id=action_id)
            session.add(lock)
        return lock.action_id


# Policies
def policy_model_query():
    with session_for_read() as session:
        query = session.query(models.Policy).options(
            joinedload(models.Policy.bindings)
        )
        return query


@retry_on_deadlock
def policy_create(context, values):
    with session_for_write() as session:
        policy = models.Policy()
        policy.update(values)
        session.add(policy)
        return policy


def policy_get(context, policy_id, project_safe=True):
    policy = policy_model_query()
    policy = policy.filter_by(id=policy_id).first()

    if policy is None:
        return None

    return utils.check_resource_project(context, policy, project_safe)


def policy_get_by_name(context, name, project_safe=True):
    return query_by_name(context, policy_model_query, name,
                         project_safe=project_safe)


def policy_get_by_short_id(context, short_id, project_safe=True):
    return query_by_short_id(context, policy_model_query, models.Policy,
                             short_id, project_safe=project_safe)


def policy_get_all(context, limit=None, marker=None, sort=None, filters=None,
                   project_safe=True):
    query = policy_model_query()
    query = utils.filter_query_by_project(query, project_safe, context)

    if filters:
        query = utils.exact_filter(query, models.Policy, filters)

    keys, dirs = utils.get_sort_params(sort, consts.POLICY_CREATED_AT)
    if marker:
        marker = policy_model_query().get(marker)
    return sa_utils.paginate_query(query, models.Policy, limit, keys,
                                   marker=marker, sort_dirs=dirs).all()


@retry_on_deadlock
def policy_update(context, policy_id, values):
    with session_for_write() as session:
        policy = session.query(models.Policy).get(policy_id)
        if not policy:
            raise exception.ResourceNotFound(type='policy', id=policy_id)

        policy.update(values)
        policy.save(session)
        return policy


@retry_on_deadlock
def policy_delete(context, policy_id):
    with session_for_write() as session:
        policy = session.query(models.Policy).get(policy_id)

        if not policy:
            return

        bindings = session.query(models.ClusterPolicies).filter_by(
            policy_id=policy_id)
        if bindings.count():
            raise exception.EResourceBusy(type='policy', id=policy_id)
        session.delete(policy)


# Cluster-Policy Associations
def cluster_policy_model_query():
    with session_for_read() as session:
        query = session.query(models.ClusterPolicies)
        return query


def cluster_policy_get(context, cluster_id, policy_id):
    query = cluster_policy_model_query()
    bindings = query.filter_by(cluster_id=cluster_id,
                               policy_id=policy_id)
    return bindings.first()


def cluster_policy_get_all(context, cluster_id, filters=None, sort=None):
    with session_for_read() as session:
        query = session.query(models.ClusterPolicies)
        query = query.filter_by(cluster_id=cluster_id)

        if filters is not None:
            key_enabled = consts.CP_ENABLED
            if key_enabled in filters:
                filter_enabled = {key_enabled: filters[key_enabled]}
                query = utils.exact_filter(query, models.ClusterPolicies,
                                           filter_enabled)
            key_type = consts.CP_POLICY_TYPE
            key_name = consts.CP_POLICY_NAME
            if key_type in filters and key_name in filters:
                query = query.join(models.Policy).filter(
                    and_(models.Policy.type == filters[key_type],
                         models.Policy.name == filters[key_name]))
            elif key_type in filters:
                query = query.join(models.Policy).filter(
                    models.Policy.type == filters[key_type])
            elif key_name in filters:
                query = query.join(models.Policy).filter(
                    models.Policy.name == filters[key_name])

        keys, dirs = utils.get_sort_params(sort)
    return sa_utils.paginate_query(query, models.ClusterPolicies, None,
                                   keys, sort_dirs=dirs).all()


def cluster_policy_ids_by_cluster(context, cluster_id):
    """an internal API for getting cluster IDs."""
    with session_for_read() as session:
        policies = session.query(models.ClusterPolicies.policy_id).filter_by(
            cluster_id=cluster_id).all()
        return [p[0] for p in policies]


def cluster_policy_get_by_type(context, cluster_id, policy_type, filters=None):

    query = cluster_policy_model_query()
    query = query.filter_by(cluster_id=cluster_id)

    key_enabled = consts.CP_ENABLED
    if filters and key_enabled in filters:
        filter_enabled = {key_enabled: filters[key_enabled]}
        query = utils.exact_filter(query, models.ClusterPolicies,
                                   filter_enabled)

    query = query.join(models.Policy).filter(models.Policy.type == policy_type)

    return query.all()


def cluster_policy_get_by_name(context, cluster_id, policy_name, filters=None):

    query = cluster_policy_model_query()
    query = query.filter_by(cluster_id=cluster_id)

    key_enabled = consts.CP_ENABLED
    if filters and key_enabled in filters:
        filter_enabled = {key_enabled: filters[key_enabled]}
        query = utils.exact_filter(query, models.ClusterPolicies,
                                   filter_enabled)

    query = query.join(models.Policy).filter(models.Policy.name == policy_name)

    return query.all()


@retry_on_deadlock
def cluster_policy_attach(context, cluster_id, policy_id, values):
    with session_for_write() as session:
        binding = models.ClusterPolicies()
        binding.cluster_id = cluster_id
        binding.policy_id = policy_id
        binding.update(values)
        session.add(binding)
    # Load foreignkey cluster and policy
    return cluster_policy_get(context, cluster_id, policy_id)


@retry_on_deadlock
def cluster_policy_detach(context, cluster_id, policy_id):
    with session_for_write() as session:
        query = session.query(models.ClusterPolicies)
        bindings = query.filter_by(cluster_id=cluster_id,
                                   policy_id=policy_id).first()
        if bindings is None:
            return
        session.delete(bindings)


@retry_on_deadlock
def cluster_policy_update(context, cluster_id, policy_id, values):
    with session_for_write() as session:
        query = session.query(models.ClusterPolicies)
        binding = query.filter_by(cluster_id=cluster_id,
                                  policy_id=policy_id).first()

        if binding is None:
            return None

        binding.update(values)
        binding.save(session)
        return binding


@retry_on_deadlock
def cluster_add_dependents(context, cluster_id, profile_id):
    """Add profile ID of container node to host cluster's 'dependents' property

    :param cluster_id: ID of the cluster to be updated.
    :param profile_id: Profile ID of the container node.
    :raises ResourceNotFound: The specified cluster does not exist in database.
    """

    with session_for_write() as session:
        cluster = session.query(models.Cluster).get(cluster_id)
        if cluster is None:
            raise exception.ResourceNotFound(type='cluster', id=cluster_id)

        profiles = cluster.dependents.get('profiles', [])
        profiles.append(profile_id)
        cluster.dependents.update({'profiles': profiles})
        cluster.save(session)


@retry_on_deadlock
def cluster_remove_dependents(context, cluster_id, profile_id):
    """Remove profile ID from host cluster's 'dependents' property

    :param cluster_id: ID of the cluster to be updated.
    :param profile_id: Profile ID of the container node.
    :raises ResourceNotFound: The specified cluster does not exist in database.
    """

    with session_for_write() as session:
        cluster = session.query(models.Cluster).get(cluster_id)
        if cluster is None:
            raise exception.ResourceNotFound(type='cluster', id=cluster_id)

        profiles = cluster.dependents.get('profiles', [])
        if profile_id in profiles:
            profiles.remove(profile_id)
            if len(profiles) == 0:
                cluster.dependents.pop('profiles')
            else:
                cluster.dependents.update({'profiles': profiles})
            cluster.save(session)


# Profiles
def profile_model_query():
    with session_for_read() as session:
        query = session.query(models.Profile)
        return query


@retry_on_deadlock
def profile_create(context, values):
    with session_for_write() as session:
        profile = models.Profile()
        profile.update(values)
        session.add(profile)
        return profile


def profile_get(context, profile_id, project_safe=True):
    query = profile_model_query()
    profile = query.get(profile_id)

    if profile is None:
        return None

    return utils.check_resource_project(context, profile, project_safe)


def profile_get_by_name(context, name, project_safe=True):
    return query_by_name(context, profile_model_query, name,
                         project_safe=project_safe)


def profile_get_by_short_id(context, short_id, project_safe=True):
    return query_by_short_id(context, profile_model_query, models.Profile,
                             short_id, project_safe=project_safe)


def profile_get_all(context, limit=None, marker=None, sort=None, filters=None,
                    project_safe=True):
    query = profile_model_query()
    query = utils.filter_query_by_project(query, project_safe, context)

    if filters:
        query = utils.exact_filter(query, models.Profile, filters)

    keys, dirs = utils.get_sort_params(sort, consts.PROFILE_CREATED_AT)
    if marker:
        marker = profile_model_query().get(marker)
    return sa_utils.paginate_query(query, models.Profile, limit, keys,
                                   marker=marker, sort_dirs=dirs).all()


@retry_on_deadlock
def profile_update(context, profile_id, values):
    with session_for_write() as session:
        profile = session.query(models.Profile).get(profile_id)
        if not profile:
            raise exception.ResourceNotFound(type='profile', id=profile_id)

        profile.update(values)
        profile.save(session)
        return profile


@retry_on_deadlock
def profile_delete(context, profile_id):
    with session_for_write() as session:
        profile = session.query(models.Profile).get(profile_id)
        if profile is None:
            return

        # used by any clusters?
        clusters = session.query(models.Cluster).filter_by(
            profile_id=profile_id)
        if clusters.count() > 0:
            raise exception.EResourceBusy(type='profile', id=profile_id)

        # used by any nodes?
        nodes = session.query(models.Node).filter_by(profile_id=profile_id)
        if nodes.count() > 0:
            raise exception.EResourceBusy(type='profile', id=profile_id)
        session.delete(profile)


# Credentials
def credential_model_query():
    with session_for_read() as session:
        query = session.query(models.Credential)
        return query


@retry_on_deadlock
def cred_create(context, values):
    with session_for_write() as session:
        cred = models.Credential()
        cred.update(values)
        session.add(cred)
        return cred


def cred_get(context, user, project):
    return credential_model_query().get((user, project))


@retry_on_deadlock
def cred_update(context, user, project, values):
    with session_for_write() as session:
        cred = session.query(models.Credential).get((user, project))
        cred.update(values)
        cred.save(session)
        return cred


@retry_on_deadlock
def cred_delete(context, user, project):
    with session_for_write() as session:
        cred = session.query(models.Credential).get((user, project))
        if cred is None:
            return None
        session.delete(cred)


@retry_on_deadlock
def cred_create_update(context, values):
    try:
        return cred_create(context, values)
    except db_exc.DBDuplicateEntry:
        user = values.pop('user')
        project = values.pop('project')
        return cred_update(context, user, project, values)


# Events
def event_model_query():
    with session_for_read() as session:
        query = session.query(models.Event).options(
            joinedload(models.Event.cluster)
        )
        return query


@retry_on_deadlock
def event_create(context, values):
    with session_for_write() as session:
        event = models.Event()
        event.update(values)
        session.add(event)
        return event


@retry_on_deadlock
def event_get(context, event_id, project_safe=True):
    event = event_model_query().get(event_id)
    return utils.check_resource_project(context, event, project_safe)


def event_get_by_short_id(context, short_id, project_safe=True):
    return query_by_short_id(context, event_model_query, models.Event,
                             short_id, project_safe=project_safe)


def _event_filter_paginate_query(context, query, filters=None,
                                 limit=None, marker=None, sort=None):
    if filters:
        query = utils.exact_filter(query, models.Event, filters)

    keys, dirs = utils.get_sort_params(sort, consts.EVENT_TIMESTAMP)
    if marker:
        marker = event_model_query().get(marker)
    return sa_utils.paginate_query(query, models.Event, limit, keys,
                                   marker=marker, sort_dirs=dirs).all()


def event_get_all(context, limit=None, marker=None, sort=None, filters=None,
                  project_safe=True):
    query = event_model_query()
    query = utils.filter_query_by_project(query, project_safe, context)

    return _event_filter_paginate_query(context, query, filters=filters,
                                        limit=limit, marker=marker, sort=sort)


def event_count_by_cluster(context, cluster_id, project_safe=True):
    query = event_model_query()
    query = utils.filter_query_by_project(query, project_safe, context)

    count = query.filter_by(cluster_id=cluster_id).count()

    return count


def event_get_all_by_cluster(context, cluster_id, limit=None, marker=None,
                             sort=None, filters=None, project_safe=True):
    query = event_model_query()
    query = query.filter_by(cluster_id=cluster_id)
    query = utils.filter_query_by_project(query, project_safe, context)

    return _event_filter_paginate_query(context, query, filters=filters,
                                        limit=limit, marker=marker, sort=sort)


@retry_on_deadlock
def event_prune(context, cluster_id, project_safe=True):
    with session_for_write() as session:
        query = session.query(models.Event).with_for_update()
        query = query.filter_by(cluster_id=cluster_id)
        query = utils.filter_query_by_project(query, project_safe, context)

        return query.delete(synchronize_session='fetch')


@retry_on_deadlock
def event_purge(project, granularity='days', age=30):
    with session_for_write() as session:
        query = session.query(models.Event).with_for_update()
        if project is not None:
            query = query.filter(models.Event.project.in_(project))
        if granularity is not None and age is not None:
            if granularity == 'days':
                age = age * 86400
            elif granularity == 'hours':
                age = age * 3600
            elif granularity == 'minutes':
                age = age * 60
            time_line = timeutils.utcnow() - datetime.timedelta(seconds=age)
            query = query.filter(models.Event.timestamp < time_line)

        return query.delete(synchronize_session='fetch')


# Actions
def action_model_query():
    with session_for_read() as session:
        query = session.query(models.Action).options(
            joinedload(models.Action.dep_on),
            joinedload(models.Action.dep_by)
        )
        return query


@retry_on_deadlock
def action_create(context, values):
    with session_for_write() as session:
        action = models.Action()
        action.update(values)
        session.add(action)
    return action_get(context, action.id)


@retry_on_deadlock
def action_update(context, action_id, values):
    with session_for_write() as session:
        action = session.query(models.Action).get(action_id)
        if not action:
            raise exception.ResourceNotFound(type='action', id=action_id)

        action.update(values)
        action.save(session)


def action_get(context, action_id, project_safe=True, refresh=False):
    action = action_model_query().get(action_id)
    if action is None:
        return None

    return utils.check_resource_project(context, action, project_safe)


def action_list_active_scaling(context, cluster_id=None, project_safe=True):
    query = action_model_query()
    query = utils.filter_query_by_project(query, project_safe, context)

    if cluster_id:
        query = query.filter_by(target=cluster_id)
    query = query.filter(
        models.Action.status.in_(
            [consts.ACTION_READY,
             consts.ACTION_WAITING,
             consts.ACTION_RUNNING,
             consts.ACTION_WAITING_LIFECYCLE_COMPLETION]))
    query = query.filter(
        models.Action.action.in_(consts.CLUSTER_SCALE_ACTIONS))
    scaling_actions = query.all()
    return scaling_actions


def action_get_by_name(context, name, project_safe=True):
    return query_by_name(context, action_model_query, name,
                         project_safe=project_safe)


def action_get_by_short_id(context, short_id, project_safe=True):
    return query_by_short_id(context, action_model_query, models.Action,
                             short_id, project_safe=project_safe)


def action_get_all_by_owner(context, owner_id):
    query = action_model_query().filter_by(owner=owner_id)
    return query.all()


def action_get_all_active_by_target(context, target_id, project_safe=True):
    query = action_model_query()
    query = utils.filter_query_by_project(query, project_safe, context)
    query = query.filter_by(target=target_id)
    query = query.filter(
        models.Action.status.in_(
            [consts.ACTION_READY,
             consts.ACTION_WAITING,
             consts.ACTION_RUNNING,
             consts.ACTION_WAITING_LIFECYCLE_COMPLETION]))
    actions = query.all()
    return actions


def action_get_all(context, filters=None, limit=None, marker=None, sort=None,
                   project_safe=True):
    query = action_model_query()
    query = utils.filter_query_by_project(query, project_safe, context)

    if filters:
        query = utils.exact_filter(query, models.Action, filters)

    keys, dirs = utils.get_sort_params(sort, consts.ACTION_CREATED_AT)
    if marker:
        marker = action_model_query().get(marker)
    return sa_utils.paginate_query(query, models.Action, limit, keys,
                                   marker=marker, sort_dirs=dirs).all()


@retry_on_deadlock
def action_check_status(context, action_id, timestamp):
    with session_for_write() as session:
        q = session.query(models.ActionDependency)
        count = q.filter_by(dependent=action_id).count()
        if count > 0:
            return consts.ACTION_WAITING

        action = session.query(models.Action).get(action_id)
        if action.status == consts.ACTION_WAITING:
            action.status = consts.ACTION_READY
            action.status_reason = 'All depended actions completed.'
            action.end_time = timestamp
            action.save(session)

        return action.status


def action_dependency_model_query():
    with session_for_read() as session:
        query = session.query(models.ActionDependency)
        return query


@retry_on_deadlock
def dependency_get_depended(context, action_id):
    q = action_dependency_model_query().filter_by(
        dependent=action_id)
    return [d.depended for d in q.all()]


@retry_on_deadlock
def dependency_get_dependents(context, action_id):
    q = action_dependency_model_query().filter_by(
        depended=action_id)
    return [d.dependent for d in q.all()]


@retry_on_deadlock
def dependency_add(context, depended, dependent):
    if isinstance(depended, list) and isinstance(dependent, list):
        raise exception.Error(
            'Multiple dependencies between lists not support')

    with session_for_write() as session:
        if isinstance(depended, list):   # e.g. D depends on A,B,C
            for d in depended:
                r = models.ActionDependency(depended=d, dependent=dependent)
                session.add(r)

            query = session.query(models.Action).with_for_update()
            query = query.filter_by(id=dependent)
            query.update({'status': consts.ACTION_WAITING,
                          'status_reason': 'Waiting for depended actions.'},
                         synchronize_session='fetch')
            return

        # Only dependent can be a list now, convert it to a list if it
        # is not a list
        if not isinstance(dependent, list):  # e.g. B,C,D depend on A
            dependents = [dependent]
        else:
            dependents = dependent

        for d in dependents:
            r = models.ActionDependency(depended=depended, dependent=d)
            session.add(r)

        q = session.query(models.Action).with_for_update()
        q = q.filter(models.Action.id.in_(dependents))
        q.update({'status': consts.ACTION_WAITING,
                  'status_reason': 'Waiting for depended actions.'},
                 synchronize_session='fetch')


@retry_on_deadlock
def action_mark_succeeded(context, action_id, timestamp):
    with session_for_write() as session:

        query = session.query(models.Action).filter_by(id=action_id)
        values = {
            'owner': None,
            'status': consts.ACTION_SUCCEEDED,
            'status_reason': 'Action completed successfully.',
            'end_time': timestamp,
        }
        query.update(values, synchronize_session=False)

        subquery = session.query(models.ActionDependency).filter_by(
            depended=action_id)
        subquery.delete(synchronize_session='fetch')


@retry_on_deadlock
def action_mark_ready(context, action_id, timestamp):
    with session_for_write() as session:

        query = session.query(models.Action).filter_by(id=action_id)
        values = {
            'owner': None,
            'status': consts.ACTION_READY,
            'status_reason': 'Lifecycle timeout.',
            'end_time': timestamp,
        }
        query.update(values, synchronize_session=False)


@retry_on_deadlock
def _mark_failed(action_id, timestamp, reason=None):
    # mark myself as failed
    with session_for_write() as session:
        query = session.query(models.Action).filter_by(id=action_id)
        values = {
            'owner': None,
            'status': consts.ACTION_FAILED,
            'status_reason': (str(reason) if reason else
                              'Action execution failed'),
            'end_time': timestamp,
        }
        query.update(values, synchronize_session=False)
        action = query.all()

        query = session.query(models.ActionDependency)
        query = query.filter_by(depended=action_id)
        dependents = [d.dependent for d in query.all()]
        query.delete(synchronize_session=False)

    if parent_status_update_needed(action):
        for d in dependents:
            _mark_failed(d, timestamp)


@retry_on_deadlock
def action_mark_failed(context, action_id, timestamp, reason=None):
    _mark_failed(action_id, timestamp, reason)


@retry_on_deadlock
def _mark_cancelled(session, action_id, timestamp, reason=None):
    query = session.query(models.Action).filter_by(id=action_id)
    values = {
        'owner': None,
        'status': consts.ACTION_CANCELLED,
        'status_reason': (str(reason) if reason else
                          'Action execution cancelled'),
        'end_time': timestamp,
    }
    query.update(values, synchronize_session=False)
    action = query.all()

    query = session.query(models.ActionDependency)
    query = query.filter_by(depended=action_id)
    dependents = [d.dependent for d in query.all()]
    query.delete(synchronize_session=False)

    if parent_status_update_needed(action):
        for d in dependents:
            _mark_cancelled(session, d, timestamp)


@retry_on_deadlock
def action_mark_cancelled(context, action_id, timestamp, reason=None):
    with session_for_write() as session:
        _mark_cancelled(session, action_id, timestamp, reason)


@retry_on_deadlock
def action_acquire(context, action_id, owner, timestamp):
    with session_for_write() as session:
        action = session.query(models.Action).with_for_update().get(action_id)
        if not action:
            return None

        if action.owner and action.owner != owner:
            return None

        if action.status != consts.ACTION_READY:
            return None
        action.owner = owner
        action.start_time = timestamp
        action.status = consts.ACTION_RUNNING
        action.status_reason = 'The action is being processed.'
        action.save(session)

        return action


@retry_on_deadlock
def action_acquire_random_ready(context, owner, timestamp):
    with session_for_write() as session:
        action = (session.query(models.Action).
                  filter_by(status=consts.ACTION_READY).
                  filter_by(owner=None).
                  order_by(func.random()).
                  with_for_update().first())

        if action:
            action.owner = owner
            action.start_time = timestamp
            action.status = consts.ACTION_RUNNING
            action.status_reason = 'The action is being processed.'
            action.save(session)

            return action


@retry_on_deadlock
def action_acquire_first_ready(context, owner, timestamp):
    with session_for_write() as session:
        action = session.query(models.Action).filter_by(
            status=consts.ACTION_READY).filter_by(
            owner=None).order_by(
            consts.ACTION_CREATED_AT or func.random()).first()
    if action:
        return action_acquire(context, action.id, owner, timestamp)


@retry_on_deadlock
def action_abandon(context, action_id, values=None):
    """Abandon an action for other workers to execute again.

    This API is always called with the action locked by the current
    worker. There is no chance the action is gone or stolen by others.
    """
    with session_for_write() as session:
        action = session.query(models.Action).get(action_id)

        action.owner = None
        action.start_time = None
        action.status = consts.ACTION_READY
        action.status_reason = 'The action was abandoned.'
        if values:
            action.update(values)
        action.save(session)
        return action


@retry_on_deadlock
def action_lock_check(context, action_id, owner=None):
    action = action_model_query().get(action_id)
    if not action:
        raise exception.ResourceNotFound(type='action', id=action_id)

    if owner:
        return owner if owner == action.owner else action.owner
    else:
        return action.owner if action.owner else None


@retry_on_deadlock
def action_signal(context, action_id, value):
    with session_for_write() as session:
        action = session.query(models.Action).get(action_id)
        if not action:
            return

        action.control = value
        action.save(session)


def action_signal_query(context, action_id):
    action = action_model_query().get(action_id)
    if not action:
        return None

    return action.control


@retry_on_deadlock
def action_delete(context, action_id):
    with session_for_write() as session:
        action = session.query(models.Action).get(action_id)
        if not action:
            return
        if ((action.status == consts.ACTION_WAITING) or
                (action.status == consts.ACTION_RUNNING) or
                (action.status == consts.ACTION_SUSPENDED)):

            raise exception.EResourceBusy(type='action', id=action_id)
        session.delete(action)


@retry_on_deadlock
def action_delete_by_target(context, target, action=None,
                            action_excluded=None, status=None,
                            project_safe=True):
    if action and action_excluded:
        LOG.warning("action and action_excluded cannot be both specified.")
        return None

    with session_for_write() as session:
        q = session.query(models.Action).filter_by(target=target)
        q = utils.filter_query_by_project(q, project_safe, context)

        if action:
            q = q.filter(models.Action.action.in_(action))
        if action_excluded:
            q = q.filter(~models.Action.action.in_(action_excluded))
        if status:
            q = q.filter(models.Action.status.in_(status))
        return q.delete(synchronize_session='fetch')


@retry_on_deadlock
def action_purge(project, granularity='days', age=30):
    with session_for_write() as session:
        query = session.query(models.Action).with_for_update()
        if project is not None:
            query = query.filter(models.Action.project.in_(project))
        if granularity is not None and age is not None:
            if granularity == 'days':
                age = age * 86400
            elif granularity == 'hours':
                age = age * 3600
            elif granularity == 'minutes':
                age = age * 60
            time_line = timeutils.utcnow() - datetime.timedelta(seconds=age)
            query = query.filter(models.Action.created_at < time_line)

        # Get dependants to delete
        for d in query.all():
            q = session.query(models.ActionDependency).filter_by(depended=d.id)
            q.delete(synchronize_session='fetch')
        return query.delete(synchronize_session='fetch')


# Receivers
def receiver_model_query():
    with session_for_read() as session:
        query = session.query(models.Receiver)
        return query


@retry_on_deadlock
def receiver_create(context, values):
    with session_for_write() as session:
        receiver = models.Receiver()
        receiver.update(values)
        session.add(receiver)
        return receiver


def receiver_get(context, receiver_id, project_safe=True):
    receiver = receiver_model_query().get(receiver_id)
    if not receiver:
        return None

    return utils.check_resource_project(context, receiver, project_safe)


def receiver_get_all(context, limit=None, marker=None, filters=None, sort=None,
                     project_safe=True):
    query = receiver_model_query()
    query = utils.filter_query_by_project(query, project_safe, context)

    if filters:
        query = utils.exact_filter(query, models.Receiver, filters)

    keys, dirs = utils.get_sort_params(sort, consts.RECEIVER_NAME)
    if marker:
        marker = receiver_model_query().get(marker)
    return sa_utils.paginate_query(query, models.Receiver, limit, keys,
                                   marker=marker, sort_dirs=dirs).all()


def receiver_get_by_name(context, name, project_safe=True):
    return query_by_name(context, receiver_model_query, name,
                         project_safe=project_safe)


def receiver_get_by_short_id(context, short_id, project_safe=True):
    return query_by_short_id(context, receiver_model_query, models.Receiver,
                             short_id, project_safe=project_safe)


@retry_on_deadlock
def receiver_delete(context, receiver_id):
    with session_for_write() as session:
        receiver = session.query(models.Receiver).get(receiver_id)
        if not receiver:
            return
        session.delete(receiver)


@retry_on_deadlock
def receiver_update(context, receiver_id, values):
    with session_for_write() as session:
        receiver = session.query(models.Receiver).get(receiver_id)
        if not receiver:
            raise exception.ResourceNotFound(type='receiver', id=receiver_id)

        receiver.update(values)
        receiver.save(session)
        return receiver


@retry_on_deadlock
def service_create(service_id, host=None, binary=None, topic=None):
    with session_for_write() as session:
        time_now = timeutils.utcnow(True)
        svc = models.Service(id=service_id, host=host, binary=binary,
                             topic=topic, created_at=time_now,
                             updated_at=time_now)
        session.add(svc)
        return svc


@retry_on_deadlock
def service_update(service_id, values=None):
    with session_for_write() as session:
        service = session.query(models.Service).get(service_id)
        if not service:
            return

        if values is None:
            values = {}

        values.update({'updated_at': timeutils.utcnow(True)})
        service.update(values)
        service.save(session)
        return service


@retry_on_deadlock
def service_delete(service_id):
    with session_for_write() as session:
        session.query(models.Service).filter_by(
            id=service_id).delete(synchronize_session='fetch')


def service_get(service_id):
    with session_for_read() as session:
        return session.query(models.Service).get(service_id)


def service_get_all():
    with session_for_read() as session:
        return session.query(models.Service).all()


def service_get_all_expired(binary):
    with session_for_read() as session:
        date_limit = service_expired_time()
        svc = models.Service
        return session.query(models.Service).filter(
            and_(svc.binary == binary, svc.updated_at <= date_limit)
        )


@retry_on_deadlock
def _mark_engine_failed(session, action_id, timestamp, reason=None):
    query = session.query(models.ActionDependency)
    # process cluster actions
    d_query = query.filter_by(dependent=action_id)
    dependents = [d.depended for d in d_query.all()]
    if dependents:
        for d in dependents:
            _mark_engine_failed(session, d, timestamp, reason)
    else:
        depended = query.filter_by(depended=action_id)
        depended.delete(synchronize_session=False)

    # TODO(anyone): this will mark all depended actions' status to 'FAILED'
    # even the action belong to other engines and the action is running
    # mark myself as failed
    action = session.query(models.Action).filter_by(id=action_id).first()
    values = {
        'owner': None,
        'status': consts.ACTION_FAILED,
        'status_reason': (str(reason) if reason else
                          'Action execution failed'),
        'end_time': timestamp,
    }
    action.update(values)
    action.save(session)


@retry_on_deadlock
def dummy_gc(engine_id):
    with session_for_write() as session:
        q_actions = session.query(models.Action).filter_by(owner=engine_id)
        timestamp = time.time()
        for action in q_actions.all():
            _mark_engine_failed(session, action.id, timestamp,
                                reason='Engine failure')
            # Release all node locks
            query = (session.query(models.NodeLock).
                     filter_by(action_id=action.id))
            query.delete(synchronize_session=False)

            # Release all cluster locks
            for clock in session.query(models.ClusterLock).all():
                res = _release_cluster_lock(session, clock, action.id, -1)
                if not res:
                    _release_cluster_lock(session, clock, action.id, 1)


@retry_on_deadlock
def gc_by_engine(engine_id):
    # Get all actions locked by an engine
    with session_for_write() as session:
        q_actions = session.query(models.Action).filter_by(owner=engine_id)
        timestamp = time.time()
        for a in q_actions.all():
            # Release all node locks
            query = session.query(models.NodeLock).filter_by(action_id=a.id)
            query.delete(synchronize_session=False)

            # Release all cluster locks
            for cl in session.query(models.ClusterLock).all():
                res = _release_cluster_lock(session, cl, a.id, -1)
                if not res:
                    _release_cluster_lock(session, cl, a.id, 1)

            # mark action failed and release lock
            _mark_failed(a.id, timestamp, reason="Engine failure")


# HealthRegistry
def health_registry_model_query():
    with session_for_read() as session:
        query = session.query(models.HealthRegistry)
        return query


@retry_on_deadlock
def registry_create(context, cluster_id, check_type, interval, params,
                    engine_id, enabled=True):
    with session_for_write() as session:
        registry = models.HealthRegistry()
        registry.cluster_id = cluster_id
        registry.check_type = check_type
        registry.interval = interval
        registry.params = params
        registry.engine_id = engine_id
        registry.enabled = enabled
        session.add(registry)
        return registry


@retry_on_deadlock
def registry_update(context, cluster_id, values):
    with session_for_write() as session:
        query = session.query(models.HealthRegistry).with_for_update()
        registry = query.filter_by(cluster_id=cluster_id).first()
        if registry:
            registry.update(values)
            registry.save(session)


@retry_on_deadlock
def registry_claim(context, engine_id):
    with session_for_write() as session:
        engines = session.query(models.Service).all()
        svc_ids = [e.id for e in engines if not utils.is_service_dead(e)]
        q_reg = session.query(models.HealthRegistry).with_for_update()
        if svc_ids:
            q_reg = q_reg.filter(
                models.HealthRegistry.engine_id.notin_(svc_ids))

        result = q_reg.all()
        q_reg.update({'engine_id': engine_id}, synchronize_session=False)

        return result


@retry_on_deadlock
def registry_delete(context, cluster_id):
    with session_for_write() as session:
        registry = session.query(models.HealthRegistry).filter_by(
            cluster_id=cluster_id).first()
        if registry is None:
            return
        session.delete(registry)


def registry_get(context, cluster_id):
    with session_for_read() as session:
        registry = session.query(models.HealthRegistry).filter_by(
            cluster_id=cluster_id).first()

        return registry


def registry_get_by_param(context, params):
    query = health_registry_model_query()
    obj = utils.exact_filter(query, models.HealthRegistry, params).first()
    return obj


def registry_list_ids_by_service(context, engine_id):
    with session_for_read() as session:
        return session.query(models.HealthRegistry.cluster_id).filter_by(
            engine_id=engine_id).all()


# Utils
def db_sync(db_url):
    """Migrate the database to `version` or the most recent version."""
    return migration.db_sync(db_url)


def db_version():
    """Display the current database version."""
    return migration.db_version()


def parent_status_update_needed(action):
    """Return if the status of the parent action needs to be updated

    Return value for update_parent_status key in action inputs
    """
    return (len(action) > 0 and hasattr(action[0], 'inputs') and
            action[0].inputs.get('update_parent_status', True))
