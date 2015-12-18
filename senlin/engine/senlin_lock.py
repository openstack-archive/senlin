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

# from senlin.common.i18n import _
from senlin.common.i18n import _LE
from senlin.db import api as db_api
# from senlin.engine.actions import base
from senlin.engine import dispatcher
from senlin.engine import scheduler

CONF = cfg.CONF

CONF.import_opt('lock_retry_times', 'senlin.common.config')
CONF.import_opt('lock_retry_interval', 'senlin.common.config')

LOG = logging.getLogger(__name__)

LOCK_SCOPES = (
    CLUSTER_SCOPE, NODE_SCOPE,
) = (
    -1, 1,
)


def action_on_dead_engine(context, action):
    action = db_api.action_get(context, action)
    if action and action.owner:
        return not dispatcher.notify('listening', action.owner)


def cluster_lock_acquire(context, cluster_id, action_id, scope=CLUSTER_SCOPE,
                         forced=False):
    """Try to lock the specified cluster.

    :param cluster_id: ID of the cluster to be locked.
    :param action_id: ID of the action which wants to lock the cluster.
    :param scope: scope of lock, could be cluster wide lock, or node-wide
                  lock.
    :param forced: set to True to cancel current action that owns the lock,
                   if any.
    :returns: True if lock is acquired, or False otherwise.
    """

    # Step 1: try lock the cluster - if the returned owner_id is the
    #         action id, it was a success
    owners = db_api.cluster_lock_acquire(cluster_id, action_id, scope)
    if action_id in owners:
        return True
    # Will reach here only because scope == CLUSTER_SCOPE
    # if action_on_dead_engine(context, owners[0]):
    #     LOG.debug(_('The cluster %(c)s is locked by dead action %(a)s, '
    #                 'try to steal the lock.') % {
    #         'c': cluster_id,
    #         'a': owners[0]
    #     })
    #     act = base.Action.load(context, owners[0])
    #     reason = _('Engine died when executing this action.')
    #     act.set_status(result=base.Action.RES_ERROR,
    #                    reason=reason)
    #     owners = db_api.cluster_lock_steal(cluster_id, action_id)
    #     return action_id in owners

    # Step 2: retry using global configuration options
    retries = cfg.CONF.lock_retry_times
    retry_interval = cfg.CONF.lock_retry_interval

    while retries > 0:
        scheduler.sleep(retry_interval)
        owners = db_api.cluster_lock_acquire(cluster_id, action_id, scope)
        if action_id in owners:
            return True
        retries = retries - 1

    # Step 3: Last resort is 'forced locking', only needed when retry failed
    if forced:
        owners = db_api.cluster_lock_steal(cluster_id, action_id)
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
    return db_api.cluster_lock_release(cluster_id, action_id, scope)


def node_lock_acquire(context, node_id, action_id, forced=False):
    """Try to lock the specified node.

    :param context: the context used for DB operations;
    :param node_id: ID of the node to be locked.
    :param action_id: ID of the action that attempts to lock the node.
    :param forced: set to True to cancel current action that owns the lock,
                   if any.
    :returns: True if lock is acquired, or False otherwise.
    """
    # Step 1: try lock the node - if the returned owner_id is the
    #         action id, it was a success
    owner = db_api.node_lock_acquire(node_id, action_id)
    if action_id == owner:
        return True
    # if action_on_dead_engine(context, owner):
    #     LOG.debug(_('The node %(n)s is locked by dead action %(a)s, '
    #                 'try to steal the lock.') % {
    #         'n': node_id,
    #         'a': owner
    #     })
    #     act = base.Action.load(context, owner)
    #     reason = _('Engine died when executing this action.')
    #     act.set_status(result=base.Action.RES_ERROR,
    #                    reason=reason)
    #     db_api.node_lock_steal(node_id, action_id)
    #     return True

    # Step 2: retry using global configuration options
    retries = cfg.CONF.lock_retry_times
    retry_interval = cfg.CONF.lock_retry_interval

    while retries > 0:
        scheduler.sleep(retry_interval)
        owner = db_api.node_lock_acquire(node_id, action_id)
        if action_id == owner:
            return True
        retries = retries - 1

    # Step 3: Last resort is 'forced locking', only needed when retry failed
    if forced:
        owner = db_api.node_lock_steal(node_id, action_id)
        return action_id == owner

    LOG.error(_LE('Node is already locked by action %(old)s, '
                  'action %(new)s failed grabbing the lock'),
              {'old': owner, 'new': action_id})

    return False


def node_lock_release(node_id, action_id):
    """Release the lock on the specified node.

    :param node_id: ID of the node to be released.
    :param action_id: ID of the action that attempts to release the node.
    """
    return db_api.node_lock_release(node_id, action_id)
