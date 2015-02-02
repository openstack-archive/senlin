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
from sqlalchemy.orm import session as orm_session

from senlin.common import attr
from senlin.common import exception
from senlin.common.i18n import _
from senlin.db.sqlalchemy import filters as db_filters
from senlin.db.sqlalchemy import migration
from senlin.db.sqlalchemy import models
from senlin.openstack.common import log as logging

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
            sort_dir = 'desc'

    # This assures the order of the clusters will always be the same
    # even for sort_key values that are not unique in the database
    sort_keys = sort_keys + ['id']

    model_marker = None
    if marker:
        model_marker = model_query(context, model).get(marker)
    try:
        query = utils.paginate_query(query, model, limit, sort_keys,
                                     model_marker, sort_dir)
    except utils.InvalidSortKey as exc:
        # TODO(Qiming): Catch this exception and return to user
        raise exception.Invalid(reason=exc.message)
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


def _session(context):
    return (context and context.session) or get_session()


# Clusters
def cluster_create(context, values):
    cluster_ref = models.Cluster()
    if 'status_reason' in values:
        values['status_reason'] = values['status_reason'][:255]
    cluster_ref.update(values)
    cluster_ref.save(_session(context))
    return cluster_ref


def cluster_get(context, cluster_id, show_deleted=False, tenant_safe=True):
    query = model_query(context, models.Cluster)
    cluster = query.get(cluster_id)

    deleted_ok = show_deleted or context.show_deleted
    if cluster is None or cluster.deleted_time is not None and not deleted_ok:
        return None

    if tenant_safe and (cluster is not None):
        if (context is not None) and (context.tenant_id != cluster.project):
            return None
    return cluster


def cluster_get_all_by_parent(context, parent):
    results = soft_delete_aware_query(context, models.Cluster).\
        filter_by(parent=parent).all()
    return results


def cluster_get_by_name_and_parent(context, cluster_name, parent):
    query = soft_delete_aware_query(context, models.Cluster).\
        filter_by(project=context.tenant_id).\
        filter_by(name=cluster_name).\
        filter_by(parent=parent)
    return query.first()


def cluster_get_by_name(context, cluster_name):
    r0 = soft_delete_aware_query(context, models.Cluster)
    result = r0.filter_by(project=context.tenant_id, name=cluster_name).first()
    return result


def _query_cluster_get_all(context, tenant_safe=True, show_deleted=False,
                           show_nested=False):
    query = soft_delete_aware_query(context, models.Cluster,
                                    show_deleted=show_deleted)

    if not show_nested:
        query = query.filter_by(parent=None)

    if tenant_safe:
        query = query.filter_by(project=context.tenant_id)
    return query


def cluster_get_all(context, limit=None, marker=None, sort_keys=None,
                    sort_dir=None, filters=None, tenant_safe=True,
                    show_deleted=False, show_nested=False):
    query = _query_cluster_get_all(context, tenant_safe=tenant_safe,
                                   show_deleted=show_deleted,
                                   show_nested=show_nested)
    if filters is None:
        filters = {}

    sort_key_map = {
        attr.CLUSTER_NAME: models.Cluster.name.key,
        attr.CLUSTER_STATUS: models.Cluster.status.key,
        attr.CLUSTER_CREATED_TIME: models.Cluster.created_time.key,
        attr.CLUSTER_UPDATED_TIME: models.Cluster.updated_time.key,
    }
    keys = _get_sort_keys(sort_keys, sort_key_map)

    query = db_filters.exact_filter(query, models.Cluster, filters)
    return _paginate_query(context, query, models.Cluster, limit=limit,
                           marker=marker, sort_keys=keys, sort_dir=sort_dir,
                           default_sort_keys=['init_time']).all()


def cluster_count_all(context, filters=None, tenant_safe=True,
                      show_deleted=False, show_nested=False):
    query = _query_cluster_get_all(context, tenant_safe=tenant_safe,
                                   show_deleted=show_deleted,
                                   show_nested=show_nested)
    query = db_filters.exact_filter(query, models.Cluster, filters)
    return query.count()


def cluster_update(context, cluster_id, values):
    cluster = cluster_get(context, cluster_id)

    if not cluster:
        raise exception.NotFound(
            _('Attempt to update a cluster with id "%s" that does '
              'not exist failed') % cluster_id)

    cluster.update(values)
    cluster.save(_session(context))


def cluster_delete(context, cluster_id):
    cluster = cluster_get(context, cluster_id)
    if not cluster:
        raise exception.NotFound(
            _('Attempt to delete a cluster with id "%s" that does '
              'not exist failed') % cluster_id)

    session = orm_session.Session.object_session(cluster)

    nodes = node_get_all_by_cluster(context, cluster_id)
    for node in nodes.values():
        session.delete(node)

    cluster.soft_delete(session=session)
    session.flush()


# Nodes
def node_create(context, values):
    node = models.Node()
    if 'status_reason' in values:
        values['status_reason'] = values['status_reason'][:255]
    node.update(values)
    node.save(_session(context))
    return node


def node_get(context, node_id, show_deleted=False):
    node = model_query(context, models.Node).get(node_id)
    if not node:
        return None

    if not show_deleted and node.deleted_time is not None:
        return None

    return node


def _query_node_get_all(context, show_deleted=False, cluster_id=None):
    query = soft_delete_aware_query(context, models.Node,
                                    show_deleted=show_deleted)

    if cluster_id:
        query = query.filter_by(cluster_id=cluster_id)

    return query


def node_get_all(context, cluster_id=None, show_deleted=False,
                 limit=None, marker=None, sort_keys=None, sort_dir=None,
                 filters=None, tenant_safe=True):
    query = _query_node_get_all(context, show_deleted=show_deleted,
                                cluster_id=cluster_id)
    if filters is None:
        filters = {}

    sort_key_map = {
        attr.NODE_INDEX: models.Node.index.key,
        attr.NODE_NAME: models.Node.name.key,
        attr.NODE_CREATED_TIME: models.Node.created_time.key,
        attr.NODE_UPDATED_TIME: models.Node.updated_time.key,
        attr.NODE_DELETED_TIME: models.Node.deleted_time.key,
        attr.NODE_STATUS: models.Node.status.key,
    }
    keys = _get_sort_keys(sort_keys, sort_key_map)
    query = db_filters.exact_filter(query, models.Node, filters)
    return _paginate_query(context, query, models.Node,
                           limit=limit, marker=marker,
                           sort_keys=keys, sort_dir=sort_dir,
                           default_sort_keys=['init_time']).all()


def node_get_all_by_cluster(context, cluster_id):
    query = model_query(context, models.Node).filter_by(cluster_id=cluster_id)
    nodes = query.all()
    return dict((node.name, node) for node in nodes)


def node_get_by_name_and_cluster(context, node_name, cluster_id):
    q0 = model_query(context, models.Node).filter_by(name=node_name)
    node = q0.filter_by(cluster_id=cluster_id).first()
    return node


def node_get_by_physical_id(context, phy_id):
    query = model_query(context, models.Node).filter_by(physical_id=phy_id)
    return query.first()


def node_update(context, node_id, values):
    '''Update a node with new property values.

    :param node_id: ID of the node to be updated.
    :param values: A dictionary of values to be updated on the node.
    :raises NotFound: The specified node does not exist in database.
    '''
    query = model_query(context, models.Node)
    node = query.get(node_id)

    if not node:
        raise exception.NotFound(
            _('Attempt to update a node with id "%s" that does '
              ' not exists failed') % node_id)

    node.update(values)
    node.save(query.session)


def node_migrate(context, node_id, from_cluster, to_cluster):
    query = model_query(context, models.Node)
    node = query.get(node_id)
    session = query.session
    session.begin()
    if from_cluster:
        cluster1 = session.query(models.Cluster).get(from_cluster)
        cluster1.size -= 1
    if to_cluster:
        cluster2 = session.query(models.Cluster).get(to_cluster)
        cluster2.size += 1
    node.cluster_id = to_cluster
    session.commit()


def node_delete(context, node_id, force=False):
    node = node_get(context, node_id)

    if not node:
        msg = _('Attempt to delete a node with id "%s" that does not '
                'exist failed') % node_id
        raise exception.NotFound(msg)

    session = orm_session.Session.object_session(node)
    node.soft_delete(session=session)
    session.flush()


# Locks
def cluster_lock_acquire(cluster_id, action_id):
    session = get_session()
    with session.begin():
        lock = session.query(models.ClusterLock).get(cluster_id)
        # TODO(Qiming): lock nodes as well
        if lock is not None:
            return lock.worker_id
        session.add(models.ClusterLock(cluster_id=cluster_id,
                                       worker_id=action_id))
        return action_id


def cluster_lock_steal(cluster_id, old_worker_id, new_worker_id):
    session = get_session()
    with session.begin():
        lock = session.query(models.ClusterLock).get(cluster_id)
        rows_affected = session.query(models.ClusterLock).\
            filter_by(cluster_id=cluster_id, worker_id=old_worker_id).\
            update({"worker_id": new_worker_id})
        # TODO(Qiming): steal locks from nodes as well
    if not rows_affected:
        return lock.worker_id if lock is not None else True


def cluster_lock_release(cluster_id, worker_id):
    session = get_session()
    with session.begin():
        rows_affected = session.query(models.ClusterLock).\
            filter_by(cluster_id=cluster_id, worker_id=worker_id).\
            delete()
        # TODO(Qiming): delete locks from nodes as well
    if not rows_affected:
        return True


def node_lock_create(node_id, worker_id):
    session = get_session()
    with session.begin():
        lock = session.query(models.NodeLock).get(node_id)
        if lock is not None:
            return lock.worker_id
        session.add(models.NodeLock(node_id=node_id,
                                    worker_id=worker_id))


def node_lock_steal(node_id, old_worker_id, new_worker_id):
    session = get_session()
    with session.begin():
        lock = session.query(models.NodeLock).get(node_id)
        rows_affected = session.query(models.NodeLock).\
            filter_by(node_id=node_id, worker_id=old_worker_id).\
            update({"worker_id": new_worker_id})
    if not rows_affected:
        return lock.worker_id if lock is not None else True


def node_lock_release(node_id, worker_id):
    session = get_session()
    with session.begin():
        rows_affected = session.query(models.NodeLock).\
            filter_by(node_id=node_id, worker_id=worker_id).\
            delete()
    if not rows_affected:
        return True


# Policies
def policy_create(context, values):
    policy = models.Policy()
    policy.update(values)
    policy.save(_session(context))
    return policy


def policy_get(context, policy_id, show_deleted=False):
    policy = soft_delete_aware_query(context, models.Policy,
                                     show_deleted=show_deleted)
    policy = policy.filter_by(id=policy_id).first()
    if not policy:
        msg = _('Policy with id "%s" not found') % policy_id
        raise exception.NotFound(msg)
    return policy


def policy_get_all(context, show_deleted=False):
    policies = soft_delete_aware_query(context, models.Policy,
                                       show_deleted=show_deleted).all()
    if not policies:
        raise exception.NotFound(_('No policy were found'))
    return policies


def policy_update(context, policy_id, values):
    policy = policy_get(context, policy_id)

    if not policy:
        msg = _('Attempt to update a policy with id: %(id)s that does not '
                'exist failed') % policy_id
        raise exception.NotFound(msg)

    policy.update(values)
    policy.save(_session(context))
    return policy


def policy_delete(context, policy_id, force=False):
    policy = policy_get(context, policy_id)

    if not policy:
        msg = _('Attempt to delete a policy with id "%s" that does not '
                'exist failed') % policy_id
        raise exception.NotFound(msg)

    session = orm_session.Session.object_session(policy)

    # TODO(Qiming): Check if a policy is still in use, raise an exception
    # if so
    policy.soft_delete(session=session)
    session.flush()


# Cluster-Policy Associations
def cluster_attach_policy(context, cluster_id, policy_id, values):
    binding = models.ClusterPolicies()
    binding.cluster_id = cluster_id
    binding.policy_id = policy_id
    binding.update(values)
    binding.save(_session(context))
    return binding


def cluster_get_policies(context, cluster_id):
    policies = model_query(context, models.ClusterPolicies).\
        filter_by(cluster_id=cluster_id).all()
    return policies


def cluster_detach_policy(context, cluster_id, policy_id):
    binding = model_query(context, models.ClusterPolicies).\
        filter_by(cluster_id=cluster_id, policy_id=policy_id).first()

    if not binding:
        msg = _('Failed detaching policy "%(policy)s" from cluster '
                '"%(cluster)s"') % {'policy': policy_id,
                                    'cluster': cluster_id}
        raise exception.NotFound(msg)

    session = orm_session.Session.object_session(binding)
    session.delete(binding)
    session.flush()


def cluster_enable_policy(context, cluster_id, policy_id):
    binding = model_query(context, models.ClusterPolicies).\
        filter_by(cluster_id=cluster_id, policy_id=policy_id).first()

    if not binding:
        msg = _('Failed enabling policy "%(policy)s" on cluster '
                '"%(cluster)s"') % {'policy': policy_id,
                                    'cluster': cluster_id}

        raise exception.NotFound(msg)

    binding.enabled = True
    binding.save(_session(context))
    return binding


def cluster_disable_policy(context, cluster_id, policy_id):
    binding = model_query(context, models.ClusterPolicies).\
        filter_by(cluster_id=cluster_id, policy_id=policy_id).first()

    if not binding:
        msg = _('Failed disabling policy "%(policy)s" on cluster '
                '"%(cluster)s"') % {'policy': policy_id,
                                    'cluster': cluster_id}
        raise exception.NotFound(msg)

    binding.enabled = False
    binding.save(_session(context))
    return binding


# Profiles
def profile_create(context, values):
    profile = models.Profile()
    profile.update(values)
    profile.save(_session(context))
    return profile


def profile_get(context, profile_id):
    profile = model_query(context, models.Profile).get(profile_id)
    if not profile:
        msg = _('Profile with id "%s" not found') % profile_id
        raise exception.NotFound(msg)
    return profile


def profile_get_all(context, limit=None, marker=None, sort_keys=None,
                    sort_dir=None, filters=None, show_deleted=False):
    query = soft_delete_aware_query(context, models.Profile,
                                    show_deleted=show_deleted)

    if filters is None:
        filters = {}

    sort_key_map = {
        attr.PROFILE_TYPE: models.Profile.type.key,
        attr.PROFILE_NAME: models.Profile.name.key,
        attr.PROFILE_PERMISSION: models.Profile.permission.key,
        attr.PROFILE_CREATED_TIME: models.Profile.created_time.key,
        attr.PROFILE_UPDATED_TIME: models.Profile.updated_time.key,
        attr.PROFILE_DELETED_TIME: models.Profile.deleted_time.key,
        attr.PROFILE_TAGS: models.Profile.tags.key,
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
        raise exception.NotFound(
            _('Profile with id "%s" not found') % profile_id)

    profile.update(values)
    profile.save(_session(context))
    return profile


def profile_delete(context, profile_id, force=False):
    profile = profile_get(context, profile_id)
    session = orm_session.Session.object_session(profile)

    # TODO(Qiming): Check if a profile is still in use, raise an exception
    # if so
    profile.soft_delete(session=session)
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


def event_create(context, values):
    if values['obj_type'] == 'CLUSTER' and cfg.CONF.max_events_per_cluster:
        cluster_id = values['obj_id']
        event_count = event_count_by_cluster(context, cluster_id)
        if (event_count >= cfg.CONF.max_events_per_cluster):
            # prune events
            batch_size = cfg.CONF.event_purge_batch_size
            _delete_event_rows(context, cluster_id, batch_size)

    event = models.Event()
    if 'status_reason' in values:
        values['status_reason'] = values['status_reason'][:255]
    event.update(values)
    event.save(_session(context))
    return event


def event_get(context, event_id):
    event = model_query(context, models.Event).get(event_id)
    return event


def event_get_all(context):
    events = model_query(context, models.Event).all()
    return events


def _events_paginate_query(context, query, model, limit=None, sort_keys=None,
                           marker=None, sort_dir=None):
    default_sort_keys = ['timestamp']
    if not sort_keys:
        sort_keys = default_sort_keys
        if not sort_dir:
            sort_dir = 'desc'

    # This assures the order of the clusters will always be the same
    # even for sort_key values that are not unique in the database
    sort_keys = sort_keys + ['id']

    model_marker = None
    if marker:
        # not to use model_query(context, model).get(marker), because
        # user can only see the ID(column 'uuid') and the ID as the marker
        model_marker = model_query(context, model).filter_by(id=marker).first()
    try:
        query = utils.paginate_query(query, model, limit, sort_keys,
                                     model_marker, sort_dir)
    except utils.InvalidSortKey as exc:
        raise exception.Invalid(reason=exc.message)

    return query


def event_count_by_cluster(context, cid):
    count = model_query(context, models.Event).\
        filter_by(obj_id=cid, obj_type='CLUSTER').count()
    return count


def _events_by_cluster(context, cid):
    query = model_query(context, models.Event).\
        filter_by(obj_id=cid, obj_type='CLUSTER')
    return query


def event_get_all_by_cluster(context, cluster_id, limit=None, marker=None,
                             sort_keys=None, sort_dir=None, filters=None):
    query = _events_by_cluster(context, cluster_id)

    if filters is None:
        filters = {}

    sort_key_map = {
        attr.EVENT_TIMESTAMP: models.Event.timestamp.key,
        attr.EVENT_OBJ_TYPE: models.Event.obj_type.key,
    }
    keys = _get_sort_keys(sort_keys, sort_key_map)

    query = db_filters.exact_filter(query, models.Event, filters)
    return _events_paginate_query(context, query, models.Event,
                                  limit=limit, marker=marker,
                                  sort_keys=keys, sort_dir=sort_dir,
                                  default_sort_keys=['timestamp']).all()


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


def action_get(context, action_id):
    action = model_query(context, models.Action).get(action_id)
    if not action:
        msg = _('Action with id "%s" not found') % action_id
        raise exception.NotFound(msg)
    return action


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
        attr.ACTION_NAME: models.Action.name.key,
        attr.ACTION_TARGET: models.Action.target.key,
        attr.ACTION_ACTION: models.Action.action.key,
        attr.ACTION_INTERVAL: models.Action.interval.key,
        attr.ACTION_START_TIME: models.Action.start_time.key,
        attr.ACTION_END_TIME: models.Action.end_time.key,
        attr.ACTION_INPUTS: models.Action.inputs.key,
        attr.ACTION_OUTPUTS: models.Action.outputs.key,
        attr.ACTION_DEPENDS_ON: models.Action.depends_on.key,
        attr.ACTION_DEPENDED_BY: models.Action.depended_by.key,
        attr.ACTION_STATUS: models.Action.status.key,
        attr.ACTION_STATUS_REASON: models.Action.status_reason.key,
    }
    keys = _get_sort_keys(sort_keys, sort_key_map)

    query = db_filters.exact_filter(query, models.Action, filters)
    return _paginate_query(context, query, models.Action,
                           limit=limit, marker=marker,
                           sort_keys=keys, sort_dir=sort_dir,
                           default_sort_keys=['created_time']).all()


def _action_dependency_add(context, action_id, field, adds):
    if not isinstance(adds, list):
        add_list = [adds]
    else:
        add_list = adds

    action = model_query(context, models.Action).get(action_id)
    if not action:
        msg = _('Action with id "%s" not found') % action_id
        raise exception.NotFound(msg)

    if action[field] is None:
        d = add_list
    else:
        d = list(set(action[field]).union(set(add_list)))
    action[field] = d

    if field == 'depends_on':
        action.status = ACTION_WAITING
        action.status_reason = ACTION_WAITING
        action.status_reason = _('The action is waiting for its dependancy \
                                   being completed.')


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
            _action_dependency_add(context, d, "depended_by", dependent)

        _action_dependency_add(context, dependent, "depends_on", depended)
        session.commit()
        return

    # Only dependent can be a list now, convert it to a list if it
    # is not a list
    if not isinstance(dependent, list):  # e.g. B,C,D depend on A
        dependents = [dependent]
    else:
        dependents = dependent

    session.begin()
    _action_dependency_add(context, depended, "depended_by", dependent)

    for d in dependents:
        _action_dependency_add(context, d, "depends_on", depended)
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
        raise exception.NotFound(
            _('Action with id "%s" not found') % action_id)

    session = query.session
    session.begin()

    action.status = ACTION_SUCCEEDED
    action.end_time = timestamp

    for a in action.depended_by:
        _action_dependency_del(query, a, 'depends_on', action_id)
    action.depended_by = []

    session.commit()
    return action


def _mark_failed_action(query, action_id, timestamp):
    action = query.get(action_id)
    if not action:
        LOG.warning(_('Action with id "%s" not found') % action_id)
        return

    action.status = ACTION_FAILED
    action.end_time = timestamp
    if action.depended_by is not None:
        for a in action.depended_by:
            _mark_failed_action(query, a, timestamp)


def action_mark_failed(context, action_id, timestamp):
    query = model_query(context, models.Action)
    action = query.get(action_id)
    if not action:
        raise exception.NotFound(
            _('Action with id "%s" not found') % action_id)

    session = query.session
    session.begin()

    action.status = ACTION_FAILED
    action.end_time = timestamp

    for a in action.depended_by:
        _mark_failed_action(query, a, timestamp)

    session.commit()
    return action


def _mark_cancelled_action(query, action_id, timestamp):
    action = query.get(action_id)
    if not action:
        LOG.warning(_('Action with id "%s" not found') % action_id)
        return

    action.status = ACTION_CANCELED
    action.end_time = timestamp
    if action.depended_by is not None:
        for a in action.depended_by:
            _mark_cancelled_action(query, a, timestamp)


def action_mark_cancelled(context, action_id, timestamp):
    query = model_query(context, models.Action)
    action = query.get(action_id)
    if not action:
        raise exception.NotFound(
            _('Action with id "%s" not found') % action_id)

    session = query.session
    session.begin()

    action.status = ACTION_CANCELED
    action.end_time = timestamp

    for a in action.depended_by:
        _mark_cancelled_action(query, a, timestamp)
    session.commit()

    return action


def action_acquire(context, action_id, owner, timestamp):
    query = model_query(context, models.Action)
    action = query.get(action_id)
    if not action:
        raise exception.NotFound(
            _('Action with id "%s" not found') % action_id)

    if action.owner and action.owner != owner:
        raise exception.ActionIsOwned(owner=action.owner)

    action.owner = owner
    action.start_time = timestamp
    action.status = ACTION_RUNNING
    action.status_reason = _('The action is being processed.')
    action.save(query.session)
    return action


def action_release(context, action_id, owner):
    query = model_query(context, models.Action)
    action = query.get(action_id)
    if not action:
        raise exception.NotFound(
            _('Action with id "%s" not found') % action_id)

    if action.owner is None:
        return

    if action.owner != owner:
        raise exception.ActionIsStolen(owner=action.owner)

    action.owner = owner
    action.start_time = None
    action.status = ACTION_READY
    action.status_reason = _('The action released.')
    action.save(query.session)
    return action


def action_lock_check(context, action_id, owner=None):
    action = model_query(context, models.Action).get(action_id)
    if not action:
        raise exception.NotFound(
            _('Action with id "%s" not found') % action_id)

    if owner:
        return owner if owner == action.owner else action.owner
    else:
        return action.owner if action.owner else None


def action_control(context, action_id, value):
    query = model_query(context, models.Action)
    action = query.get(action_id)
    if not action:
        return

    action.control = value
    action.save(query.session)


def action_control_check(context, action_id):
    action = model_query(context, models.Action).get(action_id)
    if not action:
        raise exception.NotFound(
            _('Action with id "%s" not found') % action_id)

    return action.control


def action_delete(context, action_id, force=False):
    query = model_query(context, models.Action)
    action = query.get(action_id)

    if not action:
        msg = _('Attempt to delete a action with id "%s" that does not'
                ' exist') % action_id
        raise exception.NotFound(msg)

    # TODO(liuh): Need check if and how an action can be safety deleted
    action.delete()
    query.session.flush()


# Utils
def db_sync(engine, version=None):
    """Migrate the database to `version` or the most recent version."""
    return migration.db_sync(engine, version=version)


def db_version(engine):
    """Display the current database version."""
    return migration.db_version(engine)
