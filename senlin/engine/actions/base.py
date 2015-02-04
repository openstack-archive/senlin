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

import datetime
import six
import time

from oslo_config import cfg

from senlin.common import context as req_context
from senlin.common import exception
from senlin.common.i18n import _
from senlin.common.i18n import _LI
from senlin.db import api as db_api
from senlin.engine import dispatcher
from senlin.openstack.common import log as logging
from senlin.policies import base as policies

wallclock = time.time
LOG = logging.getLogger(__name__)


class Action(object):
    '''An action can be performed on a cluster or a node of a cluster.'''

    RETURNS = (
        RES_OK, RES_ERROR, RES_RETRY, RES_CANCEL, RES_TIMEOUT,
    ) = (
        'OK', 'ERROR', 'RETRY', 'CANCEL', 'TIMEOUT',
    )

    # Action status definitions:
    #  INIT:      Not ready to be executed because fields are being modified,
    #             or dependency with other actions are being analyzed.
    #  READY:     Initialized and ready to be executed by a worker.
    #  RUNNING:   Being executed by a worker thread.
    #  SUCCEEDED: Completed with success.
    #  FAILED:    Completed with failure.
    #  CANCELLED: Action cancelled because worker thread was cancelled.
    STATUSES = (
        INIT, WAITING, READY, RUNNING,
        SUCCEEDED, FAILED, CANCELLED
    ) = (
        'INIT', 'WAITING', 'READY', 'RUNNING',
        'SUCCEEDED', 'FAILED', 'CANCELLED',
    )

    # Signal commands
    COMMANDS = (
        SIG_CANCEL, SIG_SUSPEND, SIG_RESUME,
    ) = (
        'CANCEL', 'SUSPEND', 'RESUME',
    )

    def __new__(cls, context, action, **kwargs):
        if (cls != Action):
            return super(Action, cls).__new__(cls)

        target_type = action.split('_')[0]
        if target_type == 'CLUSTER':
            from senlin.engine.actions import cluster_action
            ActionClass = cluster_action.ClusterAction
        elif target_type == 'NODE':
            from senlin.engine.actions import node_action
            ActionClass = node_action.NodeAction
        elif target_type == 'POLICY':
            from senlin.engine.actions import policy_action
            ActionClass = policy_action.PolicyAction
        else:
            from senlin.engine.actions import custom_action
            ActionClass = custom_action.CustomAction

        return super(Action, cls).__new__(ActionClass)

    def __init__(self, context, action, **kwargs):
        # context will be persisted into database so that any worker thread
        # can pick the action up and execute it on behalf of the initiator
        if action not in self.ACTIONS:
            raise exception.ActionNotSupported(
                action=action, object=_('target %s') % self.target)

        self.id = kwargs.get('id', '')
        self.name = kwargs.get('name', '')
        self.context = req_context.RequestContext.from_dict(context.to_dict())

        self.description = kwargs.get('description', '')

        # Target is the ID of a cluster, a node, a profile
        self.target = kwargs.get('target', None)
        if self.target is None:
            raise exception.ActionMissingTarget(action=action)

        self.action = action

        # Why this action is fired, it can be a UUID of another action
        self.cause = kwargs.get('cause', '')

        # Owner can be an UUID format ID for the worker that is currently
        # working on the action.  It also serves as a lock.
        self.owner = kwargs.get('owner', None)

        # An action may need to be executed repeatitively, interval is the
        # time in seconds between two consequtive execution.
        # A value of -1 indicates that this action is only to be executed once
        self.interval = kwargs.get('interval', -1)

        # Start time can be an absolute time or a time relative to another
        # action. E.g.
        #   - '2014-12-18 08:41:39.908569'
        #   - 'AFTER: 57292917-af90-4c45-9457-34777d939d4d'
        #   - 'WHEN: 0265f93b-b1d7-421f-b5ad-cb83de2f559d'
        self.start_time = kwargs.get('start_time', None)
        self.end_time = kwargs.get('end_time', None)

        # Timeout is a placeholder in case some actions may linger too long
        self.timeout = kwargs.get('timeout', cfg.CONF.default_action_timeout)

        # Return code, useful when action is not automatically deleted
        # after execution
        self.status = kwargs.get('status', self.INIT)
        self.status_reason = kwargs.get('status_reason', '')

        # All parameters are passed in using keyword arguments which is
        # a dictionary stored as JSON in DB
        self.inputs = kwargs.get('inputs', {})
        self.outputs = kwargs.get('outputs', {})

        # Dependency with other actions
        self.depends_on = kwargs.get('depends_on', [])
        self.depended_by = kwargs.get('depended_by', [])

        self.created_time = kwargs.get('created_time', None)
        self.updated_time = kwargs.get('updated_time', None)
        self.deleted_time = kwargs.get('deleted_time', None)

    def store(self, context):
        '''Store the action record into database table.'''

        values = {
            'name': self.name,
            'context': self.context.to_dict(),
            'target': self.target,
            'action': self.action,
            'cause': self.cause,
            'owner': self.owner,
            'interval': self.interval,
            'start_time': self.start_time,
            'end_time': self.end_time,
            'timeout': self.timeout,
            'status': self.status,
            'status_reason': self.status_reason,
            'inputs': self.inputs,
            'outputs': self.outputs,
            'depends_on': self.depends_on,
            'depended_by': self.depended_by,
            'created_time': datetime.datetime.utcnow(),
            'updated_time': self.updated_time,
            'deleted_time': self.deleted_time,
        }

        if self.id:
            values['updated_time'] = datetime.datetime.utcnow()
            action = db_api.action_update(context, values)
        else:
            values['created_time'] = datetime.datetime.utcnow()
            action = db_api.action_create(context, values)

        self.id = action.id
        return self.id

    @classmethod
    def _from_db_record(cls, record):
        '''Construct a action object from database record.

        :param context: the context used for DB operations;
        :param record: a DB action object that contains all fields.
        '''
        context = req_context.RequestContext.from_dict(record.context)
        kwargs = {
            'id': record.id,
            'name': record.name,
            'target': record.target,
            'cause': record.cause,
            'owner': record.owner,
            'interval': record.interval,
            'start_time': record.start_time,
            'end_time': record.end_time,
            'timeout': record.timeout,
            'status': record.status,
            'status_reason': record.status_reason,
            'inputs': record.inputs,
            'outputs': record.outputs,
            'depends_on': record.depends_on,
            'depended_by': record.depended_by,
            'deleted_time': record.deleted_time,
        }

        return cls(context, record.action, **kwargs)

    @classmethod
    def load(cls, context, action_id):
        '''Retrieve an action from database.'''

        action = db_api.action_get(context, action_id)
        if action is None:
            msg = _('No action with id "%s" exists') % action_id
            raise exception.NotFound(msg)

        return cls._from_db_record(action)

    @classmethod
    def load_all(cls, context, filters=None, limit=None, marker=None,
                 sort_keys=None, sort_dir=None, show_deleted=False):
        '''Retrieve all actions of from database.'''

        records = db_api.action_get_all(context, filters=filters,
                                        limit=limit, marker=marker,
                                        sort_keys=sort_keys,
                                        sort_dir=sort_dir,
                                        show_deleted=show_deleted)

        for record in records:
            yield cls._from_db_record(record)

    @classmethod
    def delete(cls, context, action_id, force=False):
        db_api.action_delete(context, action_id, force)

    def signal(self, context, cmd):
        '''Cancel an action execution progress.'''
        db_api.action_signal(context, self.id, cmd)

    def execute(self, **kwargs):
        '''Execute the action.

        In theory, the action encapsulates all information needed for
        execution.  'kwargs' may specify additional parameters.
        :param kwargs: additional parameters that may override the default
                       properties stored in the action record.
        '''
        return NotImplemented

    def set_status(self, result):
        '''Set action status based on return value from execute.'''

        timestamp = wallclock()

        if result == self.RES_OK:
            status = self.SUCCEEDED
            msg = _LI('Action %(name)s [%(id)s] completed with %(status)s.')
            db_api.action_mark_succeeded(self.context, self.id, timestamp)

        elif result == self.RES_ERROR or result == self.RES_TIMEOUT:
            status = self.FAILED
            msg = _LI('Action %(name)s [%(id)s] failed with ERROR.')
            db_api.action_mark_failed(self.context, self.id, timestamp,
                                      reason=result)

        elif result == self.RES_TIMEOUT:
            status = self.FAILED
            msg = _LI('Action %(name)s [%(id)s] failed with TIMEOUT.')
            db_api.action_mark_failed(self.context, self.id, timestamp,
                                      reason=result)

        elif result == self.RES_CANCEL:
            status = self.CANCELLED
            msg = _LI('Action %(name)s [%(id)s] was cancelled.')
            db_api.action_mark_cancelled(self.context, self.id, timestamp)

        else:  # result == self.RES_RETRY:
            status = self.READY
            # Action failed at the moment, but can be retried
            # We abandon it and then notify other dispatchers to execute it
            db_api.action_abandon(self.context, self.id)

            # TODO(yanyan): This is dirty, we have to import dispatcher here?
            dispatcher.notify(self.context, dispatcher.Dispatcher.NEW_ACTION,
                              None, action_id=self.id)
            msg = _LI('Action %(name)s [%(id)s] aborted with RETRY.')

        LOG.info(msg, {'name': self.action, 'id': self.id, 'status': status})
        self.status = status

    def get_status(self):
        action = db_api.action_get(self.context, self.id)
        self.status = action.status
        return action.status

    def is_timeout(self):
        time_lapse = wallclock() - self.start_time
        return time_lapse > self.timeout

    def _check_signal(self):
        # Check timeout first, if true, return timeout message
        if self.timeout is not None and self.is_timeout():
            LOG.debug('Action %s run timeout' % self.id)
            return self.RES_TIMEOUT

        result = db_api.action_signal_query(self.context, self.id)
        return result

    def is_cancelled(self):
        return self._check_signal() == self.SIG_CANCEL

    def is_suspended(self):
        return self._check_signal() == self.SIG_SUSPEND

    def is_resumed(self):
        return self._check_signal() == self.SIG_RESUME

    def policy_check(self, cluster_id, target):
        """Check all policies attached to cluster and give result.

        :param target: A tuple of ('when', action_name)
        """
        # Initialize an empty dict for policy check result
        data = {}
        data['result'] = policies.Policy.CHECK_SUCCEED

        # Get list of policy IDs attached to cluster
        policy_list = db_api.cluster_get_policies(self.context, cluster_id)

        policy_ids = [p.id for p in policy_list if p.enabled]
        policy_check_list = []
        for pid in policy_ids:
            policy = policies.Policy.load(self.context, pid)
            for t in policy.TARGET:
                if t == (target, self.action):
                    policy_check_list.append(policy)
                    break

        # No policy need to check, return data
        if len(policy_check_list) == 0:
            return data

        while len(policy_check_list) != 0:
            # Check all policies and collect return data
            policy = policy_check_list[0]
            if target == 'BEFORE':
                data = policy.pre_op(self.cluster_id, self.action, data)
            elif target == 'AFTER':
                data = policy.post_op(self.cluster_id, self.action, data)
            else:
                data = data

            if data['result'] == policies.Policy.CHECK_FAIL:
                # Policy check failed, return
                return False
            elif data['result'] == policies.Policy.CHECK_RETRY:
                # Policy check need extra input, move
                # it to the end of policy list and
                # wait for retry
                policy_check_list.remove(policy)
                policy_check_list.append(policy)
            else:
                # Policy check succeeded
                policy_check_list.remove(policy)

            # TODO(anyone): add retry limitation check to
            # prevent endless loop on single policy

        return data

    def to_dict(self):
        action_dict = {
            'id': self.id,
            'name': self.name,
            'action': self.action,
            'context': self.context.to_dict(),
            'target': self.target,
            'cause': self.cause,
            'owner': self.owner,
            'interval': self.interval,
            'start_time': self.start_time,
            'end_time': self.end_time,
            'interval': self.interval,
            'timeout': self.timeout,
            'status': self.status,
            'status_reason': self.status_reason,
            'inputs': self.inputs,
            'outputs': self.outputs,
            'depends_on': self.depends_on,
            'depended_by': self.depended_by,
            'deleted_time': self.deleted_time,
        }
        return action_dict

    @classmethod
    def from_dict(cls, context=None, **kwargs):
        return cls(context=context, **kwargs)


def ActionProc(context, action_id, worker_id):
    '''Action process.'''

    # Step 1: lock the action for execution
    timestamp = wallclock()
    result = db_api.action_acquire(context, action_id, worker_id, timestamp)
    if result is None:
        LOG.debug(_('Failed locking action "%s" for execution'), action_id)
        return False

    # Step 2: materialize the action object
    action = Action.load(context, action_id)

    LOG.info(_LI('Action %(name)s [%(id)s] started'),
             {'name': six.text_type(action.action), 'id': action.id})

    try:
        # Step 3: execute the action
        result = action.execute()
    except Exception as ex:
        # We catch exception here to make sure the following logics are
        # executed.
        LOG.error(_('Exception occurred in action execution: %s'),
                  six.text_type(ex))
        result = action.RES_ERROR
    finally:
        # NOTE: locks on action is eventually released here by status update
        action.set_status(result)
