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
Implementation of SQLAlchemy backend.
'''

import six
import sys

from oslo_config import cfg
from oslo_db.sqlalchemy import session as db_session
from oslo_db.sqlalchemy import utils
from oslo_log import log as logging
from oslo_utils import timeutils

from senlin.common import consts
from senlin.common import exception
from senlin.common.i18n import _
from senlin.common import utils as common_utils
from senlin.db.sqlalchemy import filters as db_filters
from senlin.db.sqlalchemy import migration
from senlin.db.sqlalchemy import models

LOG = logging.getLogger(__name__)


CONF = cfg.CONF
CONF.import_opt('max_events_per_cluster', 'senlin.common.config')

_facade = None


def get_facade():
    global _facade

    if not _facade:
        _facade = db_session.EngineFacade.from_config(CONF)
    return _facade


def get_engine():
    return get_facade().get_engine()


def get_session():
    return get_facade().get_session()


def get_backend():
    """The backend is this module itself."""
    return sys.modules[__name__]


def _session(context):
    return (context and context.session) or get_session()


def model_query(context, *args):
    session = _session(context)
    query = session.query(*args)
    return query


def _get_sort_params(value, whitelist, default_key=None):
    """Parse a string into a list of sort_keys and a list of sort_dirs.

    :param value: A string that contains the sorting parameters.
    :param whitelist: A list of permitted sorting keys.
    :param default_key: An optional key set as the default sorting key.

    :return: A list of sorting keys and a list of sort_dirs.
    """
    keys, dirs = common_utils.parse_sort_param(value)
    if not keys:
        if default_key:
            return [default_key, 'id'], ['asc', 'asc']
        return ['id'], ['asc']

    for i in reversed(range(len(keys))):
        if keys[i] not in whitelist:
            keys.pop(i)
            dirs.pop(i)

    keys.append('id')
    dirs.append('asc')

    return keys, dirs


# TODO(Yanyan Hu): Set default value of project_safe to True
def query_by_short_id(context, model, short_id, project_safe=False):
    q = model_query(context, model)
    q = q.filter(model.id.like('%s%%' % short_id))

    if project_safe:
        q = q.filter_by(project=context.project)

    if q.count() == 1:
        return q.first()
    elif q.count() == 0:
        return None
    else:
        raise exception.MultipleChoices(arg=short_id)


# TODO(Yanyan Hu): Set default value of project_safe to True
def query_by_name(context, model, name, project_safe=False):
    q = model_query(context, model)
    q = q.filter_by(name=name)

    if project_safe:
        q = q.filter_by(project=context.project)

    if q.count() == 1:
        return q.first()
    elif q.count() == 0:
        return None
    else:
        raise exception.MultipleChoices(arg=name)


# Clusters
def cluster_create(context, values):
    cluster_ref = models.Cluster()
    cluster_ref.update(values)
    cluster_ref.save(_session(context))
    return cluster_ref


def cluster_get(context, cluster_id, project_safe=True):
    query = model_query(context, models.Cluster)
    cluster = query.get(cluster_id)

    if cluster is None:
        return None

    if project_safe and (cluster is not None):
        if context.project != cluster.project:
            return None
    return cluster


def cluster_get_by_name(context, name, project_safe=True):
    return query_by_name(context, models.Cluster, name,
                         project_safe=project_safe)


def cluster_get_by_short_id(context, short_id, project_safe=True):
    return query_by_short_id(context, models.Cluster, short_id,
                             project_safe=project_safe)


def _query_cluster_get_all(context, project_safe=True, show_nested=False):
    query = model_query(context, models.Cluster)

    if not show_nested:
        query = query.filter_by(parent=None)

    if project_safe:
        query = query.filter_by(project=context.project)
    return query


def cluster_get_all(context, limit=None, marker=None, sort=None, filters=None,
                    project_safe=True, show_nested=False):
    query = _query_cluster_get_all(context, project_safe=project_safe,
                                   show_nested=show_nested)
    if filters:
        query = db_filters.exact_filter(query, models.Cluster, filters)

    keys, dirs = _get_sort_params(sort, consts.CLUSTER_SORT_KEYS, 'init_at')
    if marker:
        marker = model_query(context, models.Cluster).get(marker)

    return utils.paginate_query(query, models.Cluster, limit, keys,
                                marker=marker, sort_dirs=dirs).all()


def cluster_next_index(context, cluster_id):
    session = _session(context)
    cluster = session.query(models.Cluster).get(cluster_id)
    if cluster is None:
        return 0

    next_index = cluster.next_index
    cluster.next_index += 1
    cluster.save(session)
    return next_index


def cluster_count_all(context, filters=None, project_safe=True,
                      show_nested=False):
    query = _query_cluster_get_all(context, project_safe=project_safe,
                                   show_nested=show_nested)
    query = db_filters.exact_filter(query, models.Cluster, filters)
    return query.count()


def cluster_update(context, cluster_id, values):
    cluster = cluster_get(context, cluster_id)

    if not cluster:
        raise exception.ClusterNotFound(cluster=cluster_id)

    cluster.update(values)
    cluster.save(_session(context))


def cluster_delete(context, cluster_id):
    session = _session(context)

    cluster = session.query(models.Cluster).get(cluster_id)
    if cluster is None:
        raise exception.ClusterNotFound(cluster=cluster_id)

    session.begin()
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
    session.commit()
    session.flush()


# Nodes
def node_create(context, values):
    # This operation is always called with cluster and node locked
    session = _session(context)
    node = models.Node()
    node.update(values)
    node.save(session)
    return node


def node_get(context, node_id, project_safe=True):
    node = model_query(context, models.Node).get(node_id)
    if not node:
        return None

    if project_safe and context.project != node.project:
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

    if project_safe:
        query = query.filter_by(project=context.project)

    return query


def node_get_all(context, cluster_id=None, limit=None, marker=None, sort=None,
                 filters=None, project_safe=True):
    query = _query_node_get_all(context, project_safe=project_safe,
                                cluster_id=cluster_id)

    if filters:
        query = db_filters.exact_filter(query, models.Node, filters)

    keys, dirs = _get_sort_params(sort, consts.NODE_SORT_KEYS, 'init_at')
    if marker:
        marker = model_query(context, models.Node).get(marker)
    return utils.paginate_query(query, models.Node, limit, keys,
                                marker=marker, sort_dirs=dirs).all()


def node_get_all_by_cluster(context, cluster_id, project_safe=True):
    return _query_node_get_all(context, cluster_id=cluster_id,
                               project_safe=project_safe).all()


def node_update(context, node_id, values):
    '''Update a node with new property values.

    :param node_id: ID of the node to be updated.
    :param values: A dictionary of values to be updated on the node.
    :raises ClusterNotFound: The specified node does not exist in database.
    '''
    session = _session(context)
    session.begin()

    node = session.query(models.Node).get(node_id)
    if not node:
        session.rollback()
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
    session.commit()


def node_migrate(context, node_id, to_cluster, timestamp, role=None):
    session = _session(context)
    session.begin()

    node = session.query(models.Node).get(node_id)
    from_cluster = node.cluster_id
    if from_cluster:
        node.index = -1
    if to_cluster:
        cluster2 = session.query(models.Cluster).get(to_cluster)
        index = cluster2.next_index
        cluster2.next_index += 1
        node.index = index
    node.cluster_id = to_cluster if to_cluster else ''
    node.updated_at = timestamp
    node.role = role
    session.commit()
    return node


def node_delete(context, node_id, force=False):
    session = _session(context)
    node = session.query(models.Node).get(node_id)
    if not node:
        # Note: this is okay, because the node may have already gone
        return

    session.begin()
    session.delete(node)
    session.commit()
    session.flush()


# Locks
def cluster_lock_acquire(cluster_id, action_id, scope):
    '''Acquire lock on a cluster.

    :param cluster_id: ID of the cluster.
    :param action_id: ID of the action that attempts to lock the cluster.
    :param scope: +1 means a node-level operation lock; -1 indicates
                  a cluster-level lock.
    :return: A list of action IDs that currently works on the cluster.
    '''
    session = get_session()
    session.begin()
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

    session.commit()
    return lock.action_ids


def cluster_lock_release(cluster_id, action_id, scope):
    '''Release lock on a cluster.

    :param cluster_id: ID of the cluster.
    :param action_id: ID of the action that attempts to release the cluster.
    :param scope: +1 means a node-level operation lock; -1 indicates
                  a cluster-level lock.
    :return: True indicates successful release, False indicates failure.
    '''
    session = get_session()
    session.begin()
    lock = session.query(models.ClusterLock).get(cluster_id)
    if lock is None:
        session.commit()
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

    session.commit()
    return success


def cluster_lock_steal(cluster_id, action_id):
    session = get_session()
    session.begin()
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

    session.commit()
    return lock.action_ids


def node_lock_acquire(node_id, action_id):
    session = get_session()
    session.begin()

    lock = session.query(models.NodeLock).get(node_id)
    if lock is None:
        lock = models.NodeLock(node_id=node_id, action_id=action_id)
        session.add(lock)
    session.commit()

    return lock.action_id


def node_lock_release(node_id, action_id):
    session = get_session()
    session.begin()

    success = False
    lock = session.query(models.NodeLock).get(node_id)
    if lock is not None and lock.action_id == action_id:
        session.delete(lock)
        success = True

    session.commit()
    return success


def node_lock_steal(node_id, action_id):
    session = get_session()
    session.begin()
    lock = session.query(models.NodeLock).get(node_id)
    if lock is not None:
        lock.action_id = action_id
        lock.save(session)
    else:
        lock = models.NodeLock(node_id=node_id, action_id=action_id)
        session.add(lock)
    session.commit()
    return lock.action_id


# Policies
def policy_create(context, values):
    policy = models.Policy()
    policy.update(values)
    policy.save(_session(context))
    return policy


def policy_get(context, policy_id, project_safe=True):
    policy = model_query(context, models.Policy)
    policy = policy.filter_by(id=policy_id).first()

    if policy is not None:
        if project_safe and context.project != policy.project:
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

    if project_safe:
        query = query.filter_by(project=context.project)

    if filters:
        query = db_filters.exact_filter(query, models.Policy, filters)

    keys, dirs = _get_sort_params(sort, consts.POLICY_SORT_KEYS, 'created_at')
    if marker:
        marker = model_query(context, models.Policy).get(marker)
    return utils.paginate_query(query, models.Policy, limit, keys,
                                marker=marker, sort_dirs=dirs).all()


def policy_update(context, policy_id, values):
    policy = model_query(context, models.Policy).get(policy_id)
    if not policy:
        raise exception.PolicyNotFound(policy=policy_id)

    policy.update(values)
    policy.save(_session(context))
    return policy


def policy_delete(context, policy_id, force=False):
    session = _session(context)
    policy = session.query(models.Policy).get(policy_id)

    if not policy:
        return

    bindings = session.query(models.ClusterPolicies).filter_by(
        policy_id=policy_id)
    if bindings.count():
        raise exception.ResourceBusyError(resource_type='policy',
                                          resource_id=policy_id)
    session.begin()
    session.delete(policy)
    session.commit()
    session.flush()


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
        query = db_filters.exact_filter(query, models.ClusterPolicies, filters)

    keys, dirs = _get_sort_params(sort, consts.CLUSTER_POLICY_SORT_KEYS)
    return utils.paginate_query(query, models.ClusterPolicies, None, keys,
                                sort_dirs=dirs).all()


def cluster_policy_get_by_type(context, cluster_id, policy_type, filters=None):

    query = model_query(context, models.ClusterPolicies)
    query = query.filter_by(cluster_id=cluster_id)

    if filters:
        query = db_filters.exact_filter(query, models.ClusterPolicies, filters)

    query = query.join(models.Policy).filter(models.Policy.type == policy_type)

    return query.all()


def cluster_policy_attach(context, cluster_id, policy_id, values):
    binding = models.ClusterPolicies()
    binding.cluster_id = cluster_id
    binding.policy_id = policy_id
    binding.update(values)
    binding.save(_session(context))
    return binding


def cluster_policy_detach(context, cluster_id, policy_id):
    session = _session(context)
    query = session.query(models.ClusterPolicies)
    bindings = query.filter_by(cluster_id=cluster_id,
                               policy_id=policy_id).first()
    if bindings is None:
        return
    session.begin()
    session.delete(bindings)
    session.commit()
    session.flush()


def cluster_policy_update(context, cluster_id, policy_id, values):
    session = _session(context)
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
    profile = models.Profile()
    profile.update(values)
    profile.save(_session(context))
    return profile


def profile_get(context, profile_id, project_safe=True):
    query = model_query(context, models.Profile)
    profile = query.filter_by(id=profile_id).first()

    if project_safe and profile is not None:
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

    if project_safe:
        query = query.filter_by(project=context.project)

    if filters:
        query = db_filters.exact_filter(query, models.Profile, filters)

    keys, dirs = _get_sort_params(sort, consts.PROFILE_SORT_KEYS, 'created_at')
    if marker:
        marker = model_query(context, models.Profile).get(marker)
    return utils.paginate_query(query, models.Profile, limit, keys,
                                marker=marker, sort_dirs=dirs).all()


def profile_update(context, profile_id, values):
    profile = model_query(context, models.Profile).get(profile_id)
    if not profile:
        raise exception.ProfileNotFound(profile=profile_id)

    profile.update(values)
    profile.save(_session(context))
    return profile


def profile_delete(context, profile_id, force=False):
    session = _session(context)
    profile = session.query(models.Profile).get(profile_id)
    if profile is None:
        return

    # used by any clusters?
    clusters = session.query(models.Cluster).filter_by(profile_id=profile_id)
    if clusters.count() > 0:
        raise exception.ResourceBusyError(resource_type='profile',
                                          resource_id=profile_id)

    # used by any nodes?
    nodes = session.query(models.Node).filter_by(profile_id=profile_id)
    if nodes.count() > 0:
        raise exception.ResourceBusyError(resource_type='profile',
                                          resource_id=profile_id)

    session.begin()
    session.delete(profile)
    session.commit()
    session.flush()


# Credentials
def cred_create(context, values):
    cred = models.Credential()
    cred.update(values)
    cred.save(_session(context))
    return cred


def cred_get(context, user, project):
    return model_query(context, models.Credential).get((user, project))


def cred_update(context, user, project, values):
    cred = model_query(context, models.Credential).get((user, project))
    cred.update(values)
    cred.save(_session(context))
    return cred


def cred_delete(context, user, project):
    session = _session(context)
    cred = session.query(models.Credential).get((user, project))
    if cred is None:
        return None

    session.begin()
    session.delete(cred)
    session.commit()
    session.flush()


# Events
def _delete_event_rows(context, cluster_id, limit):
    # MySQL does not support LIMIT in subqueries,
    # sqlite does not support JOIN in DELETE.
    # So we must manually supply the IN() values.
    # pgsql SHOULD work with the pure DELETE/JOIN below but that must be
    # confirmed via integration tests.
    query = event_count_by_cluster(context, cluster_id)
    session = _session(context)
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
    event = models.Event()
    event.update(values)
    event.save(_session(context))
    return event


def event_get(context, event_id, project_safe=True):
    event = model_query(context, models.Event).get(event_id)
    if project_safe and event is not None:
        if event.project != context.project:
            return None

    return event


def event_get_by_short_id(context, short_id, project_safe=True):
    return query_by_short_id(context, models.Event, short_id,
                             project_safe=project_safe)


def _event_filter_paginate_query(context, query, filters=None,
                                 limit=None, marker=None, sort=None):
    if filters:
        query = db_filters.exact_filter(query, models.Event, filters)

    keys, dirs = _get_sort_params(sort, consts.EVENT_SORT_KEYS, 'timestamp')
    if marker:
        marker = model_query(context, models.Event).get(marker)
    return utils.paginate_query(query, models.Event, limit, keys,
                                marker=marker, sort_dirs=dirs).all()


def event_get_all(context, limit=None, marker=None, sort=None, filters=None,
                  project_safe=True):
    query = model_query(context, models.Event)
    if project_safe:
        query = query.filter_by(project=context.project)

    return _event_filter_paginate_query(context, query, filters=filters,
                                        limit=limit, marker=marker, sort=sort)


def event_count_by_cluster(context, cluster_id, project_safe=True):
    query = model_query(context, models.Event)

    if project_safe:
        query = query.filter_by(project=context.project)
    count = query.filter_by(cluster_id=cluster_id).count()

    return count


def event_get_all_by_cluster(context, cluster_id, limit=None, marker=None,
                             sort=None, filters=None, project_safe=True):
    query = model_query(context, models.Event)
    query = query.filter_by(cluster_id=cluster_id)

    if project_safe:
        query = query.filter_by(project=context.project)

    return _event_filter_paginate_query(context, query, filters=filters,
                                        limit=limit, marker=marker, sort=sort)


# Actions
def action_create(context, values):
    action = models.Action()
    action.update(values)
    action.save(_session(context))
    return action


def action_update(context, action_id, values):
    session = get_session()
    action = session.query(models.Action).get(action_id)
    if not action:
        raise exception.ActionNotFound(action=action_id)

    action.update(values)
    action.save(session)


def action_get(context, action_id, refresh=False):
    session = get_session()
    action = session.query(models.Action).get(action_id)
    if action is None:
        return None
    session.refresh(action)
    return action


def action_get_by_name(context, name):
    return query_by_name(context, models.Action, name)


def action_get_by_short_id(context, short_id):
    return query_by_short_id(context, models.Action, short_id)


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
        query = db_filters.exact_filter(query, models.Action, filters)

    keys, dirs = _get_sort_params(sort, consts.ACTION_SORT_KEYS, 'created_at')
    if marker:
        marker = model_query(context, models.Action).get(marker)
    return utils.paginate_query(query, models.Action, limit, keys,
                                marker=marker, sort_dirs=dirs).all()


def dependency_get_depended(context, action_id):
    session = get_session()
    q = session.query(models.ActionDependency).filter_by(dependent=action_id)
    return [d.depended for d in q.all()]


def dependency_get_dependents(context, action_id):
    session = get_session()
    q = session.query(models.ActionDependency).filter_by(depended=action_id)
    return [d.dependent for d in q.all()]


def dependency_add(context, depended, dependent):
    if isinstance(depended, list) and isinstance(dependent, list):
        raise exception.NotSupport(
            _('Multiple dependencies between lists not support'))

    session = get_session()

    if isinstance(depended, list):   # e.g. D depends on A,B,C
        session.begin()
        for d in depended:
            r = models.ActionDependency(depended=d, dependent=dependent)
            session.add(r)

        query = session.query(models.Action).filter_by(id=dependent)
        query.update({'status': consts.ACTION_WAITING,
                      'status_reason': _('Waiting for depended actions.')},
                     synchronize_session=False)
        session.commit()
        return

    # Only dependent can be a list now, convert it to a list if it
    # is not a list
    if not isinstance(dependent, list):  # e.g. B,C,D depend on A
        dependents = [dependent]
    else:
        dependents = dependent

    session.begin()
    for d in dependents:
        r = models.ActionDependency(depended=depended, dependent=d)
        session.add(r)

    q = session.query(models.Action).filter(models.Action.id.in_(dependents))
    q.update({'status': consts.ACTION_WAITING,
              'status_reason': _('Waiting for depended actions.')},
             synchronize_session=False)
    session.commit()


def action_mark_succeeded(context, action_id, timestamp):
    session = get_session()
    session.begin()

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
    dependents = [d.dependent for d in subquery.all()]
    subquery.delete(synchronize_session=False)

    for d in dependents:
        # set action to ready if no depended action hanging
        q = session.query(models.ActionDependency).filter_by(dependent=d)
        count = q.count()
        if count == 0:
            query = session.query(models.Action).filter_by(id=d)
            values = {
                'status': consts.ACTION_READY,
                'status_reason': _('All depended actions completed.')
            }
            query.update(values, synchronize_session=False)

    session.commit()
    session.expire_all()


def _mark_failed(session, action_id, timestamp, reason=None):
    query = session.query(models.Action).filter_by(id=action_id)
    values = {
        'owner': None,
        'status': consts.ACTION_FAILED,
        'status_reason': (six.text_type(reason) if reason else
                          _('Action execution failed')),
        'end_time': timestamp,
    }
    query.update(values, synchronize_session=False)

    dep = session.query(models.ActionDependency)
    dependents = dep.filter_by(depended=action_id).all()
    for d in dependents:
        _mark_failed(session, d.dependent, timestamp)


def action_mark_failed(context, action_id, timestamp, reason=None):
    session = get_session()
    session.begin()
    _mark_failed(session, action_id, timestamp, reason)
    session.commit()


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

    dep = session.query(models.ActionDependency)
    dependents = dep.filter_by(depended=action_id).all()
    for d in dependents:
        _mark_cancelled(session, d.dependent, timestamp)


def action_mark_cancelled(context, action_id, timestamp, reason=None):
    session = get_session()
    session.begin()
    _mark_cancelled(session, action_id, timestamp, reason)
    session.commit()


def action_acquire(context, action_id, owner, timestamp):
    session = _session(context)
    with session.begin():
        action = session.query(models.Action).get(action_id)
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

        return action


def action_acquire_1st_ready(context, owner, timestamp):
    session = _session(context)

    with session.begin():
        action = session.query(models.Action).\
            filter_by(status=consts.ACTION_READY).\
            filter_by(owner=None).first()

        if action:
            action.owner = owner
            action.start_time = timestamp
            action.status = consts.ACTION_RUNNING
            action.status_reason = _('The action is being processed.')

            return action


def action_abandon(context, action_id):
    '''Abandon an action for other workers to execute again.

    This API is always called with the action locked by the current
    worker. There is no chance the action is gone or stolen by others.
    '''

    query = model_query(context, models.Action)
    action = query.get(action_id)

    action.owner = None
    action.start_time = None
    action.status = consts.ACTION_READY
    action.status_reason = _('The action was abandoned.')
    action.save(query.session)
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
    query = model_query(context, models.Action)
    action = query.get(action_id)
    if not action:
        return

    action.control = value
    action.save(query.session)


def action_signal_query(context, action_id):
    action = model_query(context, models.Action).get(action_id)
    if not action:
        return None

    return action.control


def action_delete(context, action_id, force=False):
    session = _session(context)
    action = session.query(models.Action).get(action_id)
    if not action:
        return
    if ((action.status == 'WAITING') or (action.status == 'RUNNING') or
            (action.status == 'SUSPENDED')):

        raise exception.ResourceBusyError(resource_type='action',
                                          resource_id=action_id)
    session.begin()
    session.delete(action)
    session.commit()
    session.flush()


# Receivers
def receiver_create(context, values):
    receiver = models.Receiver()
    receiver.update(values)
    receiver.save(_session(context))
    return receiver


def receiver_get(context, receiver_id, project_safe=True):
    receiver = model_query(context, models.Receiver).get(receiver_id)
    if not receiver:
        return None

    if project_safe and context.project != receiver.project:
        return None

    return receiver


def receiver_get_all(context, limit=None, marker=None, filters=None, sort=None,
                     project_safe=True):
    query = model_query(context, models.Receiver)
    if project_safe:
        query = query.filter_by(project=context.project)

    if filters:
        query = db_filters.exact_filter(query, models.Receiver, filters)

    keys, dirs = _get_sort_params(sort, consts.RECEIVER_SORT_KEYS, 'name')
    if marker:
        marker = model_query(context, models.Receiver).get(marker)
    return utils.paginate_query(query, models.Receiver, limit, keys,
                                marker=marker, sort_dirs=dirs).all()


def receiver_get_by_name(context, name, project_safe=True):
    return query_by_name(context, models.Receiver, name,
                         project_safe=project_safe)


def receiver_get_by_short_id(context, short_id, project_safe=True):
    return query_by_short_id(context, models.Receiver, short_id,
                             project_safe=project_safe)


def receiver_delete(context, receiver_id):
    session = _session(context)
    receiver = session.query(models.Receiver).get(receiver_id)
    if not receiver:
        return

    session.begin()
    session.delete(receiver)
    session.commit()
    session.flush()


def service_create(service_id=None, host=None, binary=None,
                   topic=None):
    session = get_session()
    session.begin()
    time_now = timeutils.utcnow()
    svc = models.Service(id=service_id, host=host, binary=binary,
                         topic=topic, created_at=time_now,
                         updated_at=time_now)
    session.add(svc)
    session.commit()
    return svc


def service_update(service_id, values=None):
    if values is None:
        values = {}
    session = get_session()
    service = service_get(service_id)
    values.update({'updated_at': timeutils.utcnow()})
    service.update(values)
    service.save(session)
    return service


def service_delete(service_id):
    session = get_session()
    svc = session.query(models.Service).get(service_id)
    if not svc:
        return None
    session.begin()
    session.delete(svc)
    session.commit()


def service_get(service_id):
    session = get_session()
    svc = session.query(models.Service).get(service_id)
    return svc


def service_get_all():
    session = get_session()
    svcs = session.query(models.Service).all()
    return svcs


# Utils
def db_sync(engine, version=None):
    """Migrate the database to `version` or the most recent version."""
    return migration.db_sync(engine, version=version)


def db_version(engine):
    """Display the current database version."""
    return migration.db_version(engine)
