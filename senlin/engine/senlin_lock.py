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

import contextlib
import uuid

from oslo import messaging
from oslo_config import cfg
from oslo_utils import excutils

from senlin.common import exception
from senlin.common.i18n import _LE
from senlin.common.i18n import _LI
from senlin.common.i18n import _LW
from senlin.common import messaging as rpc_messaging
from senlin.db import api as db_api
from senlin.engine import dispatcher
from senlin.engine import scheduler
from senlin.openstack.common import log as logging

CONF = cfg.CONF

CONF.import_opt('engine_life_check_timeout', 'senlin.common.config')
CONF.import_opt('lock_retry_times', 'senlin.common.config')
CONF.import_opt('lock_retry_interval', 'senlin.common.config')

LOG = logging.getLogger(__name__)


class BaseLock(object):
    '''Base class for locks.'''

    def __init__(self, context, target, engine_id):
        self.context = context
        self.target = target
        self.target_type = 'target'
        self.engine_id = engine_id
        self.listener = None

    @staticmethod
    def engine_alive(context, engine_id):
        client = rpc_messaging.get_rpc_client(version='1.0', topic=engine_id)
        client_context = client.prepare(
            timeout=cfg.CONF.engine_life_check_timeout)
        try:
            return client_context.call(context, 'listening')
        except messaging.MessagingTimeout:
            return False

    @staticmethod
    def generate_engine_id():
        return str(uuid.uuid4())

    def try_acquire(self):
        '''Try to acquire a lock for target.

        It won't raise an ActionInProgress exception or try to steal lock.
        '''
        return self.lock_create(self.target.id, self.engine_id)

    def acquire(self, retry=True):
        '''Acquire a lock on the target.

        :param retry: When True, retry if lock was released while stealing.
        :type retry: boolean
        '''

        lock_engine_id = self.lock_create(self.target.id, self.engine_id)
        if lock_engine_id is None:
            LOG.debug("Engine %(engine)s acquired lock on %(target_type)s "
                      "%(target)s" % {'engine': self.engine_id,
                                      'target_type': self.target_type,
                                      'target': self.target.id})
            return

        if lock_engine_id == self.engine_id or \
           self.engine_alive(self.context, lock_engine_id):
            LOG.debug("Lock on %(target_type)s %(target)s is owned by engine "
                      "%(engine)s" % {'target_type': self.target_type,
                                      'target': self.target.id,
                                      'engine': lock_engine_id})
            raise exception.ActionInProgress(target_name=self.target.name,
                                             action=self.target.status)
        else:
            LOG.info(_LI("Stale lock detected on %(target_type)s %(target)s. "
                         "Engine %(engine)s will attempt to steal the lock"),
                     {'target_type': self.target_type,
                      'target': self.target.id,
                      'engine': self.engine_id})

            result = self.lock_steal(self.target.id, lock_engine_id,
                                     self.engine_id)

            if result is None:
                LOG.info(_LI("Engine %(engine)s successfully stole the lock "
                             "on %(target_type)s %(target)s"),
                         {'engine': self.engine_id,
                          'target_type': self.target_type,
                          'target': self.target.id})
                return
            elif result is True:
                if retry:
                    LOG.info(_LI("The lock on %(target_type)s %(target)s was "
                                 "released while engine %(engine)s was "
                                 "stealing it. Trying again"),
                             {'target_type': self.target_type,
                              'target': self.target.id,
                              'engine': self.engine_id})
                    return self.acquire(retry=False)
            else:
                new_lock_engine_id = result
                LOG.info(_LI("Failed to steal lock on %(target_type)s "
                             "%(target)s. Engine %(engine)s stole the "
                             "lock already"), {'target_type': self.target_type,
                                               'target': self.target.id,
                                               'engine': new_lock_engine_id})

            raise exception.ActionInProgress(
                target_name=self.target.name, action=self.target.status)

    def release(self, target_id):
        """Release a target lock."""
        # Only the engine that owns the lock will be releasing it.
        result = self.lock_release(target_id, self.engine_id)
        if result is True:
            LOG.warn(_LW("Lock was already released on %(target_type) "
                         "%(target)s!"), {'target_type': self.target_type,
                                          'target': target_id})
        else:
            LOG.debug("Engine %(engine)s released lock on %(target_type)s "
                      "%(target)s" % {'engine': self.engine_id,
                                      'target_type': self.target_type,
                                      'target': target_id})

    @contextlib.contextmanager
    def thread_lock(self, target_id):
        '''Acquire a lock and release it only if there is an exception.

        The release method still needs to be scheduled to be run at the
        end of the thread using the Thread.link method.
        '''
        try:
            self.acquire()
            yield
        except:  # noqa
            with excutils.save_and_reraise_exception():
                self.release(target_id)

    @contextlib.contextmanager
    def try_thread_lock(self, target_id):
        '''Acquire the lock using try_acquire.

        Similar to thread_lock, but acquire the lock using try_acquire
        and only release it upon any exception after a successful
        acquisition.
        '''

        result = None
        try:
            result = self.try_acquire()
            yield result
        except:  # noqa
            if result is None:  # Lock was successfully acquired
                with excutils.save_and_reraise_exception():
                    self.release(target_id)
            raise


def cluster_lock_acquire(cluster_id, action, steal_lock=False):
    '''Try to lock the specified cluster

    :param steal_lock: set to True to cancel current action that owns the
                       lock, if any.
    '''
    # Step 1: try lock the cluster - if the returned owner_id is the
    #         action id, it was a success

    owner_id = db_api.cluster_lock_acquire(cluster_id, action.id)
    if owner_id == action.id:
        return True

    # Step 2: retry using global configuration options
    retries = cfg.CONF.lock_retry_times
    retry_interval = cfg.CONF.lock_retry_interval

    while retries > 0:
        scheduler.sleep(retry_interval)
        owner_id = db_api.cluster_lock_acquire(cluster_id, action.id)
        if owner_id == action.id:
            return True
        retries = retries - 1

    # Step 3: Last resort is 'stealing', only needed when retry failed
    if steal_lock:
        # Cancel the action that currently owns the lock
        dispatcher.notify(action.context, dispatcher.CANCEL_ACTION,
                          None, action_id=owner_id)

        owner_id = db_api.cluster_lock_acquire(cluster_id, action.id)
        while owner_id != action.id:
            if action.is_timeout():
                LOG.error(_LE('Cluster lock timeout for action %(name)s '
                              '[%(id)s]'), {'name': action.action,
                                            'id': action.id})
                return False

            scheduler.reschedule(action)
            owner_id = db_api.cluster_lock_acquire(cluster_id, action.id)

        return True

    LOG.error(_LE('Cluster is already locked by action %(old)s, '
                  'action %(new)s failed grabbing the lock') % {
                      'old': owner_id, 'new': action.id})

    return False


def cluster_lock_release(cluster_id, action_id):
    db_api.cluster_lock_release(cluster_id, action_id)
