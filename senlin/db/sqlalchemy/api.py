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

from sqlalchemy.orm import session as orm_session

from senlin.common import consts
from senlin.common import exception
from senlin.common.i18n import _
from senlin.db.sqlalchemy import filters as db_filters
from senlin.db.sqlalchemy import migration
from senlin.db.sqlalchemy import models

LOG = logging.getLogger(__name__)


CONF = cfg.CONF
CONF.import_opt('max_events_per_cluster', 'senlin.common.config')

# Action status definitions:
#  ACTION_INIT:      Not ready to be executed because fields are being
#                    modified, or dependency with other actions are being
#                    analyzed.
#  ACTION_READY:     Initialized and ready to be executed by a worker.
#  ACTION_RUNNING:   Being executed by a worker thread.
#  ACTION_SUCCEEDED: Completed with success.
#  ACTION_FAILED:    Completed with failure.
#  ACTION_CANCELLED: Action cancelled because worker thread was cancelled.
ACTION_STATUSES = (
    ACTION_INIT, ACTION_WAITING, ACTION_READY, ACTION_RUNNING,
    ACTION_SUCCEEDED, ACTION_FAILED, ACTION_CANCELED
) = (
    'INIT', 'WAITING', 'READY', 'RUNNING',
    'SUCCEEDED', 'FAILED', 'CANCELLED',
)

_facade = None


def get_facade():
    global _facade

    if not _facade:
        _facade = db_session.EngineFacade.from_config(CONF)
    return _facade

get_engine = lambda: get_facade().get_engine()
get_session = lambda: get_facade().get_session()


def get_backend():
    """The backend is this module itself."""
    return sys.modules[__name__]


def model_query(context, *args):
    session = _session(context)
    query = session.query(*args)
    return query


def _get_sort_keys(sort_keys, mapping):
    '''Returns an array containing only whitelisted keys

    :param sort_keys: an array of strings
    :param mapping: a mapping from keys to DB column names
    :returns: filtered list of sort keys
    '''
    if isinstance(sort_keys, six.string_types):
        sort_keys = [sort_keys]
    return [mapping[key] for key in sort_keys or [] if key in mapping]


def _paginate_query(context, query, model, limit=None, marker=None,
                    sort_keys=None, sort_dir=None, default_sort_keys=None):
    if not sort_keys:
        sort_keys = default_sort_keys or []
        if not sort_dir:
            sort_dir = 'asc'

    # This assures the order of the clusters will always be the same
    # even for sort_key values that are not unique in the database
    sort_keys = sort_keys + ['id']

    model_marker = None
    if marker:
        model_marker = model_query(context, model).get(marker)
    try:
        query = utils.paginate_query(query, model, limit, sort_keys,
                                     model_marker, sort_dir)
    except utils.InvalidSortKey:
        raise exception.InvalidParameter(name='sort_keys', value=sort_keys)
    return query


def soft_delete_aware_query(context, *args, **kwargs):
    """Object query helper that accounts for the `show_deleted` field.

    :param show_deleted: if True, overrides context's show_deleted field.
    """

    query = model_query(context, *args)
    show_deleted = kwargs.get('show_deleted') or context.show_deleted

    if (not show_deleted) or show_deleted in ('False', 'false', 'no', 'No'):
        query = query.filter_by(deleted_time=None)
    return query


# TODO(Yanyan Hu): Set default value of project_safe to True
def query_by_short_id(context, model, short_id, project_safe=False,
                      show_deleted=False):
    q = soft_delete_aware_query(context, model, show_deleted=show_deleted)
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
def query_by_name(context, model, name, project_safe=False,
                  show_deleted=False):
    q = soft_delete_aware_query(context, model, show_deleted=show_deleted)
    q = q.filter_by(name=name)

    if project_safe:
        q = q.filter_by(project=context.project)

    if q.count() == 1:
        return q.first()
    elif q.count() == 0:
        return None
    else:
        raise exception.MultipleChoices(arg=name)


def _session(context):
    return (context and context.session) or get_session()


# Clusters
def cluster_create(context, values):
    cluster_ref = models.Cluster()
    cluster_ref.update(values)
    cluster_ref.save(_session(context))
    return cluster_ref


def cluster_get(context, cluster_id, show_deleted=False, project_safe=True):
    query = model_query(context, models.Cluster)
    cluster = query.get(cluster_id)

    deleted_ok = show_deleted or context.show_deleted
    if cluster is None or cluster.deleted_time is not None and not deleted_ok:
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


def _query_cluster_get_all(context, project_safe=True, show_deleted=False,
                           show_nested=False):
    query = soft_delete_aware_query(context, models.Cluster,
                                    show_deleted=show_deleted)

    if not show_nested:
        query = query.filter_by(parent=None)

    if project_safe:
        query = query.filter_by(project=context.project)
    return query


def cluster_get_all(context, limit=None, marker=None, sort_keys=None,
                    sort_dir=None, filters=None, project_safe=True,
                    show_deleted=False, show_nested=False):
    query = _query_cluster_get_all(context, project_safe=project_safe,
                                   show_deleted=show_deleted,
                                   show_nested=show_nested)
    if filters is None:
        filters = {}

    sort_key_map = {
        consts.CLUSTER_NAME: models.Cluster.name.key,
        consts.CLUSTER_STATUS: models.Cluster.status.key,
        consts.CLUSTER_CREATED_TIME: models.Cluster.created_time.key,
        consts.CLUSTER_UPDATED_TIME: models.Cluster.updated_time.key,
    }
    keys = _get_sort_keys(sort_keys, sort_key_map)

    query = db_filters.exact_filter(query, models.Cluster, filters)
    return _paginate_query(context, query, models.Cluster, limit=limit,
                           marker=marker, sort_keys=keys, sort_dir=sort_dir,
                           default_sort_keys=['init_time']).all()


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
                      show_deleted=False, show_nested=False):
    query = _query_cluster_get_all(context, project_safe=project_safe,
                                   show_deleted=show_deleted,
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
    if cluster is None or cluster.deleted_time is not None:
        raise exception.ClusterNotFound(cluster=cluster_id)

    query = session.query(models.Node).filter_by(cluster_id=cluster_id)
    nodes = query.all()

    if len(nodes) != 0:
        for node in nodes:
            session.delete(node)

    # Delete all related cluster_policies records
    for cp in cluster.policies:
        session.delete(cp)

    # Do soft delete and set the status
    cluster.update_and_save({'deleted_time': timeutils.utcnow(),
                             'status': 'DELETED',
                             'status_reason': 'Cluster deletion succeeded'
                             }, session=session)


# Nodes
def node_create(context, values):
    # This operation is always called with cluster and node locked
    session = _session(context)
    node = models.Node()
    node.update(values)
    node.save(session)
    return node


def node_get(context, node_id, show_deleted=False, project_safe=True):
    node = model_query(context, models.Node).get(node_id)
    if not node:
        return None

    if not show_deleted and node.deleted_time is not None:
        return None

    if project_safe:
        if context.project != node.project:
            return None

    return node


def node_get_by_name(context, name, show_deleted=False, project_safe=True):
    return query_by_name(context, models.Node, name,
                         show_deleted=show_deleted,
                         project_safe=project_safe)


def node_get_by_short_id(context, short_id, show_deleted=False,
                         project_safe=True):
    return query_by_short_id(context, models.Node, short_id,
                             show_deleted=show_deleted,
                             project_safe=project_safe)


def _query_node_get_all(context, project_safe=True, show_deleted=False,
                        cluster_id=None):
    query = soft_delete_aware_query(context, models.Node,
                                    show_deleted=show_deleted)

    if cluster_id:
        query = query.filter_by(cluster_id=cluster_id)

    if project_safe:
        query = query.filter_by(project=context.project)

    return query


def node_get_all(context, cluster_id=None, show_deleted=False,
                 limit=None, marker=None, sort_keys=None, sort_dir=None,
                 filters=None, project_safe=True):
    if cluster_id is None:
        query = _query_node_get_all(context, project_safe=project_safe,
                                    show_deleted=show_deleted)
    else:
        query = _query_node_get_all(context, project_safe=project_safe,
                                    show_deleted=show_deleted,
                                    cluster_id=cluster_id)

    if filters is None:
        filters = {}

    sort_key_map = {
        consts.NODE_INDEX: models.Node.index.key,
        consts.NODE_NAME: models.Node.name.key,
        consts.NODE_CREATED_TIME: models.Node.created_time.key,
        consts.NODE_UPDATED_TIME: models.Node.updated_time.key,
        consts.NODE_DELETED_TIME: models.Node.deleted_time.key,
        consts.NODE_STATUS: models.Node.status.key,
    }
    keys = _get_sort_keys(sort_keys, sort_key_map)
    query = db_filters.exact_filter(query, models.Node, filters)
    return _paginate_query(context, query, models.Node,
                           limit=limit, marker=marker,
                           sort_keys=keys, sort_dir=sort_dir,
                           default_sort_keys=['init_time']).all()


def node_get_all_by_cluster(context, cluster_id, show_deleted=False,
                            project_safe=True):
    if show_deleted:
        query = model_query(context,
                            models.Node).filter_by(cluster_id=cluster_id)
    else:
        query = model_query(context,
                            models.Node).filter_by(cluster_id=cluster_id,
                                                   deleted_time=None)

    if project_safe:
        query = query.filter_by(project=context.project)

    nodes = query.all()

    return nodes


def node_get_by_name_and_cluster(context, node_name, cluster_id,
                                 project_safe=True):
    query = model_query(context, models.Node).filter_by(name=node_name)

    if project_safe:
        query = query.filter_by(project=context.project)

    node = query.filter_by(cluster_id=cluster_id).first()
    return node


def node_get_by_physical_id(context, phy_id, project_safe=True):
    query = model_query(context, models.Node).filter_by(physical_id=phy_id)

    if project_safe:
        query = query.filter_by(project=context.project)

    return query.first()


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


def node_migrate(context, node_id, to_cluster, timestamp):
    session = _session(context)
    session.begin()

    node = session.query(models.Node).get(node_id)
    from_cluster = node.cluster_id
    if from_cluster is not None:
        node.index = -1
    if to_cluster is not None:
        cluster2 = session.query(models.Cluster).get(to_cluster)
        index = cluster2.next_index
        cluster2.next_index += 1
        node.index = index
    node.cluster_id = to_cluster
    node.updated_time = timestamp
    session.commit()
    return node


def node_delete(context, node_id, force=False):
    session = _session(context)
    node = session.query(models.Node).get(node_id)
    if not node:
        # Note: this is okay, because the node may have already gone
        return

    if node.cluster_id is not None:
        cluster = session.query(models.Cluster).get(node.cluster_id)
        cluster.save(session)

    node.update_and_save({'deleted_time': timeutils.utcnow(),
                          'status': 'DELETED',
                          'status_reason': 'Node deletion succeeded'},
                         session=session)
    session.flush()


# Triggers
def trigger_create(context, values):
    trigger = models.Trigger()
    trigger.update(values)
    trigger.save(_session(context))
    return trigger


def trigger_get(context, trigger_id, show_deleted=False):
    query = soft_delete_aware_query(context, models.Trigger,
                                    show_deleted=show_deleted)
    trigger = query.filter_by(id=trigger_id).first()
    return trigger


def trigger_get_by_name(context, name, show_deleted=False):
    return query_by_name(context, models.Trigger, name,
                         show_deleted=show_deleted)


def trigger_get_by_short_id(context, short_id, show_deleted=False):
    return query_by_short_id(context, models.Trigger, short_id,
                             show_deleted=show_deleted)


def trigger_get_all(context, limit=None, marker=None, sort_keys=None,
                    sort_dir=None, filters=None, project_safe=True,
                    show_deleted=False):
    query = soft_delete_aware_query(context, models.Trigger,
                                    show_deleted=show_deleted)
    if project_safe:
        query = query.filter_by(project=context.project)

    if filters is None:
        filters = {}

    sort_key_map = {
        consts.TRIGGER_NAME: models.Trigger.name.key,
        consts.TRIGGER_TYPE: models.Trigger.type.key,
        consts.TRIGGER_STATE: models.Trigger.state.key,
        consts.TRIGGER_SEVERITY: models.Trigger.severity.key,
        consts.TRIGGER_ENABLED: models.Trigger.enabled.key,
        consts.TRIGGER_CREATED_TIME: models.Trigger.created_time.key,
        consts.TRIGGER_UPDATED_TIME: models.Trigger.updated_time.key,
    }
    keys = _get_sort_keys(sort_keys, sort_key_map)

    query = db_filters.exact_filter(query, models.Trigger, filters)
    return _paginate_query(context, query, models.Trigger,
                           limit=limit, marker=marker,
                           sort_keys=keys, sort_dir=sort_dir,
                           default_sort_keys=['created_time']).all()


def trigger_update(context, trigger_id, values):
    trigger = model_query(context, models.Trigger).get(trigger_id)
    if not trigger:
        raise exception.TriggerNotFound(trigger=trigger_id)

    trigger.update(values)
    trigger.save(_session(context))
    return trigger


def trigger_delete(context, trigger_id, force=False):
    session = _session(context)
    trigger = session.query(models.Trigger).get(trigger_id)
    if not trigger:
        return

    trigger.soft_delete(session=session)
    session.flush()


# Webhooks
def webhook_create(context, values):
    webhook = models.Webhook()
    webhook.update(values)
    webhook.save(_session(context))
    return webhook


def webhook_get(context, webhook_id, show_deleted=False):
    webhook = model_query(context, models.Webhook).get(webhook_id)
    if not webhook:
        return None

    if not show_deleted and webhook.deleted_time is not None:
        return None

    return webhook


def webhook_get_by_name(context, name, show_deleted=False):
    return query_by_name(context, models.Webhook, name,
                         show_deleted=show_deleted)


def webhook_get_all(context, show_deleted=False, limit=None,
                    marker=None, sort_keys=None, sort_dir=None,
                    filters=None, project_safe=True):
    query = soft_delete_aware_query(context, models.Webhook,
                                    show_deleted=show_deleted)

    if project_safe:
        query = query.filter_by(project=context.project)

    if filters is None:
        filters = {}

    sort_key_map = {
        consts.WEBHOOK_NAME: models.Webhook.name.key,
        consts.WEBHOOK_OBJ_ID: models.Webhook.obj_id.key,
        consts.WEBHOOK_OBJ_TYPE: models.Webhook.obj_type.key,
        consts.WEBHOOK_CREATED_TIME: models.Webhook.created_time.key,
        consts.WEBHOOK_DELETED_TIME: models.Webhook.deleted_time.key,
    }
    keys = _get_sort_keys(sort_keys, sort_key_map)
    query = db_filters.exact_filter(query, models.Webhook, filters)
    return _paginate_query(context, query, models.Webhook,
                           limit=limit, marker=marker,
                           sort_keys=keys, sort_dir=sort_dir,
                           default_sort_keys=['obj_id']).all()


def webhook_get_by_short_id(context, short_id, show_deleted=False):
    return query_by_short_id(context, models.Webhook, short_id,
                             show_deleted=show_deleted)


def webhook_delete(context, webhook_id, force=False):
    session = _session(context)
    webhook = session.query(models.Webhook).get(webhook_id)
    if not webhook:
        return

    webhook.soft_delete(session=session)
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


def policy_get(context, policy_id, show_deleted=False, project_safe=True):
    policy = soft_delete_aware_query(context, models.Policy,
                                     show_deleted=show_deleted)
    policy = policy.filter_by(id=policy_id).first()

    if project_safe and policy is not None:
        if context.project != policy.project:
            return None

    return policy


def policy_get_by_name(context, name, show_deleted=False, project_safe=True):
    return query_by_name(context, models.Policy, name,
                         show_deleted=show_deleted,
                         project_safe=project_safe)


def policy_get_by_short_id(context, short_id, show_deleted=False,
                           project_safe=True):
    return query_by_short_id(context, models.Policy, short_id,
                             show_deleted=show_deleted,
                             project_safe=project_safe)


def policy_get_all(context, limit=None, marker=None, sort_keys=None,
                   sort_dir=None, filters=None, show_deleted=False,
                   project_safe=True):
    query = soft_delete_aware_query(context, models.Policy,
                                    show_deleted=show_deleted)

    if project_safe:
        query = query.filter_by(project=context.project)

    if filters is None:
        filters = {}

    sort_key_map = {
        consts.POLICY_TYPE: models.Policy.type.key,
        consts.POLICY_NAME: models.Policy.name.key,
        consts.POLICY_LEVEL: models.Policy.level.key,
        consts.POLICY_COOLDOWN: models.Policy.cooldown.key,
        consts.POLICY_CREATED_TIME: models.Policy.created_time.key,
        consts.POLICY_UPDATED_TIME: models.Policy.updated_time.key,
        consts.POLICY_DELETED_TIME: models.Policy.deleted_time.key,
    }
    keys = _get_sort_keys(sort_keys, sort_key_map)

    query = db_filters.exact_filter(query, models.Policy, filters)
    return _paginate_query(context, query, models.Policy,
                           limit=limit, marker=marker,
                           sort_keys=keys, sort_dir=sort_dir,
                           default_sort_keys=['created_time']).all()


def policy_update(context, policy_id, values):
    policy = model_query(context, models.Policy).get(policy_id)
    if not policy:
        raise exception.PolicyNotFound(policy=policy_id)

    policy.update(values)
    policy.save(_session(context))
    return policy


def policy_delete(context, policy_id, force=False):
    policy = policy_get(context, policy_id)

    if not policy:
        return

    query = model_query(context, models.ClusterPolicies)
    bindings = query.filter_by(policy_id=policy_id)
    if bindings.count():
        raise exception.ResourceBusyError(resource_type='policy',
                                          resource_id=policy_id)

    session = orm_session.Session.object_session(policy)

    policy.soft_delete(session=session)
    session.flush()


# Cluster-Policy Associations
def cluster_policy_get(context, cluster_id, policy_id):
    query = model_query(context, models.ClusterPolicies)
    bindings = query.filter_by(cluster_id=cluster_id,
                               policy_id=policy_id)
    return bindings.first()


def cluster_policy_get_all(context, cluster_id, filters=None,
                           sort_keys=None, sort_dir=None):
    query = model_query(context, models.ClusterPolicies)
    query = query.filter_by(cluster_id=cluster_id)
    if filters is None:
        filters = {}

    sort_key_map = {
        consts.CP_PRIORITY: models.ClusterPolicies.priority.key,
        consts.CP_LEVEL: models.ClusterPolicies.level.key,
        consts.CP_COOLDOWN: models.ClusterPolicies.cooldown.key,
        consts.CP_ENABLED: models.ClusterPolicies.enabled.key,
    }

    keys = _get_sort_keys(sort_keys, sort_key_map)
    query = db_filters.exact_filter(query, models.ClusterPolicies, filters)

    if sort_dir is None and sort_keys is None:
        sort_dir = 'desc'
    return _paginate_query(context, query, models.ClusterPolicies,
                           sort_keys=keys, sort_dir=sort_dir,
                           default_sort_keys=['priority']).all()


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

    session.delete(bindings)
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


def profile_get(context, profile_id, show_deleted=False, project_safe=True):
    query = soft_delete_aware_query(context, models.Profile,
                                    show_deleted=show_deleted)
    profile = query.filter_by(id=profile_id).first()

    if project_safe and profile is not None:
        if context.project != profile.project:
            return None

    return profile


def profile_get_by_name(context, name, show_deleted=False, project_safe=True):
    return query_by_name(context, models.Profile, name,
                         show_deleted=show_deleted,
                         project_safe=project_safe)


def profile_get_by_short_id(context, short_id, show_deleted=False,
                            project_safe=True):
    return query_by_short_id(context, models.Profile, short_id,
                             show_deleted=show_deleted,
                             project_safe=project_safe)


def profile_get_all(context, limit=None, marker=None, sort_keys=None,
                    sort_dir=None, filters=None, show_deleted=False,
                    project_safe=True):
    query = soft_delete_aware_query(context, models.Profile,
                                    show_deleted=show_deleted)

    if project_safe:
        query = query.filter_by(project=context.project)

    if filters is None:
        filters = {}

    sort_key_map = {
        consts.PROFILE_TYPE: models.Profile.type.key,
        consts.PROFILE_NAME: models.Profile.name.key,
        consts.PROFILE_PERMISSION: models.Profile.permission.key,
        consts.PROFILE_CREATED_TIME: models.Profile.created_time.key,
        consts.PROFILE_UPDATED_TIME: models.Profile.updated_time.key,
        consts.PROFILE_DELETED_TIME: models.Profile.deleted_time.key,
    }
    keys = _get_sort_keys(sort_keys, sort_key_map)

    query = db_filters.exact_filter(query, models.Profile, filters)
    return _paginate_query(context, query, models.Profile,
                           limit=limit, marker=marker,
                           sort_keys=keys, sort_dir=sort_dir,
                           default_sort_keys=['created_time']).all()


def profile_update(context, profile_id, values):
    profile = model_query(context, models.Profile).get(profile_id)
    if not profile:
        raise exception.ProfileNotFound(profile=profile_id)

    profile.update(values)
    profile.save(_session(context))
    return profile


def profile_delete(context, profile_id, force=False):
    profile = profile_get(context, profile_id, show_deleted=False)
    if profile is None:
        return

    # used by any clusters?
    query = model_query(context, models.Cluster)
    clusters = query.filter_by(profile_id=profile_id, deleted_time=None)
    if clusters.count() > 0:
        raise exception.ResourceBusyError(resource_type='profile',
                                          resource_id=profile_id)

    # used by any nodes?
    query = model_query(context, models.Node)
    nodes = query.filter_by(profile_id=profile_id, deleted_time=None)
    if nodes.count() > 0:
        raise exception.ResourceBusyError(resource_type='profile',
                                          resource_id=profile_id)

    session = orm_session.Session.object_session(profile)

    profile.soft_delete(session=session)
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
    cred = model_query(context, models.Credential).get((user, project))
    if cred is None:
        return None
    cred.delete()


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


def event_get(context, event_id):
    return model_query(context, models.Event).get(event_id)


def event_get_by_short_id(context, short_id):
    return query_by_short_id(context, models.Event, short_id)


def _event_filter_paginate_query(context, query, filters=None,
                                 limit=None, marker=None,
                                 sort_keys=None, sort_dir=None):
    if filters is None:
        filters = {}

    sort_key_map = {
        consts.EVENT_TIMESTAMP: models.Event.timestamp.key,
        consts.EVENT_LEVEL: models.Event.level.key,
        consts.EVENT_OBJ_TYPE: models.Event.obj_type.key,
        consts.EVENT_OBJ_NAME: models.Event.obj_name.key,
        consts.EVENT_USER: models.Event.user.key,
        consts.EVENT_ACTION: models.Event.action.key,
    }
    keys = _get_sort_keys(sort_keys, sort_key_map)

    query = db_filters.exact_filter(query, models.Event, filters)
    return _paginate_query(context, query, models.Event,
                           limit=limit, marker=marker,
                           sort_keys=keys, sort_dir=sort_dir,
                           default_sort_keys=['timestamp']).all()


def event_get_all(context, limit=None, marker=None, sort_keys=None,
                  sort_dir=None, filters=None, project_safe=True,
                  show_deleted=False):
    query = soft_delete_aware_query(context, models.Event,
                                    show_deleted=show_deleted)
    if project_safe:
        query = query.filter_by(project=context.project)

    return _event_filter_paginate_query(context, query, filters=filters,
                                        limit=limit, marker=marker,
                                        sort_keys=sort_keys,
                                        sort_dir=sort_dir)


def event_count_by_cluster(context, cluster_id):
    count = model_query(context, models.Event).\
        filter_by(cluster_id=cluster_id).count()
    return count


def event_get_all_by_cluster(context, cluster_id, limit=None, marker=None,
                             sort_keys=None, sort_dir=None, filters=None):
    query = model_query(context, models.Event).\
        filter_by(cluster_id=cluster_id)

    return _event_filter_paginate_query(context, query, filters=filters,
                                        limit=limit, marker=marker,
                                        sort_keys=sort_keys,
                                        sort_dir=sort_dir)


def purge_deleted(age, granularity='days'):
    pass
#    try:
#        age = int(age)
#    except ValueError:
#        raise exception.Error(_("age should be an integer"))
#    if age < 0:
#        raise exception.Error(_("age should be a positive integer"))
#
#    if granularity not in ('days', 'hours', 'minutes', 'seconds'):
#        raise exception.Error(
#            _("granularity should be days, hours, minutes, or seconds"))
#
#    if granularity == 'days':
#        age = age * 86400
#    elif granularity == 'hours':
#        age = age * 3600
#    elif granularity == 'minutes':
#        age = age * 60
#
#    time_line = datetime.datetime.now() - datetime.timedelta(seconds=age)
#    engine = get_engine()
#    meta = sqlalchemy.MetaData()
#    meta.bind = engine
#
#    cluster = sqlalchemy.Table('cluster', meta, autoload=True)
#    event = sqlalchemy.Table('event', meta, autoload=True)
#    cluster_policies = sqlalchemy.Table('cluster_policy', meta, autoload=True)
#    user_creds = sqlalchemy.Table('user_creds', meta, autoload=True)
#
#    stmt = sqlalchemy.select([cluster.c.id,
#                              cluster.c.profile_id,
#                              cluster.c.user_creds_id]).\
#        where(cluster.c.deleted_at < time_line)
#    deleted_clusters = engine.execute(stmt)
#
#    for s in deleted_clusters:
#        event_del = event.delete().where(event.c.cluster_id == s[0])
#        engine.execute(event_del)
#        cluster_del = cluster.delete().where(cluster.c.id == s[0])
#        engine.execute(cluster_del)
#        cluster_policies_del = cluster_policies.delete().\
#            where(.c.id == s[1])
#        engine.execute(raw_template_del)
#        user_creds_del = user_creds.delete().where(user_creds.c.id == s[2])
#        engine.execute(user_creds_del)


# Actions
def action_create(context, values):
    action = models.Action()
    action.update(values)
    action.save(_session(context))
    return action


def action_update(context, action_id, values):
    action = action_get(context, action_id)

    if not action:
        raise exception.ActionNotFound(action=action_id)

    action.update(values)
    action.save(_session(context))


def action_get(context, action_id, show_deleted=False, refresh=False):
    session = _session(context)
    action = session.query(models.Action).get(action_id)
    deleted_ok = show_deleted or context.show_deleted

    if action is None or action.deleted_time is not None and not deleted_ok:
        return None

    if refresh:
        session.refresh(action)

    return action


def action_get_by_name(context, name):
    return query_by_name(context, models.Action, name)


def action_get_by_short_id(context, short_id):
    return query_by_short_id(context, models.Action, short_id)


def action_get_1st_ready(context):
    query = model_query(context, models.Action).\
        filter_by(status=ACTION_READY)
    return query.first()


def action_get_all_ready(context):
    query = model_query(context, models.Action).\
        filter_by(status=ACTION_READY)
    return query.all()


def action_get_all_by_owner(context, owner_id):
    query = model_query(context, models.Action).\
        filter_by(owner=owner_id)
    return query.all()


def action_get_all(context, filters=None, limit=None, marker=None,
                   sort_keys=None, sort_dir=None, show_deleted=False):
    query = soft_delete_aware_query(context, models.Action,
                                    show_deleted=show_deleted)

    if filters is None:
        filters = {}

    sort_key_map = {
        consts.ACTION_NAME: models.Action.name.key,
        consts.ACTION_TARGET: models.Action.target.key,
        consts.ACTION_ACTION: models.Action.action.key,
        consts.ACTION_CREATED_TIME: models.Action.created_time.key,
        consts.ACTION_STATUS: models.Action.status.key,
    }
    keys = _get_sort_keys(sort_keys, sort_key_map)

    query = db_filters.exact_filter(query, models.Action, filters)
    return _paginate_query(context, query, models.Action,
                           limit=limit, marker=marker,
                           sort_keys=keys, sort_dir=sort_dir,
                           default_sort_keys=['created_time']).all()


def _action_dependency_add(query, action_id, field, adds):
    if not isinstance(adds, list):
        add_list = [adds]
    else:
        add_list = adds

    action = query.get(action_id)
    if action is None:
        raise exception.ActionNotFound(action=action_id)

    query.session.refresh(action)
    if action[field] is None:
        d = add_list
    else:
        d = list(set(action[field]).union(set(add_list)))
    action[field] = d

    if field == 'depends_on':
        action.status = ACTION_WAITING
        action.status_reason = _('The action is waiting for its dependency '
                                 'being completed.')


def _action_dependency_del(query, action_id, field, dels):
    if not isinstance(dels, list):
        del_list = [dels]
    else:
        del_list = dels

    action = query.get(action_id)
    if not action:
        msg = _('Action with id "%s" not found') % action_id
        LOG.warning(msg)
        return

    query.session.refresh(action)
    if action[field] is not None:
        action[field] = list(set(action[field]) - set(del_list))

    if field == 'depends_on' and len(action[field]) == 0:
        action.status = ACTION_READY
        action.status_reason = _('The action becomes ready due to all '
                                 'dependencies have been satisfied.')


def action_add_dependency(context, depended, dependent):
    if isinstance(depended, list) and isinstance(dependent, list):
        raise exception.NotSupport(
            _('Multiple dependencies between lists not support'))

    query = model_query(context, models.Action)
    session = query.session

    if isinstance(depended, list):   # e.g. D depends on A,B,C
        session.begin()
        for d in depended:
            _action_dependency_add(query, d, "depended_by", dependent)

        _action_dependency_add(query, dependent, "depends_on", depended)
        session.commit()
        return

    # Only dependent can be a list now, convert it to a list if it
    # is not a list
    if not isinstance(dependent, list):  # e.g. B,C,D depend on A
        dependents = [dependent]
    else:
        dependents = dependent

    session.begin()
    _action_dependency_add(query, depended, "depended_by", dependent)

    for d in dependents:
        _action_dependency_add(query, d, "depends_on", depended)
    session.commit()


def action_del_dependency(context, depended, dependent):
    if isinstance(depended, list) and isinstance(dependent, list):
        raise exception.NotSupport(
            _('Multiple dependencies between lists not support'))

    query = model_query(context, models.Action)
    session = query.session

    if isinstance(depended, list):   # e.g. D depends on A,B,C
        session.begin()
        for d in depended:
            _action_dependency_del(query, d, "depended_by", dependent)

        _action_dependency_del(query, dependent, "depends_on", depended)
        session.commit()
        return

    # Only dependent can be a list now, convert it to a list if it
    # is not a list
    if not isinstance(dependent, list):  # e.g. B,C,D depend on A
        dependents = [dependent]
    else:
        dependents = dependent

    session.begin()
    _action_dependency_del(query, depended, "depended_by", dependent)

    for d in dependents:
        _action_dependency_del(query, d, "depends_on", depended)
    session.commit()


def action_mark_succeeded(context, action_id, timestamp):
    query = model_query(context, models.Action)
    action = query.get(action_id)
    if not action:
        raise exception.ActionNotFound(action=action_id)

    session = query.session
    session.begin()

    action.owner = None
    action.status = ACTION_SUCCEEDED
    action.status_reason = _('Action completed successfully.')
    action.end_time = timestamp

    for a in action.depended_by:
        _action_dependency_del(query, a, 'depends_on', action_id)
    action.depended_by = []

    session.commit()
    return action


def _mark_failed_action(query, action_id, timestamp, reason):
    action = query.get(action_id)
    if not action:
        LOG.warning(_('Action with id "%s" not found') % action_id)
        return

    action.owner = None
    action.status = ACTION_FAILED
    action.status_reason = reason
    action.end_time = timestamp

    if action.depended_by is not None:
        for child in action.depended_by:
            _mark_failed_action(query, child, timestamp, reason)


def action_mark_failed(context, action_id, timestamp, reason=None):
    query = model_query(context, models.Action)

    session = query.session
    session.begin()

    action = query.get(action_id)
    action.owner = None
    action.status = ACTION_FAILED
    if reason is not None:
        action.status_reason = six.text_type(reason)
    else:
        action.status_reason = _('Action execution failed')
    action.end_time = timestamp

    for child in action.depended_by:
        child_reason = _('Action %(id)s failed: %(reason)s') % {
            'id': action_id, 'reason': action.status_reason}
        _mark_failed_action(query, child, timestamp, child_reason)

    session.commit()
    return action


def _mark_cancelled_action(query, action_id, timestamp):
    action = query.get(action_id)
    if not action:
        LOG.warning(_('Action with id "%s" not found') % action_id)
        return

    action.owner = None
    action.status = ACTION_CANCELED
    action.status_reason = _('Dependent action was cancelled')
    action.end_time = timestamp
    if action.depended_by is not None:
        for a in action.depended_by:
            _mark_cancelled_action(query, a, timestamp)


def action_mark_cancelled(context, action_id, timestamp):
    query = model_query(context, models.Action)
    action = query.get(action_id)
    if not action:
        raise exception.ActionNotFound(action=action_id)

    session = query.session
    session.begin()

    action.owner = None
    action.status = ACTION_CANCELED
    action.reason = _('Action execution was cancelled')
    action.end_time = timestamp

    for a in action.depended_by:
        _mark_cancelled_action(query, a, timestamp)
    session.commit()

    return action


def action_acquire(context, action_id, owner, timestamp):
    session = _session(context)

    with session.begin():
        action = session.query(models.Action).get(action_id)
        if not action:
            return None

        if action.owner and action.owner != owner:
            return None

        if action.status != ACTION_READY:
            msg = _('The action is not in an executable status: '
                    '%s') % action.status
            LOG.warning(msg)
            return None
        action.owner = owner
        action.start_time = timestamp
        action.status = ACTION_RUNNING
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
    action.status = ACTION_READY
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

    action.soft_delete(session=session)
    session.flush()


# Utils
def db_sync(engine, version=None):
    """Migrate the database to `version` or the most recent version."""
    return migration.db_sync(engine, version=version)


def db_version(engine):
    """Display the current database version."""
    return migration.db_version(engine)
