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

import six
import sys
import threading

from oslo_config import cfg
from oslo_db import api as oslo_db_api
from oslo_db import exception as db_exc
from oslo_db.sqlalchemy import enginefacade
from oslo_db.sqlalchemy import utils as sa_utils
from oslo_log import log as logging
from oslo_utils import timeutils
from sqlalchemy.orm import joinedload_all

from senlin.common import consts
from senlin.common import exception
from senlin.common.i18n import _
from senlin.db.sqlalchemy import migration
from senlin.db.sqlalchemy import models
from senlin.db.sqlalchemy import utils

LOG = logging.getLogger(__name__)


CONF = cfg.CONF
CONF.import_opt('max_events_per_cluster', 'senlin.common.config')

_main_context_manager = None
_CONTEXT = threading.local()


def _get_main_context_manager():
    global _main_context_manager
    if not _main_context_manager:
        _main_context_manager = enginefacade.transaction_context()
    return _main_context_manager


def get_engine():
    return _get_main_context_manager().get_legacy_facade().get_engine()


def get_session():
    return _get_main_context_manager().get_legacy_facade().get_session()


def session_for_read():
    return _get_main_context_manager().reader.using(_CONTEXT)


def session_for_write():
    return _get_main_context_manager().writer.using(_CONTEXT)


def get_backend():
    """The backend is this module itself."""
    return sys.modules[__name__]


def model_query(context, *args):
    with session_for_read() as session:
        query = session.query(*args).options(joinedload_all('*'))
        return query


def query_by_short_id(context, model, short_id, project_safe=True):
    q = model_query(context, model)
    q = q.filter(model.id.like('%s%%' % short_id))

    if not context.is_admin and project_safe:
        q = q.filter_by(project=context.project)

    if q.count() == 1:
        return q.first()
    elif q.count() == 0:
        return None
    else:
        raise exception.MultipleChoices(arg=short_id)


def query_by_name(context, model, name, project_safe=True):
    q = model_query(context, model)
    q = q.filter_by(name=name)

    if not context.is_admin and project_safe:
        q = q.filter_by(project=context.project)

    if q.count() == 1:
        return q.first()
    elif q.count() == 0:
        return None
    else:
        raise exception.MultipleChoices(arg=name)


# Clusters
def cluster_create(context, values):
    with session_for_write() as session:
        cluster_ref = models.Cluster()
        cluster_ref.update(values)
        session.add(cluster_ref)
        return cluster_ref


def cluster_get(context, cluster_id, project_safe=True):
    cluster = model_query(context, models.Cluster).get(cluster_id)

    if cluster is None:
        return None

    if not context.is_admin and project_safe:
        if context.project != cluster.project:
            return None
    return cluster


def cluster_get_by_name(context, name, project_safe=True):
    return query_by_name(context, models.Cluster, name,
                         project_safe=project_safe)


def cluster_get_by_short_id(context, short_id, project_safe=True):
    return query_by_short_id(context, models.Cluster, short_id,
                             project_safe=project_safe)


def _query_cluster_get_all(context, project_safe=True):
    query = model_query(context, models.Cluster)

    if not context.is_admin and project_safe:
        query = query.filter_by(project=context.project)
    return query


def cluster_get_all(context, limit=None, marker=None, sort=None, filters=None,
                    project_safe=True):
    query = _query_cluster_get_all(context, project_safe=project_safe)
    if filters:
        query = utils.exact_filter(query, models.Cluster, filters)

    keys, dirs = utils.get_sort_params(sort, consts.CLUSTER_INIT_AT)
    if marker:
        marker = model_query(context, models.Cluster).get(marker)

    return sa_utils.paginate_query(query, models.Cluster, limit, keys,
                                   marker=marker, sort_dirs=dirs).all()


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


def cluster_update(context, cluster_id, values):
    with session_for_write() as session:
        cluster = session.query(models.Cluster).get(cluster_id)

        if not cluster:
            raise exception.ClusterNotFound(cluster=cluster_id)

        cluster.update(values)
        cluster.save(session)


def cluster_delete(context, cluster_id):
    with session_for_write() as session:
        cluster = session.query(models.Cluster).get(cluster_id)
        if cluster is None:
            raise exception.ClusterNotFound(cluster=cluster_id)

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
def node_create(context, values):
    # This operation is always called with cluster and node locked
    with session_for_write() as session:
        node = models.Node()
        node.update(values)
        session.add(node)
        return node


def node_get(context, node_id, project_safe=True):
    node = model_query(context, models.Node).get(node_id)
    if not node:
        return None

    if not context.is_admin and project_safe:
        if context.project != node.project:
            return None

    return node


def node_get_by_name(context, name, project_safe=True):
    return query_by_name(context, models.Node, name, project_safe=project_safe)


def node_get_by_short_id(context, short_id, project_safe=True):
    return query_by_short_id(context, models.Node, short_id,
                             project_safe=project_safe)


def _query_node_get_all(context, project_safe=True, cluster_id=None):
    query = model_query(context, models.Node)

    if cluster_id is not None:
        query = query.filter_by(cluster_id=cluster_id)

    if not context.is_admin and project_safe:
        query = query.filter_by(project=context.project)

    return query


def node_get_all(context, cluster_id=None, limit=None, marker=None, sort=None,
                 filters=None, project_safe=True):
    query = _query_node_get_all(context, project_safe=project_safe,
                                cluster_id=cluster_id)

    if filters:
        query = utils.exact_filter(query, models.Node, filters)

    keys, dirs = utils.get_sort_params(sort, consts.NODE_INIT_AT)
    if marker:
        marker = model_query(context, models.Node).get(marker)
    return sa_utils.paginate_query(query, models.Node, limit, keys,
                                   marker=marker, sort_dirs=dirs).all()


def node_get_all_by_cluster(context, cluster_id, project_safe=True):
    return _query_node_get_all(context, cluster_id=cluster_id,
                               project_safe=project_safe).all()


def node_count_by_cluster(context, cluster_id, project_safe=True):
    return _query_node_get_all(context, cluster_id=cluster_id,
                               project_safe=project_safe).count()


def node_update(context, node_id, values):
    '''Update a node with new property values.

    :param node_id: ID of the node to be updated.
    :param values: A dictionary of values to be updated on the node.
    :raises ClusterNotFound: The specified node does not exist in database.
    '''
    with session_for_write() as session:
        node = session.query(models.Node).get(node_id)
        if not node:
            raise exception.NodeNotFound(node=node_id)

        node.update(values)
        node.save(session)
        if 'status' in values and node.cluster_id is not None:
            cluster = session.query(models.Cluster).get(node.cluster_id)
            if cluster is not None:
                if values['status'] == 'ERROR':
                    cluster.status = 'WARNING'
                if 'status_reason' in values:
                    cluster.status_reason = _('Node %(node)s: %(reason)s') % {
                        'node': node.name, 'reason': values['status_reason']}
                cluster.save(session)


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


def node_delete(context, node_id, force=False):
    with session_for_write() as session:
        node = session.query(models.Node).get(node_id)
        if not node:
            # Note: this is okay, because the node may have already gone
            return
        session.delete(node)


# Locks
def cluster_lock_acquire(cluster_id, action_id, scope):
    '''Acquire lock on a cluster.

    :param cluster_id: ID of the cluster.
    :param action_id: ID of the action that attempts to lock the cluster.
    :param scope: +1 means a node-level operation lock; -1 indicates
                  a cluster-level lock.
    :return: A list of action IDs that currently works on the cluster.
    '''
    with session_for_write() as session:
        lock = session.query(models.ClusterLock).get(cluster_id)
        if lock is not None:
            if scope == 1 and lock.semaphore > 0:
                if action_id not in lock.action_ids:
                    lock.action_ids.append(six.text_type(action_id))
                    lock.semaphore += 1
                    lock.save(session)
        else:
            lock = models.ClusterLock(cluster_id=cluster_id,
                                      action_ids=[six.text_type(action_id)],
                                      semaphore=scope)
            session.add(lock)

        return lock.action_ids


def cluster_lock_release(cluster_id, action_id, scope):
    '''Release lock on a cluster.

    :param cluster_id: ID of the cluster.
    :param action_id: ID of the action that attempts to release the cluster.
    :param scope: +1 means a node-level operation lock; -1 indicates
                  a cluster-level lock.
    :return: True indicates successful release, False indicates failure.
    '''
    with session_for_write() as session:
        lock = session.query(models.ClusterLock).get(cluster_id)
        if lock is None:
            return False

        success = False
        if scope == -1 or lock.semaphore == 1:
            if six.text_type(action_id) in lock.action_ids:
                session.delete(lock)
                success = True
        elif action_id in lock.action_ids:
            if lock.semaphore == 1:
                session.delete(lock)
            else:
                lock.action_ids.remove(six.text_type(action_id))
                lock.semaphore -= 1
                lock.save(session)
            success = True

        return success


def cluster_lock_steal(cluster_id, action_id):
    with session_for_write() as session:
        lock = session.query(models.ClusterLock).get(cluster_id)
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


def node_lock_acquire(node_id, action_id):
    with session_for_write() as session:
        lock = session.query(models.NodeLock).get(node_id)
        if lock is None:
            lock = models.NodeLock(node_id=node_id, action_id=action_id)
            session.add(lock)

        return lock.action_id


def node_lock_release(node_id, action_id):
    with session_for_write() as session:

        success = False
        lock = session.query(models.NodeLock).get(node_id)
        if lock is not None and lock.action_id == action_id:
            session.delete(lock)
            success = True

        return success


def node_lock_steal(node_id, action_id):
    with session_for_write() as session:
        lock = session.query(models.NodeLock).get(node_id)
        if lock is not None:
            lock.action_id = action_id
            lock.save(session)
        else:
            lock = models.NodeLock(node_id=node_id, action_id=action_id)
            session.add(lock)
        return lock.action_id


# Policies
def policy_create(context, values):
    with session_for_write() as session:
        policy = models.Policy()
        policy.update(values)
        session.add(policy)
        return policy


def policy_get(context, policy_id, project_safe=True):
    policy = model_query(context, models.Policy)
    policy = policy.filter_by(id=policy_id).first()

    if policy is None:
        return None

    if not context.is_admin and project_safe:
        if context.project != policy.project:
            return None

    return policy


def policy_get_by_name(context, name, project_safe=True):
    return query_by_name(context, models.Policy, name,
                         project_safe=project_safe)


def policy_get_by_short_id(context, short_id, project_safe=True):
    return query_by_short_id(context, models.Policy, short_id,
                             project_safe=project_safe)


def policy_get_all(context, limit=None, marker=None, sort=None, filters=None,
                   project_safe=True):
    query = model_query(context, models.Policy)

    if not context.is_admin and project_safe:
        query = query.filter_by(project=context.project)

    if filters:
        query = utils.exact_filter(query, models.Policy, filters)

    keys, dirs = utils.get_sort_params(sort, consts.POLICY_CREATED_AT)
    if marker:
        marker = model_query(context, models.Policy).get(marker)
    return sa_utils.paginate_query(query, models.Policy, limit, keys,
                                   marker=marker, sort_dirs=dirs).all()


def policy_update(context, policy_id, values):
    with session_for_write() as session:
        policy = session.query(models.Policy).get(policy_id)
        if not policy:
            raise exception.PolicyNotFound(policy=policy_id)

        policy.update(values)
        policy.save(session)
        return policy


def policy_delete(context, policy_id, force=False):
    with session_for_write() as session:
        policy = session.query(models.Policy).get(policy_id)

        if not policy:
            return

        bindings = session.query(models.ClusterPolicies).filter_by(
            policy_id=policy_id)
        if bindings.count():
            raise exception.ResourceBusyError(resource_type='policy',
                                              resource_id=policy_id)
        session.delete(policy)


# Cluster-Policy Associations
def cluster_policy_get(context, cluster_id, policy_id):
    query = model_query(context, models.ClusterPolicies)
    bindings = query.filter_by(cluster_id=cluster_id,
                               policy_id=policy_id)
    return bindings.first()


def cluster_policy_get_all(context, cluster_id, filters=None, sort=None):

    query = model_query(context, models.ClusterPolicies)
    query = query.filter_by(cluster_id=cluster_id)

    if filters:
        query = utils.exact_filter(query, models.ClusterPolicies, filters)

    keys, dirs = utils.get_sort_params(sort)
    return sa_utils.paginate_query(query, models.ClusterPolicies, None, keys,
                                   sort_dirs=dirs).all()


def cluster_policy_get_by_type(context, cluster_id, policy_type, filters=None):

    query = model_query(context, models.ClusterPolicies)
    query = query.filter_by(cluster_id=cluster_id)

    if filters:
        query = utils.exact_filter(query, models.ClusterPolicies, filters)

    query = query.join(models.Policy).filter(models.Policy.type == policy_type)

    return query.all()


def cluster_policy_attach(context, cluster_id, policy_id, values):
    with session_for_write() as session:
        binding = models.ClusterPolicies()
        binding.cluster_id = cluster_id
        binding.policy_id = policy_id
        binding.update(values)
        session.add(binding)
    # Load foreignkey cluster and policy
    return cluster_policy_get(context, cluster_id, policy_id)


def cluster_policy_detach(context, cluster_id, policy_id):
    with session_for_write() as session:
        query = session.query(models.ClusterPolicies)
        bindings = query.filter_by(cluster_id=cluster_id,
                                   policy_id=policy_id).first()
        if bindings is None:
            return
        session.delete(bindings)


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


# Profiles
def profile_create(context, values):
    with session_for_write() as session:
        profile = models.Profile()
        profile.update(values)
        session.add(profile)
        return profile


def profile_get(context, profile_id, project_safe=True):
    query = model_query(context, models.Profile)
    profile = query.filter_by(id=profile_id).first()

    if profile is None:
        return None

    if not context.is_admin and project_safe:
        if context.project != profile.project:
            return None

    return profile


def profile_get_by_name(context, name, project_safe=True):
    return query_by_name(context, models.Profile, name,
                         project_safe=project_safe)


def profile_get_by_short_id(context, short_id, project_safe=True):
    return query_by_short_id(context, models.Profile, short_id,
                             project_safe=project_safe)


def profile_get_all(context, limit=None, marker=None, sort=None, filters=None,
                    project_safe=True):
    query = model_query(context, models.Profile)

    if not context.is_admin and project_safe:
        query = query.filter_by(project=context.project)

    if filters:
        query = utils.exact_filter(query, models.Profile, filters)

    keys, dirs = utils.get_sort_params(sort, consts.PROFILE_CREATED_AT)
    if marker:
        marker = model_query(context, models.Profile).get(marker)
    return sa_utils.paginate_query(query, models.Profile, limit, keys,
                                   marker=marker, sort_dirs=dirs).all()


def profile_update(context, profile_id, values):
    with session_for_write() as session:
        profile = session.query(models.Profile).get(profile_id)
        if not profile:
            raise exception.ProfileNotFound(profile=profile_id)

        profile.update(values)
        profile.save(session)
        return profile


def profile_delete(context, profile_id, force=False):
    with session_for_write() as session:
        profile = session.query(models.Profile).get(profile_id)
        if profile is None:
            return

        # used by any clusters?
        clusters = session.query(models.Cluster).filter_by(
            profile_id=profile_id)
        if clusters.count() > 0:
            raise exception.ResourceBusyError(resource_type='profile',
                                              resource_id=profile_id)

        # used by any nodes?
        nodes = session.query(models.Node).filter_by(profile_id=profile_id)
        if nodes.count() > 0:
            raise exception.ResourceBusyError(resource_type='profile',
                                              resource_id=profile_id)
        session.delete(profile)


# Credentials
def cred_create(context, values):
    with session_for_write() as session:
        cred = models.Credential()
        cred.update(values)
        session.add(cred)
        return cred


def cred_get(context, user, project):
    return model_query(context, models.Credential).get((user, project))


def cred_update(context, user, project, values):
    with session_for_write() as session:
        cred = session.query(models.Credential).get((user, project))
        cred.update(values)
        cred.save(session)
        return cred


def cred_delete(context, user, project):
    with session_for_write() as session:
        cred = session.query(models.Credential).get((user, project))
        if cred is None:
            return None
        session.delete(cred)


def cred_create_update(context, values):
    try:
        return cred_create(context, values)
    except db_exc.DBDuplicateEntry:
        user = values.pop('user')
        project = values.pop('project')
        return cred_update(context, user, project, values)


# Events
def _delete_event_rows(context, cluster_id, limit):
    # MySQL does not support LIMIT in subqueries,
    # sqlite does not support JOIN in DELETE.
    # So we must manually supply the IN() values.
    # pgsql SHOULD work with the pure DELETE/JOIN below but that must be
    # confirmed via integration tests.
    query = event_count_by_cluster(context, cluster_id)
    with session_for_write() as session:
        all_events = query.order_by(models.Event.timestamp).limit(limit).all()
        ids = [r.id for r in all_events]
        q = session.query(models.Event).filter(models.Event.id.in_(ids))
        return q.delete(synchronize_session='fetch')


def event_prune(context, cluster_id):
    if cfg.CONF.max_events_per_cluster:
        event_count = event_count_by_cluster(context, cluster_id)
        if (event_count >= cfg.CONF.max_events_per_cluster):
            # prune events
            batch_size = cfg.CONF.event_purge_batch_size
            _delete_event_rows(context, cluster_id, batch_size)


def event_create(context, values):
    with session_for_write() as session:
        event = models.Event()
        event.update(values)
        session.add(event)
        return event


def event_get(context, event_id, project_safe=True):
    event = model_query(context, models.Event).get(event_id)
    if not context.is_admin and project_safe and event is not None:
        if event.project != context.project:
            return None

    return event


def event_get_by_short_id(context, short_id, project_safe=True):
    return query_by_short_id(context, models.Event, short_id,
                             project_safe=project_safe)


def _event_filter_paginate_query(context, query, filters=None,
                                 limit=None, marker=None, sort=None):
    if filters:
        query = utils.exact_filter(query, models.Event, filters)

    keys, dirs = utils.get_sort_params(sort, consts.EVENT_TIMESTAMP)
    if marker:
        marker = model_query(context, models.Event).get(marker)
    return sa_utils.paginate_query(query, models.Event, limit, keys,
                                   marker=marker, sort_dirs=dirs).all()


def event_get_all(context, limit=None, marker=None, sort=None, filters=None,
                  project_safe=True):
    query = model_query(context, models.Event)
    if not context.is_admin and project_safe:
        query = query.filter_by(project=context.project)

    return _event_filter_paginate_query(context, query, filters=filters,
                                        limit=limit, marker=marker, sort=sort)


def event_count_by_cluster(context, cluster_id, project_safe=True):
    query = model_query(context, models.Event)

    if not context.is_admin and project_safe:
        query = query.filter_by(project=context.project)
    count = query.filter_by(cluster_id=cluster_id).count()

    return count


def event_get_all_by_cluster(context, cluster_id, limit=None, marker=None,
                             sort=None, filters=None, project_safe=True):
    query = model_query(context, models.Event)
    query = query.filter_by(cluster_id=cluster_id)

    if not context.is_admin and project_safe:
        query = query.filter_by(project=context.project)

    return _event_filter_paginate_query(context, query, filters=filters,
                                        limit=limit, marker=marker, sort=sort)


# Actions
def action_create(context, values):
    with session_for_write() as session:
        action = models.Action()
        action.update(values)
        session.add(action)
        return action


def action_update(context, action_id, values):
    with session_for_write() as session:
        action = session.query(models.Action).get(action_id)
        if not action:
            raise exception.ActionNotFound(action=action_id)

        action.update(values)
        action.save(session)


def action_get(context, action_id, project_safe=True, refresh=False):
    with session_for_read() as session:
        action = session.query(models.Action).get(action_id)
        if action is None:
            return None

        if not context.is_admin and project_safe:
            if action.project != context.project:
                return None

        session.refresh(action)
        return action


def action_get_by_name(context, name, project_safe=True):
    return query_by_name(context, models.Action, name,
                         project_safe=project_safe)


def action_get_by_short_id(context, short_id, project_safe=True):
    return query_by_short_id(context, models.Action, short_id,
                             project_safe=project_safe)


def action_get_all_by_owner(context, owner_id):
    query = model_query(context, models.Action).\
        filter_by(owner=owner_id)
    return query.all()


def action_get_all(context, filters=None, limit=None, marker=None, sort=None,
                   project_safe=True):

    query = model_query(context, models.Action)
    # TODO(Qiming): Enable multi-tenancy for actions
    # if project_safe:
    #    query = query.filter_by(project=context.project)

    if filters:
        query = utils.exact_filter(query, models.Action, filters)

    keys, dirs = utils.get_sort_params(sort, consts.ACTION_CREATED_AT)
    if marker:
        marker = model_query(context, models.Action).get(marker)
    return sa_utils.paginate_query(query, models.Action, limit, keys,
                                   marker=marker, sort_dirs=dirs).all()


def action_check_status(context, action_id, timestamp):
    with session_for_write() as session:
        q = session.query(models.ActionDependency)
        count = q.filter_by(dependent=action_id).count()
        if count > 0:
            return consts.ACTION_WAITING

        action = session.query(models.Action).get(action_id)
        if action.status == consts.ACTION_WAITING:
            action.status = consts.ACTION_READY
            action.status_reason = _('All depended actions completed.')
            action.end_time = timestamp
            action.save(session)

        return action.status


def dependency_get_depended(context, action_id):
    with session_for_read() as session:
        q = session.query(models.ActionDependency).filter_by(
            dependent=action_id)
        return [d.depended for d in q.all()]


def dependency_get_dependents(context, action_id):
    with session_for_read() as session:
        q = session.query(models.ActionDependency).filter_by(
            depended=action_id)
        return [d.dependent for d in q.all()]


@oslo_db_api.wrap_db_retry(max_retries=3, retry_on_deadlock=True,
                           retry_interval=0.5, inc_retry_interval=True)
def dependency_add(context, depended, dependent):
    if isinstance(depended, list) and isinstance(dependent, list):
        raise exception.NotSupport(
            _('Multiple dependencies between lists not support'))

    with session_for_write() as session:
        if isinstance(depended, list):   # e.g. D depends on A,B,C
            for d in depended:
                r = models.ActionDependency(depended=d, dependent=dependent)
                session.add(r)

            query = session.query(models.Action).filter_by(id=dependent)
            query.update({'status': consts.ACTION_WAITING,
                          'status_reason': _('Waiting for depended actions.')},
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

        q = session.query(models.Action).filter(
            models.Action.id.in_(dependents))
        q.update({'status': consts.ACTION_WAITING,
                  'status_reason': _('Waiting for depended actions.')},
                 synchronize_session='fetch')


def action_mark_succeeded(context, action_id, timestamp):
    with session_for_write() as session:

        query = session.query(models.Action).filter_by(id=action_id)
        values = {
            'owner': None,
            'status': consts.ACTION_SUCCEEDED,
            'status_reason': _('Action completed successfully.'),
            'end_time': timestamp,
        }
        query.update(values, synchronize_session=False)

        subquery = session.query(models.ActionDependency).filter_by(
            depended=action_id)
        subquery.delete(synchronize_session='fetch')


def _mark_failed(session, action_id, timestamp, reason=None):
    # mark myself as failed
    query = session.query(models.Action).filter_by(id=action_id)
    values = {
        'owner': None,
        'status': consts.ACTION_FAILED,
        'status_reason': (six.text_type(reason) if reason else
                          _('Action execution failed')),
        'end_time': timestamp,
    }
    query.update(values, synchronize_session=False)

    query = session.query(models.ActionDependency)
    query = query.filter_by(depended=action_id)
    dependents = [d.dependent for d in query.all()]
    query.delete(synchronize_session=False)

    for d in dependents:
        _mark_failed(session, d, timestamp)


def action_mark_failed(context, action_id, timestamp, reason=None):
    with session_for_write() as session:
        _mark_failed(session, action_id, timestamp, reason)


def _mark_cancelled(session, action_id, timestamp, reason=None):
    query = session.query(models.Action).filter_by(id=action_id)
    values = {
        'owner': None,
        'status': consts.ACTION_CANCELLED,
        'status_reason': (six.text_type(reason) if reason else
                          _('Action execution failed')),
        'end_time': timestamp,
    }
    query.update(values, synchronize_session=False)

    query = session.query(models.ActionDependency)
    query = query.filter_by(depended=action_id)
    dependents = [d.dependent for d in query.all()]
    query.delete(synchronize_session=False)

    for d in dependents:
        _mark_cancelled(session, d, timestamp)


def action_mark_cancelled(context, action_id, timestamp, reason=None):
    with session_for_write() as session:
        _mark_cancelled(session, action_id, timestamp, reason)


@oslo_db_api.wrap_db_retry(max_retries=3, retry_on_deadlock=True,
                           retry_interval=0.5, inc_retry_interval=True)
def action_acquire(context, action_id, owner, timestamp):
    with session_for_write() as session:
        action = session.query(models.Action).with_for_update().\
            get(action_id)
        if not action:
            return None

        if action.owner and action.owner != owner:
            return None

        if action.status != consts.ACTION_READY:
            msg = _('The action is not in an executable status: '
                    '%s') % action.status
            LOG.warning(msg)
            return None
        action.owner = owner
        action.start_time = timestamp
        action.status = consts.ACTION_RUNNING
        action.status_reason = _('The action is being processed.')
        action.save(session)

        return action


@oslo_db_api.wrap_db_retry(max_retries=3, retry_on_deadlock=True,
                           retry_interval=0.5, inc_retry_interval=True)
def action_acquire_1st_ready(context, owner, timestamp):
    with session_for_write() as session:
        action = session.query(models.Action).\
            filter_by(status=consts.ACTION_READY).\
            filter_by(owner=None).\
            with_for_update().first()

        if action:
            action.owner = owner
            action.start_time = timestamp
            action.status = consts.ACTION_RUNNING
            action.status_reason = _('The action is being processed.')
            action.save(session)

            return action


def action_abandon(context, action_id):
    '''Abandon an action for other workers to execute again.

    This API is always called with the action locked by the current
    worker. There is no chance the action is gone or stolen by others.
    '''
    with session_for_write() as session:
        action = session.query(models.Action).get(action_id)

        action.owner = None
        action.start_time = None
        action.status = consts.ACTION_READY
        action.status_reason = _('The action was abandoned.')
        action.save(session)
        return action


def action_lock_check(context, action_id, owner=None):
    action = model_query(context, models.Action).get(action_id)
    if not action:
        raise exception.ActionNotFound(action=action_id)

    if owner:
        return owner if owner == action.owner else action.owner
    else:
        return action.owner if action.owner else None


def action_signal(context, action_id, value):
    with session_for_write() as session:
        action = session.query(models.Action).get(action_id)
        if not action:
            return

        action.control = value
        action.save(session)


def action_signal_query(context, action_id):
    action = model_query(context, models.Action).get(action_id)
    if not action:
        return None

    return action.control


def action_delete(context, action_id, force=False):
    with session_for_write() as session:
        action = session.query(models.Action).get(action_id)
        if not action:
            return
        if ((action.status == 'WAITING') or (action.status == 'RUNNING') or
                (action.status == 'SUSPENDED')):

            raise exception.ResourceBusyError(resource_type='action',
                                              resource_id=action_id)
        session.delete(action)


# Receivers
def receiver_create(context, values):
    with session_for_write() as session:
        receiver = models.Receiver()
        receiver.update(values)
        session.add(receiver)
        return receiver


def receiver_get(context, receiver_id, project_safe=True):
    receiver = model_query(context, models.Receiver).get(receiver_id)
    if not receiver:
        return None

    if not context.is_admin and project_safe:
        if context.project != receiver.project:
            return None

    return receiver


def receiver_get_all(context, limit=None, marker=None, filters=None, sort=None,
                     project_safe=True):
    query = model_query(context, models.Receiver)
    if not context.is_admin and project_safe:
        query = query.filter_by(project=context.project)

    if filters:
        query = utils.exact_filter(query, models.Receiver, filters)

    keys, dirs = utils.get_sort_params(sort, consts.RECEIVER_NAME)
    if marker:
        marker = model_query(context, models.Receiver).get(marker)
    return sa_utils.paginate_query(query, models.Receiver, limit, keys,
                                   marker=marker, sort_dirs=dirs).all()


def receiver_get_by_name(context, name, project_safe=True):
    return query_by_name(context, models.Receiver, name,
                         project_safe=project_safe)


def receiver_get_by_short_id(context, short_id, project_safe=True):
    return query_by_short_id(context, models.Receiver, short_id,
                             project_safe=project_safe)


def receiver_delete(context, receiver_id):
    with session_for_write() as session:
        receiver = session.query(models.Receiver).get(receiver_id)
        if not receiver:
            return
        session.delete(receiver)


def service_create(context, service_id, host=None, binary=None,
                   topic=None):
    with session_for_write() as session:
        time_now = timeutils.utcnow(True)
        svc = models.Service(id=service_id, host=host, binary=binary,
                             topic=topic, created_at=time_now,
                             updated_at=time_now)
        session.add(svc)
        return svc


def service_update(context, service_id, values=None):
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


def service_delete(context, service_id):
    with session_for_write() as session:
        session.query(models.Service).filter_by(
            id=service_id).delete(synchronize_session='fetch')


def service_get(context, service_id):
    return model_query(context, models.Service).get(service_id)


def service_get_all(context):
    return model_query(context, models.Service).all()


# HealthRegistry
def registry_claim(context, engine_id):
    with session_for_write() as session:
        q_eng = session.query(models.Service)
        svc_ids = [s.id for s in q_eng.all()]

        q_reg = session.query(models.HealthRegistry)
        q_reg = q_reg.filter(models.HealthRegistry.engine_id.notin_(svc_ids))
        q_reg.update({'engine_id': engine_id}, synchronize_session=False)
        result = q_reg.all()
        return result


def registry_delete(context, cluster_id):
    with session_for_write() as session:
        registry = session.query(models.HealthRegistry).filter_by(
            cluster_id=cluster_id).first()
        if registry is None:
            return
        session.delete(registry)


def registry_create(context, cluster_id, check_type, interval, params,
                    engine_id):
    with session_for_write() as session:
        registry = models.HealthRegistry()
        registry.cluster_id = cluster_id
        registry.check_type = check_type
        registry.interval = interval
        registry.params = params
        registry.engine_id = engine_id
        session.add(registry)
        return registry


# Utils
def db_sync(engine, version=None):
    """Migrate the database to `version` or the most recent version."""
    return migration.db_sync(engine, version=version)


def db_version(engine):
    """Display the current database version."""
    return migration.db_version(engine)
