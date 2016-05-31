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

from oslo_config import cfg
from oslo_log import log as logging
from oslo_utils import timeutils
import time

from senlin.common.i18n import _
from senlin.common.i18n import _LE
from senlin.common.i18n import _LI
from senlin.engine import scheduler
from senlin.objects import action as ao
from senlin.objects import cluster_lock as cl_obj
from senlin.objects import node_lock as nl_obj
from senlin.objects import service as service_obj

CONF = cfg.CONF

CONF.import_opt('lock_retry_times', 'senlin.common.config')
CONF.import_opt('lock_retry_interval', 'senlin.common.config')

LOG = logging.getLogger(__name__)

LOCK_SCOPES = (
    CLUSTER_SCOPE, NODE_SCOPE,
) = (
    -1, 1,
)


def is_engine_dead(ctx, engine_id, period_time=None):
    # if engine didn't report its status for peirod_time, will consider it
    # as a dead engine.
    if period_time is None:
        period_time = 2 * CONF.periodic_interval
    eng = service_obj.Service.get(ctx, engine_id)
    if not eng:
        return True
    if timeutils.is_older_than(eng.updated_at, period_time):
        return True
    return False


def cluster_lock_acquire(context, cluster_id, action_id, engine=None,
                         scope=CLUSTER_SCOPE, forced=False):
    """Try to lock the specified cluster.

    :param cluster_id: ID of the cluster to be locked.
    :param action_id: ID of the action which wants to lock the cluster.
    :param engine: ID of the engine which wants to lock the cluster.
    :param scope: scope of lock, could be cluster wide lock, or node-wide
                  lock.
    :param forced: set to True to cancel current action that owns the lock,
                   if any.
    :returns: True if lock is acquired, or False otherwise.
    """

    # Step 1: try lock the cluster - if the returned owner_id is the
    #         action id, it was a success
    owners = cl_obj.ClusterLock.acquire(cluster_id, action_id, scope)
    if action_id in owners:
        return True

    # Step 2: retry using global configuration options
    retries = cfg.CONF.lock_retry_times
    retry_interval = cfg.CONF.lock_retry_interval

    while retries > 0:
        scheduler.sleep(retry_interval)
        LOG.debug('Acquire lock for cluster %s again' % cluster_id)
        owners = cl_obj.ClusterLock.acquire(cluster_id, action_id, scope)
        if action_id in owners:
            return True
        retries = retries - 1

    # Step 3: Last resort is 'forced locking', only needed when retry failed
    if forced:
        owners = cl_obj.ClusterLock.steal(cluster_id, action_id)
        return action_id in owners

    # Will reach here only because scope == CLUSTER_SCOPE
    action = ao.Action.get(context, owners[0])
    if (action and action.owner and action.owner != engine and
            is_engine_dead(context, action.owner)):
        LOG.info(_LI('The cluster %(c)s is locked by dead action %(a)s, '
                     'try to steal the lock.'), {
            'c': cluster_id,
            'a': owners[0]
        })
        reason = _('Engine died when executing this action.')
        ao.Action.mark_failed(context, action.id, time.time(), reason)
        owners = cl_obj.ClusterLock.steal(cluster_id, action_id)
        return action_id in owners

    LOG.error(_LE('Cluster is already locked by action %(old)s, '
                  'action %(new)s failed grabbing the lock'),
              {'old': str(owners), 'new': action_id})

    return False


def cluster_lock_release(cluster_id, action_id, scope):
    """Release the lock on the specified cluster.

    :param cluster_id: ID of the node to be released.
    :param action_id: ID of the action that attempts to release the node.
    :param scope: The scope of the lock to be released.
    """
    return cl_obj.ClusterLock.release(cluster_id, action_id, scope)


def node_lock_acquire(context, node_id, action_id, engine=None,
                      forced=False):
    """Try to lock the specified node.

    :param context: the context used for DB operations;
    :param node_id: ID of the node to be locked.
    :param action_id: ID of the action that attempts to lock the node.
    :param engine: ID of the engine that attempts to lock the node.
    :param forced: set to True to cancel current action that owns the lock,
                   if any.
    :returns: True if lock is acquired, or False otherwise.
    """
    # Step 1: try lock the node - if the returned owner_id is the
    #         action id, it was a success
    owner = nl_obj.NodeLock.acquire(node_id, action_id)
    if action_id == owner:
        return True

    # Step 2: retry using global configuration options
    retries = cfg.CONF.lock_retry_times
    retry_interval = cfg.CONF.lock_retry_interval

    while retries > 0:
        scheduler.sleep(retry_interval)
        LOG.debug('Acquire lock for node %s again' % node_id)
        owner = nl_obj.NodeLock.acquire(node_id, action_id)
        if action_id == owner:
            return True
        retries = retries - 1

    # Step 3: Last resort is 'forced locking', only needed when retry failed
    if forced:
        owner = nl_obj.NodeLock.steal(node_id, action_id)
        return action_id == owner

    # if this node lock by dead engine
    action = ao.Action.get(context, owner)
    if (action and action.owner and action.owner != engine and
            is_engine_dead(context, action.owner)):
        LOG.info(_LI('The node %(n)s is locked by dead action %(a)s, '
                     'try to steal the lock.'), {
            'n': node_id,
            'a': owner
        })
        reason = _('Engine died when executing this action.')
        ao.Action.mark_failed(context, action.id, time.time(), reason)
        nl_obj.NodeLock.steal(node_id, action_id)
        return True

    LOG.error(_LE('Node is already locked by action %(old)s, '
                  'action %(new)s failed grabbing the lock'),
              {'old': owner, 'new': action_id})

    return False


def node_lock_release(node_id, action_id):
    """Release the lock on the specified node.

    :param node_id: ID of the node to be released.
    :param action_id: ID of the action that attempts to release the node.
    """
    return nl_obj.NodeLock.release(node_id, action_id)
