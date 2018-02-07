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

import eventlet
import random
import time

from oslo_config import cfg
from oslo_log import log as logging

from senlin.common.i18n import _
from senlin.common import utils
from senlin import objects
from senlin.objects import action as ao
from senlin.objects import cluster_lock as cl_obj
from senlin.objects import node_lock as nl_obj

CONF = cfg.CONF

CONF.import_opt('lock_retry_times', 'senlin.common.config')
CONF.import_opt('lock_retry_interval', 'senlin.common.config')

LOG = logging.getLogger(__name__)

LOCK_SCOPES = (
    CLUSTER_SCOPE, NODE_SCOPE,
) = (
    -1, 1,
)


def cluster_lock_acquire(context, cluster_id, action_id, engine=None,
                         scope=CLUSTER_SCOPE, forced=False):
    """Try to lock the specified cluster.

    :param context: the context used for DB operations.
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
    for retries in range(3):
        owners = cl_obj.ClusterLock.acquire(cluster_id, action_id, scope)
        if action_id in owners:
            return True
        eventlet.sleep(random.randrange(1, 3))

    # Step 2: Last resort is 'forced locking', only needed when retry failed
    if forced:
        owners = cl_obj.ClusterLock.steal(cluster_id, action_id)
        return action_id in owners

    # Step 3: check if the owner is a dead engine, if so, steal the lock.
    # Will reach here only because scope == CLUSTER_SCOPE
    action = ao.Action.get(context, owners[0])
    if (action and action.owner and action.owner != engine and
            utils.is_engine_dead(context, action.owner)):
        LOG.info('The cluster %(c)s is locked by dead action %(a)s, '
                 'try to steal the lock.',
                 {'c': cluster_id, 'a': owners[0]})
        dead_engine = action.owner
        owners = cl_obj.ClusterLock.steal(cluster_id, action_id)
        # Cleanse locks affected by the dead engine
        objects.Service.gc_by_engine(dead_engine)
        return action_id in owners

    lock_owners = []
    for o in owners:
        lock_owners.append(o[:8])
    LOG.warning('Cluster is already locked by action %(old)s, '
                'action %(new)s failed grabbing the lock',
                {'old': str(lock_owners), 'new': action_id[:8]})

    return False


def cluster_lock_release(cluster_id, action_id, scope):
    """Release the lock on the specified cluster.

    :param cluster_id: ID of the cluster to be released.
    :param action_id: ID of the action that attempts to release the cluster.
    :param scope: The scope of the lock to be released.
    """
    return cl_obj.ClusterLock.release(cluster_id, action_id, scope)


def node_lock_acquire(context, node_id, action_id, engine=None,
                      forced=False):
    """Try to lock the specified node.

    :param context: the context used for DB operations.
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

    # Step 2: Last resort is 'forced locking', only needed when retry failed
    if forced:
        owner = nl_obj.NodeLock.steal(node_id, action_id)
        return action_id == owner

    # Step 3: Try to steal a lock if it's owner is a dead engine.
    # if this node lock by dead engine
    action = ao.Action.get(context, owner)
    if (action and action.owner and action.owner != engine and
            utils.is_engine_dead(context, action.owner)):
        LOG.info('The node %(n)s is locked by dead action %(a)s, '
                 'try to steal the lock.',
                 {'n': node_id, 'a': owner})
        reason = _('Engine died when executing this action.')
        nl_obj.NodeLock.steal(node_id, action_id)
        ao.Action.mark_failed(context, action.id, time.time(), reason)
        return True

    LOG.error('Node is already locked by action %(old)s, '
              'action %(new)s failed grabbing the lock',
              {'old': owner, 'new': action_id})

    return False


def node_lock_release(node_id, action_id):
    """Release the lock on the specified node.

    :param node_id: ID of the node to be released.
    :param action_id: ID of the action that attempts to release the node.
    """
    return nl_obj.NodeLock.release(node_id, action_id)
