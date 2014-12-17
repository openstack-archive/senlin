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
Implementation of SQLAlchemy backend.
'''

import datetime
import six
import sys

from oslo.config import cfg
from oslo.db.sqlalchemy import session as db_session
from oslo.db.sqlalchemy import utils
import sqlalchemy
from sqlalchemy import orm
from sqlalchemy.orm import session as orm_session

from senlin.common import crypt
from senlin.common import exception
from senlin.common import i18n
from senlin.db.sqlalchemy import filters as db_filters
from senlin.db.sqlalchemy import migration
from senlin.db.sqlalchemy import models
from senlin.rpc import api as rpc_api

CONF = cfg.CONF
CONF.import_opt('max_events_per_cluster', 'senlin.common.config')

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


def soft_delete_aware_query(context, *args, **kwargs):
    """
    Cluster query helper that accounts for the `show_deleted` field.

    :param show_deleted: if True, overrides context's show_deleted field.
    """

    query = model_query(context, *args)
    show_deleted = kwargs.get('show_deleted') or context.show_deleted

    if not show_deleted:
        query = query.filter_by(deleted_at=None)
    return query


def _session(context):
    return (context and context.session) or get_session()


# Clusters
def cluster_create(context, values):
    cluster = models.Cluster()
    cluster.update(values)
    cluster.save(_session(context))

    return cluster


def cluster_get(context, cluster_id, show_deleted=False, tenant_safe=True):
    query = model_query(context, models.Cluster)
    cluster = query.get(cluster_id)

    deleted_ok = show_deleted or context.show_deleted
    if cluster is None or cluster.deleted_at is not None and not deleted_ok:
        return None

    # One exception to normal project scoping is users created by the
    # clusters in the cluster_user_project_id
    if (tenant_safe and cluster is not None and context is not None and
        context.tenant_id not in (cluster.tenant,
                                  cluster.cluster_user_project_id)):
        return None
    return cluster


def cluster_get_by_name(context, cluster_name):
    query = soft_delete_aware_query(context, models.Cluster).\
        filter(sqlalchemy.or_(
            models.Cluster.tenant == context.tenant_id,
            models.Cluster.cluster_user_project_id == context.tenant_id
        )).\
        filter_by(name=cluster_name)
    return query.first()


def _query_cluster_get_all(context, tenant_safe=True, show_deleted=False,
                           show_nested=False):
    query = soft_delete_aware_query(context, models.Cluster,
                                    show_deleted=show_deleted)

    if show_nested:
        query = query.filter_by(backup=False)
    else:
        query = query.filter_by(owner_id=None)

    if tenant_safe:
        query = query.filter_by(tenant=context.tenant_id)
    return query


def _paginate_query(context, query, model, limit=None, sort_keys=None,
                    marker=None, sort_dir=None):
    default_sort_keys = ['created_at']
    if not sort_keys:
        sort_keys = default_sort_keys
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
        raise exception.Invalid(reason=exc.message)
    return query


def _filter_and_page_query(context, query, limit=None, sort_keys=None,
                           marker=None, sort_dir=None, filters=None):
    if filters is None:
        filters = {}

    sort_key_map = {
        rpc_api.CLUSTER_NAME: models.Cluster.name.key,
        rpc_api.CLUSTER_STATUS: models.Cluster.status.key,
        rpc_api.CLUSTER_CREATED_TIME: models.Cluster.created_time.key,
        rpc_api.CLUSTER_UPDATED_TIME: models.Cluster.updated_time.key,
    }
    keys = _get_sort_keys(sort_keys, sort_key_map)

    query = db_filters.exact_filter(query, models.Cluster, filters)
    return _paginate_query(context, query, models.Cluster, limit,
                           keys, marker, sort_dir)


def cluster_get_all(context, limit=None, sort_keys=None, marker=None,
                    sort_dir=None, filters=None, tenant_safe=True,
                    show_deleted=False, show_nested=False):
    query = _query_cluster_get_all(context, tenant_safe,
                                   show_deleted=show_deleted,
                                   show_nested=show_nested)
    return _filter_and_page_query(context, query, limit, sort_keys,
                                  marker, sort_dir, filters).all()


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
        raise exception.NotFound(i18n._('Attempt to update a cluster with id: '
                                 '%(id)s %(msg)s') % {
                                     'id': cluster_id,
                                     'msg': 'that does not exist'})

    cluster.update(values)
    cluster.save(_session(context))


def cluster_delete(context, cluster_id):
    s = cluster_get(context, cluster_id)
    if not s:
        raise exception.NotFound(i18n._('Attempt to delete a cluster with id '
                                   '"%s" that does not exist') % cluster_id)
    session = orm_session.Session.object_session(s)

    for r in s.nodes:
        session.delete(r)

    s.soft_delete(session=session)
    session.flush()


# Nodes
def node_create(context, values):
    node = models.Node()
    node.update(values)
    node.save(_session(context))
    return node


def node_get(context, node_id):
    node = model_query(context, models.Node).get(node_id)
    if not node:
        raise exception.NotFound(
            i18n._('Node with id "%s" not found') % node_id)
    return node


def node_get_all(context):
    nodes = model_query(context, models.Node).all()

    if not nodes:
        raise exception.NotFound(_('No nodes were found'))
    return nodes


def node_get_all_by_cluster(context, cluster_id):
    nodes = model_query(context, models.Node).\
        filter_by(cluster_id=cluster_id).\
        options(orm.joinedload("data")).all()

    if not nodes:
        raise exception.NotFound(_("no nodes for cluster_id %s were found")
                                 % cluster_id)
    return dict((node.name, node) for node in nodes)


def node_get_by_name_and_cluster(context, name, cluster_id):
    node = model_query(context, models.Node).filter_by(name=name).\
        filter_by(cluster_id=cluster_id).\
        options(orm.joinedload("data")).first()
    return node


def node_get_by_physical_id(context, physical_id):
    nodes = (model_query(context, models.Node)
             .filter_by(physical_id=physical_id)
             .all())

    for node in nodes:
        if context is None:
            return node
        if context.tenant_id in (node.cluster.tenant,
                                 node.cluster.cluster_user_project_id):
            return node
    return None


# Locks
def cluster_lock_create(cluster_id, engine_id):
    session = get_session()
    with session.begin():
        lock = session.query(models.ClusterLock).get(cluster_id)
        if lock is not None:
            return lock.engine_id
        session.add(models.ClusterLock(cluster_id=cluster_id,
                                       engine_id=engine_id))


def cluster_lock_steal(cluster_id, old_engine_id, new_engine_id):
    session = get_session()
    with session.begin():
        lock = session.query(models.ClusterLock).get(cluster_id)
        rows_affected = session.query(models.ClusterLock).\
            filter_by(cluster_id=cluster_id, engine_id=old_engine_id).\
            update({"engine_id": new_engine_id})
    if not rows_affected:
        return lock.engine_id if lock is not None else True


def cluster_lock_release(cluster_id, engine_id):
    session = get_session()
    with session.begin():
        rows_affected = session.query(models.ClusterLock).\
            filter_by(cluster_id=cluster_id, engine_id=engine_id).\
            delete()
    if not rows_affected:
        return True

# Profiles 
def profile_create(context, values):
    profile = models.Profile()
    profile.update(values)
    profile.save(_session(context))
    return profile 


def profile_get(context, profile_id):
    profile = model_query(context, models.Profile).get(profile_id)
    if not profile:
        raise exception.NotFound(
            _('Profile with id "%s" not found') % profile_id)
    return profile


def profile_get_all(context):
    profiles = model_query(context, models.Profile).all()

    if not profiles:
        raise exception.NotFound(_('No profiles were found'))
    return profiles 


# Events
def event_create(context, values):
    if 'cluster_id' in values and cfg.CONF.max_events_per_cluster:
        cluster_id = values['cluster_id']
        event_count = event_count_all_by_cluster(context, cluster_id).count()
        if (event_count >= cfg.CONF.max_events_per_cluster):
            # prune events
            batch_size = cfg.CONF.event_purge_batch_size
            _delete_event_rows(context, cluster_id, batch_size)

    event = models.Event()
    event.update(values)
    event.save(_session(context))
    return event


def event_get(context, event_id):
    event = model_query(context, models.Event).get(event_id)
    return event


def event_get_all(context):
    clusters = soft_delete_aware_query(context, models.Cluster)
    cluster_ids = [cluster.id for cluster in clusters]
    events = model_query(context, models.Event).\
        filter(models.Event.cluster_id.in_(cluster_ids)).all()
    return events


def _events_paginate_query(context, query, model, limit=None, sort_keys=None,
                           marker=None, sort_dir=None):
    default_sort_keys = ['created_at']
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
        model_marker = model_query(context, model).filter_by(uuid=marker).\
            first()
    try:
        query = utils.paginate_query(query, model, limit, sort_keys,
                                     model_marker, sort_dir)
    except utils.InvalidSortKey as exc:
        raise exception.Invalid(reason=exc.message)

    return query


def _events_filter_and_page_query(context, query,
                                  limit=None, marker=None,
                                  sort_keys=None, sort_dir=None,
                                  filters=None):
    if filters is None:
        filters = {}

    sort_key_map = {rpc_api.EVENT_TIMESTAMP: models.Event.created_at.key,
                    rpc_api.EVENT_RES_TYPE: models.Event.node_type.key}
    keys = _get_sort_keys(sort_keys, sort_key_map)

    query = db_filters.exact_filter(query, models.Event, filters)

    return _events_paginate_query(context, query, models.Event, limit,
                                  keys, marker, sort_dir)


def event_count_all_by_cluster(context, cid):
    query = model_query(context, models.Event).filter_by(cluster_id=cid)
    return query


def event_get_all_by_tenant(context, limit=None, marker=None,
                            sort_keys=None, sort_dir=None, filters=None):
    query = model_query(context, models.Event)
    query = db_filters.exact_filter(query, models.Event, filters)
    query = query.join(models.Event.cluster).\
        filter_by(tenant=context.tenant_id).filter_by(deleted_at=None)
    filters = None
    return _events_filter_and_page_query(context, query, limit, marker,
                                         sort_keys, sort_dir, filters).all()


def event_get_all_by_cluster(context, cluster_id, limit=None, marker=None,
                             sort_keys=None, sort_dir=None, filters=None):
    query = event_count_all_by_cluster(context, cluster_id)
    return _events_filter_and_page_query(context, query, limit, marker,
                                         sort_keys, sort_dir, filters).all()


def _delete_event_rows(context, cluster_id, limit):
    # MySQL does not support LIMIT in subqueries,
    # sqlite does not support JOIN in DELETE.
    # So we must manually supply the IN() values.
    # pgsql SHOULD work with the pure DELETE/JOIN below but that must be
    # confirmed via integration tests.
    query = event_count_all_by_cluster(context, cluster_id)
    session = _session(context)
    ids = [r.id for r in query.order_by(models.Event.id).limit(limit).all()]
    q = session.query(models.Event).filter(models.Event.id.in_(ids))
    return q.delete(synchronize_session='fetch')


def purge_deleted(age, granularity='days'):
    try:
        age = int(age)
    except ValueError:
        raise exception.Error(_("age should be an integer"))
    if age < 0:
        raise exception.Error(_("age should be a positive integer"))

    if granularity not in ('days', 'hours', 'minutes', 'seconds'):
        raise exception.Error(
            _("granularity should be days, hours, minutes, or seconds"))

    if granularity == 'days':
        age = age * 86400
    elif granularity == 'hours':
        age = age * 3600
    elif granularity == 'minutes':
        age = age * 60

    time_line = datetime.datetime.now() - datetime.timedelta(seconds=age)
    engine = get_engine()
    meta = sqlalchemy.MetaData()
    meta.bind = engine

    cluster = sqlalchemy.Table('cluster', meta, autoload=True)
    event = sqlalchemy.Table('event', meta, autoload=True)
    raw_template = sqlalchemy.Table('raw_template', meta, autoload=True)
    user_creds = sqlalchemy.Table('user_creds', meta, autoload=True)

    stmt = sqlalchemy.select([cluster.c.id,
                              cluster.c.raw_template_id,
                              cluster.c.user_creds_id]).\
        where(cluster.c.deleted_at < time_line)
    deleted_clusters = engine.execute(stmt)

    for s in deleted_clusters:
        event_del = event.delete().where(event.c.cluster_id == s[0])
        engine.execute(event_del)
        cluster_del = cluster.delete().where(cluster.c.id == s[0])
        engine.execute(cluster_del)
        raw_template_del = raw_template.delete().\
            where(raw_template.c.id == s[1])
        engine.execute(raw_template_del)
        user_creds_del = user_creds.delete().where(user_creds.c.id == s[2])
        engine.execute(user_creds_del)


# User credentials
def _encrypt(value):
    if value is not None:
        return crypt.encrypt(value.encode('utf-8'))
    else:
        return None, None


def _decrypt(enc_value, method):
    if method is None:
        return None
    decryptor = getattr(crypt, method)
    value = decryptor(enc_value)
    if value is not None:
        return unicode(value, 'utf-8')


def user_creds_create(context):
    values = context.to_dict()
    user_creds_ref = models.UserCreds()
    if values.get('trust_id'):
        method, trust_id = _encrypt(values.get('trust_id'))
        user_creds_ref.trust_id = trust_id
        user_creds_ref.decrypt_method = method
        user_creds_ref.trustor_user_id = values.get('trustor_user_id')
        user_creds_ref.username = None
        user_creds_ref.password = None
        user_creds_ref.tenant = values.get('tenant')
        user_creds_ref.tenant_id = values.get('tenant_id')
    else:
        user_creds_ref.update(values)
        method, password = _encrypt(values['password'])
        user_creds_ref.password = password
        user_creds_ref.decrypt_method = method
    user_creds_ref.save(_session(context))
    return user_creds_ref


def user_creds_get(user_creds_id):
    db_result = model_query(None, models.UserCreds).get(user_creds_id)
    if db_result is None:
        return None
    # Return a dict copy of db results, do not decrypt details into db_result
    # or it can be committed back to the DB in decrypted form
    result = dict(db_result)
    del result['decrypt_method']
    result['password'] = _decrypt(result['password'], db_result.decrypt_method)
    result['trust_id'] = _decrypt(result['trust_id'], db_result.decrypt_method)
    return result


def user_creds_delete(context, user_creds_id):
    creds = model_query(context, models.UserCreds).get(user_creds_id)
    if not creds:
        raise exception.NotFound(
            _('Attempt to delete user creds with id '
              '%(id)s that does not exist') % {'id': user_creds_id})
    session = orm_session.Session.object_session(creds)
    session.delete(creds)
    session.flush()


# Utils
def db_sync(engine, version=None):
    """Migrate the database to `version` or the most recent version."""
    return migration.db_sync(engine, version=version)


def db_version(engine):
    """Display the current database version."""
    return migration.db_version(engine)
