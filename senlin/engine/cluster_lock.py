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

from oslo.config import cfg
from oslo import messaging
from oslo.utils import excutils

from senlin.common import exception
from senlin.common.i18n import _LI
from senlin.common.i18n import _LW
from senlin.common import messaging as rpc_messaging
# Just for test, need be repalced with real db api implementation
from senlin.db import api_sim as db_api
from senlin.openstack.common import log as logging

cfg.CONF.import_opt('engine_life_check_timeout', 'senlin.common.config')

LOG = logging.getLogger(__name__)


class ClusterLock(object):
    def __init__(self, context, cluster, engine_id):
        self.context = context
        self.cluster = cluster
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
        """
        Try to acquire a cluster lock, but don't raise an ActionInProgress
        exception or try to steal lock.
        """
        return db_api.cluster_lock_create(self.cluster.id, self.engine_id)

    def acquire(self, retry=True):
        """
        Acquire a lock on the cluster.

        :param retry: When True, retry if lock was released while stealing.
        :type retry: boolean
        """
        lock_engine_id = db_api.cluster_lock_create(self.cluster.id,
                                                  self.engine_id)
        if lock_engine_id is None:
            LOG.debug("Engine %(engine)s acquired lock on cluster "
                      "%(cluster)s" % {'engine': self.engine_id,
                                     'cluster': self.cluster.id})
            return

        if lock_engine_id == self.engine_id or \
           self.engine_alive(self.context, lock_engine_id):
            LOG.debug("Lock on cluster %(cluster)s is owned by engine "
                      "%(engine)s" % {'cluster': self.cluster.id,
                                      'engine': lock_engine_id})
            raise exception.ActionInProgress(cluster_name=self.cluster.name,
                                             action=self.cluster.action)
        else:
            LOG.info(_LI("Stale lock detected on cluster %(cluster)s.  Engine "
                         "%(cluster)s will attempt to steal the lock"),
                     {'cluster': self.cluster.id, 'engine': self.engine_id})

            result = db_api.cluster_lock_steal(self.cluster.id, lock_engine_id,
                                             self.engine_id)

            if result is None:
                LOG.info(_LI("Engine %(engine)s successfully stole the lock "
                             "on cluster %(cluster)s"),
                         {'engine': self.engine_id,
                          'cluster': self.cluster.id})
                return
            elif result is True:
                if retry:
                    LOG.info(_LI("The lock on cluster %(cluster)s was released "
                                 "while engine %(engine)s was stealing it. "
                                 "Trying again"), {'cluster': self.cluster.id,
                                                   'engine': self.engine_id})
                    return self.acquire(retry=False)
            else:
                new_lock_engine_id = result
                LOG.info(_LI("Failed to steal lock on cluster %(cluster)s. "
                             "Engine %(engine)s stole the lock first"),
                         {'cluster': self.cluster.id,
                          'engine': new_lock_engine_id})

            raise exception.ActionInProgress(
                cluster_name=self.cluster.name, action=self.cluster.action)

    def release(self, cluster_id):
        """Release a cluster lock."""
        # Only the engine that owns the lock will be releasing it.
        result = db_api.cluster_lock_release(cluster_id, self.engine_id)
        if result is True:
            LOG.warn(_LW("Lock was already released on cluster %s!"), cluster_id)
        else:
            LOG.debug("Engine %(engine)s released lock on cluster "
                      "%(cluster)s" % {'engine': self.engine_id,
                                     'cluster': cluster_id})

    @contextlib.contextmanager
    def thread_lock(self, cluster_id):
        """
        Acquire a lock and release it only if there is an exception.  The
        release method still needs to be scheduled to be run at the
        end of the thread using the Thread.link method.
        """
        try:
            self.acquire()
            yield
        except:  # noqa
            with excutils.save_and_reraise_exception():
                self.release(cluster_id)

    @contextlib.contextmanager
    def try_thread_lock(self, cluster_id):
        """
        Similar to thread_lock, but acquire the lock using try_acquire
        and only release it upon any exception after a successful
        acquisition.
        """
        result = None
        try:
            result = self.try_acquire()
            yield result
        except:  # noqa
            if result is None:  # Lock was successfully acquired
                with excutils.save_and_reraise_exception():
                    self.release(cluster_id)
            raise
