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
import time

from oslo_config import cfg
from oslo_log import log as logging
from oslo_utils import timeutils

from senlin.common import consts
from senlin.common import context as req_context
from senlin.common import exception
from senlin.common import utils
from senlin.engine import dispatcher
from senlin.engine import event as EVENT
from senlin.objects import action as ao
from senlin.objects import cluster_lock as cl
from senlin.objects import cluster_policy as cpo
from senlin.objects import dependency as dobj
from senlin.objects import node_lock as nl
from senlin.policies import base as policy_mod

wallclock = time.time
LOG = logging.getLogger(__name__)


class Action(object):
    """An action can be performed on a cluster or a node of a cluster."""

    RETURNS = (
        RES_OK, RES_ERROR, RES_RETRY, RES_CANCEL, RES_TIMEOUT,
        RES_LIFECYCLE_COMPLETE, RES_LIFECYCLE_HOOK_TIMEOUT,
    ) = (
        'OK', 'ERROR', 'RETRY', 'CANCEL', 'TIMEOUT', 'LIFECYCLE_COMPLETE',
        'LIFECYCLE_HOOK_TIMEOUT'
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
        INIT, WAITING, READY, RUNNING, SUSPENDED,
        SUCCEEDED, FAILED, CANCELLED, WAITING_LIFECYCLE_COMPLETION
    ) = (
        'INIT', 'WAITING', 'READY', 'RUNNING', 'SUSPENDED',
        'SUCCEEDED', 'FAILED', 'CANCELLED', 'WAITING_LIFECYCLE_COMPLETION'
    )

    # Signal commands
    COMMANDS = (
        SIG_CANCEL, SIG_SUSPEND, SIG_RESUME,
    ) = (
        'CANCEL', 'SUSPEND', 'RESUME',
    )

    def __new__(cls, target, action, ctx, **kwargs):
        if (cls != Action):
            return super(Action, cls).__new__(cls)

        target_type = action.split('_')[0]
        if target_type == 'CLUSTER':
            from senlin.engine.actions import cluster_action
            ActionClass = cluster_action.ClusterAction
        elif target_type == 'NODE':
            from senlin.engine.actions import node_action
            ActionClass = node_action.NodeAction
        else:
            from senlin.engine.actions import custom_action
            ActionClass = custom_action.CustomAction

        return super(Action, cls).__new__(ActionClass)

    def __init__(self, target, action, ctx, **kwargs):
        # context will be persisted into database so that any worker thread
        # can pick the action up and execute it on behalf of the initiator

        self.id = kwargs.get('id', None)
        self.name = kwargs.get('name', '')
        self.cluster_id = kwargs.get('cluster_id', '')

        self.context = ctx
        self.user = ctx.user_id
        self.project = ctx.project_id
        self.domain = ctx.domain_id

        self.action = action
        self.target = target

        # Why this action is fired, it can be a UUID of another action
        self.cause = kwargs.get('cause', '')

        # Owner can be an UUID format ID for the worker that is currently
        # working on the action.  It also serves as a lock.
        self.owner = kwargs.get('owner', None)

        # An action may need to be executed repeatitively, interval is the
        # time in seconds between two consecutive execution.
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

        self.created_at = kwargs.get('created_at', None)
        self.updated_at = kwargs.get('updated_at', None)

        self.data = kwargs.get('data', {})

    def store(self, ctx):
        """Store the action record into database table.

        :param ctx: An instance of the request context.
        :return: The ID of the stored object.
        """

        timestamp = timeutils.utcnow(True)

        values = {
            'name': self.name,
            'cluster_id': self.cluster_id,
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
            'created_at': self.created_at,
            'updated_at': self.updated_at,
            'data': self.data,
            'user': self.user,
            'project': self.project,
            'domain': self.domain,
        }

        if self.id:
            self.updated_at = timestamp
            values['updated_at'] = timestamp
            ao.Action.update(ctx, self.id, values)
        else:
            self.created_at = timestamp
            values['created_at'] = timestamp
            action = ao.Action.create(ctx, values)
            self.id = action.id

        return self.id

    @classmethod
    def _from_object(cls, obj):
        """Construct an action from database object.

        :param obj: a DB action object that contains all fields.
        :return: An `Action` object deserialized from the DB action object.
        """
        ctx = req_context.RequestContext.from_dict(obj.context)
        kwargs = {
            'id': obj.id,
            'name': obj.name,
            'cluster_id': obj.cluster_id,
            'cause': obj.cause,
            'owner': obj.owner,
            'interval': obj.interval,
            'start_time': obj.start_time,
            'end_time': obj.end_time,
            'timeout': obj.timeout,
            'status': obj.status,
            'status_reason': obj.status_reason,
            'inputs': obj.inputs or {},
            'outputs': obj.outputs or {},
            'created_at': obj.created_at,
            'updated_at': obj.updated_at,
            'data': obj.data,
        }

        target_type = obj.action.split('_')[0]
        if target_type == 'CLUSTER':
            from senlin.engine.actions import cluster_action
            ActionClass = cluster_action.ClusterAction
        elif target_type == 'NODE':
            from senlin.engine.actions import node_action
            ActionClass = node_action.NodeAction
        else:
            from senlin.engine.actions import custom_action
            ActionClass = custom_action.CustomAction

        return ActionClass(obj.target, obj.action, ctx, **kwargs)

    @classmethod
    def load(cls, ctx, action_id=None, db_action=None, project_safe=True):
        """Retrieve an action from database.

        :param ctx: Instance of request context.
        :param action_id: An UUID for the action to deserialize.
        :param db_action: An action object for the action to deserialize.
        :return: A `Action` object instance.
        """
        if db_action is None:
            db_action = ao.Action.get(ctx, action_id,
                                      project_safe=project_safe)
            if db_action is None:
                raise exception.ResourceNotFound(type='action', id=action_id)

        return cls._from_object(db_action)

    @classmethod
    def create(cls, ctx, target, action, force=False, **kwargs):
        """Create an action object.

        :param ctx: The requesting context.
        :param target: The ID of the target cluster/node.
        :param action: Name of the action.
        :param force: Skip checking locks/conflicts
        :param dict kwargs: Other keyword arguments for the action.
        :return: ID of the action created.
        """
        if not force:
            cls._check_action_lock(target, action)
            cls._check_conflicting_actions(ctx, target, action)

        params = {
            'user_id': ctx.user_id,
            'project_id': ctx.project_id,
            'domain_id': ctx.domain_id,
            'is_admin': ctx.is_admin,
            'request_id': ctx.request_id,
            'trusts': ctx.trusts,
        }
        c = req_context.RequestContext.from_dict(params)

        if action in consts.CLUSTER_SCALE_ACTIONS:
            Action.validate_scaling_action(c, target, action)

        obj = cls(target, action, c, **kwargs)
        return obj.store(ctx)

    @staticmethod
    def _check_action_lock(target, action):
        if action in consts.LOCK_BYPASS_ACTIONS:
            return
        elif (action in list(consts.CLUSTER_ACTION_NAMES) and
                cl.ClusterLock.is_locked(target)):
            raise exception.ResourceIsLocked(
                action=action, type='cluster', id=target)
        elif (action in list(consts.NODE_ACTION_NAMES) and
              nl.NodeLock.is_locked(target)):
            raise exception.ResourceIsLocked(
                action=action, type='node', id=target)

    @staticmethod
    def _check_conflicting_actions(ctx, target, action):
        conflict_actions = ao.Action.get_all_active_by_target(ctx, target)
        # Ignore conflicting actions on deletes.
        if not conflict_actions or action in consts.CONFLICT_BYPASS_ACTIONS:
            return
        else:
            action_ids = [a['id'] for a in conflict_actions]
            raise exception.ActionConflict(
                type=action, target=target, actions=",".join(action_ids))

    @classmethod
    def delete(cls, ctx, action_id):
        """Delete an action from database.

        :param ctx: An instance of the request context.
        :param action_id: The UUID of the target action to be deleted.
        :return: Nothing.
        """
        ao.Action.delete(ctx, action_id)

    def signal(self, cmd):
        """Send a signal to the action.

        :param cmd: One of the command word defined in self.COMMANDS.
        :returns: None
        """
        if cmd not in self.COMMANDS:
            return

        if cmd == self.SIG_CANCEL:
            expected = (self.INIT, self.WAITING, self.READY, self.RUNNING,
                        self.WAITING_LIFECYCLE_COMPLETION)
        elif cmd == self.SIG_SUSPEND:
            expected = (self.RUNNING)
        else:  # SIG_RESUME
            expected = (self.SUSPENDED)

        if self.status not in expected:
            LOG.info("Action (%(id)s) is in status (%(actual)s) while "
                     "expected status must be one of (%(expected)s).",
                     dict(id=self.id[:8], expected=expected,
                          actual=self.status))
            return

        ao.Action.signal(self.context, self.id, cmd)

    def signal_cancel(self):
        """Signal the action and any depended actions to cancel.

        If the action or any depended actions are in status
        'WAITING_LIFECYCLE_COMPLETION' or 'INIT' update the status to cancelled
         directly.

        :raises: `ActionImmutable` if the action is in an unchangeable state
        """
        expected = (self.INIT, self.WAITING, self.READY, self.RUNNING,
                    self.WAITING_LIFECYCLE_COMPLETION)

        if self.status not in expected:
            raise exception.ActionImmutable(id=self.id[:8], expected=expected,
                                            actual=self.status)

        ao.Action.signal(self.context, self.id, self.SIG_CANCEL)

        if self.status in (self.WAITING_LIFECYCLE_COMPLETION, self.INIT):
            self.set_status(self.RES_CANCEL, 'Action execution cancelled')

        depended = dobj.Dependency.get_depended(self.context, self.id)
        if not depended:
            return

        for child in depended:
            # Try to cancel all dependant actions
            action = self.load(self.context, action_id=child)
            if not action.is_cancelled():
                ao.Action.signal(self.context, child, self.SIG_CANCEL)
            # If the action is in WAITING_LIFECYCLE_COMPLETION or INIT update
            # the status to CANCELLED immediately.
            if action.status in (action.WAITING_LIFECYCLE_COMPLETION,
                                 action.INIT):
                action.set_status(action.RES_CANCEL,
                                  'Action execution cancelled')

    def force_cancel(self):
        """Force the action and any depended actions to cancel.

        If the action or any depended actions are in status 'INIT', 'WAITING',
        'READY', 'RUNNING', or 'WAITING_LIFECYCLE_COMPLETION' immediately
        update their status to cancelled. This should only be used if an action
        is stuck/dead and has no expectation of ever completing.

        :raises: `ActionImmutable` if the action is in an unchangeable state
        """
        LOG.debug('Forcing action %s to cancel.', self.id)
        self.set_status(self.RES_CANCEL, 'Action execution force cancelled')

        self.release_lock()

        depended = dobj.Dependency.get_depended(self.context, self.id)
        if not depended:
            return

        for child in depended:
            # Force cancel all dependant actions
            action = self.load(self.context, action_id=child)
            if action.status in (action.INIT, action.WAITING, action.READY,
                                 action.RUNNING,
                                 action.WAITING_LIFECYCLE_COMPLETION):
                LOG.debug('Forcing action %s to cancel.', action.id)
                action.set_status(action.RES_CANCEL,
                                  'Action execution force cancelled')
                action.release_lock()

    def execute(self, **kwargs):
        """Execute the action.

        In theory, the action encapsulates all information needed for
        execution.  'kwargs' may specify additional parameters.
        :param kwargs: additional parameters that may override the default
                       properties stored in the action record.
        """
        raise NotImplementedError

    def release_lock(self):
        """Release the lock associated with the action."""
        raise NotImplementedError

    def set_status(self, result, reason=None):
        """Set action status based on return value from execute."""

        timestamp = wallclock()

        if result == self.RES_OK:
            status = self.SUCCEEDED
            ao.Action.mark_succeeded(self.context, self.id, timestamp)

        elif result == self.RES_ERROR:
            status = self.FAILED
            ao.Action.mark_failed(self.context, self.id, timestamp,
                                  reason or 'ERROR')

        elif result == self.RES_TIMEOUT:
            status = self.FAILED
            ao.Action.mark_failed(self.context, self.id, timestamp,
                                  reason or 'TIMEOUT')

        elif result == self.RES_CANCEL:
            status = self.CANCELLED
            ao.Action.mark_cancelled(self.context, self.id, timestamp)

        else:  # result == self.RES_RETRY:
            retries = self.data.get('retries', 0)
            # Action failed at the moment, but can be retried
            # retries time is configurable
            if retries < cfg.CONF.lock_retry_times:
                status = self.READY
                retries += 1

                self.data.update({'retries': retries})
                ao.Action.abandon(self.context, self.id, {'data': self.data})
                # sleep for a while
                eventlet.sleep(cfg.CONF.lock_retry_interval)
                dispatcher.start_action(self.id)
            else:
                status = self.RES_ERROR
                if not reason:
                    reason = ('Exceeded maximum number of retries (%d)'
                              '') % cfg.CONF.lock_retry_times
                ao.Action.mark_failed(self.context, self.id, timestamp, reason)

        if status == self.SUCCEEDED:
            EVENT.info(self, consts.PHASE_END, reason or 'SUCCEEDED')
        elif status == self.READY:
            EVENT.warning(self, consts.PHASE_ERROR, reason or 'RETRY')
        else:
            EVENT.error(self, consts.PHASE_ERROR, reason or 'ERROR')

        self.status = status
        self.status_reason = reason

    def get_status(self):
        timestamp = wallclock()
        status = ao.Action.check_status(self.context, self.id, timestamp)
        self.status = status
        return status

    def is_timeout(self, timeout=None):
        if timeout is None:
            timeout = self.timeout
        if self.start_time is None:
            return False
        time_elapse = wallclock() - self.start_time
        return time_elapse > timeout

    def _check_signal(self):
        # Check timeout first, if true, return timeout message
        if self.timeout is not None and self.is_timeout():
            EVENT.debug(self, consts.PHASE_ERROR, 'TIMEOUT')
            return self.RES_TIMEOUT

        result = ao.Action.signal_query(self.context, self.id)
        return result

    def is_cancelled(self):
        return self._check_signal() == self.SIG_CANCEL

    def is_suspended(self):
        return self._check_signal() == self.SIG_SUSPEND

    def is_resumed(self):
        return self._check_signal() == self.SIG_RESUME

    def policy_check(self, cluster_id, target):
        """Check all policies attached to cluster and give result.

        :param cluster_id: The ID of the cluster to which the policy is
            attached.
        :param target: A tuple of ('when', action_name)
        :return: A dictionary that contains the check result.
        """

        if target not in ['BEFORE', 'AFTER']:
            return

        bindings = cpo.ClusterPolicy.get_all(self.context, cluster_id,
                                             sort='priority',
                                             filters={'enabled': True})

        # default values
        self.data['status'] = policy_mod.CHECK_NONE
        self.data['reason'] = ''

        for pb in bindings:
            policy = policy_mod.Policy.load(self.context, pb.policy_id,
                                            project_safe=False)

            # add last_op as input for the policy so that it can be used
            # during pre_op
            self.inputs['last_op'] = pb.last_op

            if not policy.need_check(target, self):
                continue

            if target == 'BEFORE':
                method = getattr(policy, 'pre_op', None)
            else:  # target == 'AFTER'
                method = getattr(policy, 'post_op', None)

            # call policy check function
            # it will set result in data['status']
            if method is not None:
                method(cluster_id, self)

            # stop policy check is one of them fails
            if self.data['status'] == policy_mod.CHECK_ERROR:
                reason = self.data['reason']
                self.data['reason'] = ("Failed policy '%(name)s': %(reason)s"
                                       ) % {'name': policy.name,
                                            'reason': reason}
                return

        self.data['status'] = policy_mod.CHECK_OK
        self.data['reason'] = 'Completed policy checking.'

        return

    @staticmethod
    def validate_scaling_action(ctx, cluster_id, action):
        """Validate scaling action against actions table and policy cooldown.

        :param ctx: An instance of the request context.
        :param cluster_id: ID of the cluster the scaling action is targeting.
        :param action: Scaling action being validated.
        :return: None
        :raises: An exception of ``ActionCooldown`` when the action being
        validated is still in cooldown based off the policy or
        ``ActionConflict`` when a scaling action is already in the action
        table.
        """
        # Check for conflicting actions in the actions table.
        conflicting_actions = Action._get_conflicting_scaling_actions(
            ctx, cluster_id)
        if conflicting_actions:
            action_ids = [a.get('id', None) for a in conflicting_actions]
            LOG.info("Unable to process %(action)s for cluster %(cluster_id)s "
                     "the action conflicts with %(conflicts)s",
                     {'action': action,
                      'cluster_id': cluster_id,
                      'conflicts': action_ids})
            raise exception.ActionConflict(
                type=action,
                target=cluster_id,
                actions=",".join(action_ids))

        # Check to see if action cooldown should be observed.
        bindings = cpo.ClusterPolicy.get_all(ctx, cluster_id,
                                             sort='priority',
                                             filters={'enabled': True})
        for pb in bindings:
            policy = policy_mod.Policy.load(ctx, pb.policy_id)
            if getattr(policy, 'cooldown', None) and policy.event == action:
                if pb.last_op and not timeutils.is_older_than(
                        pb.last_op, policy.cooldown):
                    LOG.info("Unable to process %(action)s for cluster "
                             "%(cluster_id)s the actions policy %(policy)s "
                             "cooldown still in progress",
                             {'action': action,
                              'cluster_id': cluster_id,
                              'policy': pb.policy_id})
                    raise exception.ActionCooldown(
                        type=action,
                        cluster=cluster_id,
                        policy_id=pb.policy_id)
        return

    @staticmethod
    def _get_conflicting_scaling_actions(ctx, cluster_id):
        """Check actions table for conflicting scaling actions.

        :param ctx: An instance of the request context.
        :param cluster_id: ID of the cluster the scaling action is targeting.
        :return: A list of conflicting actions.
        """
        scaling_actions = ao.Action.action_list_active_scaling(
            ctx, cluster_id)
        if scaling_actions:
            return [a.to_dict() for a in scaling_actions]
        else:
            return None

    def to_dict(self):
        if self.id:
            dep_on = dobj.Dependency.get_depended(self.context, self.id)
            dep_by = dobj.Dependency.get_dependents(self.context, self.id)
        else:
            dep_on = []
            dep_by = []
        action_dict = {
            'id': self.id,
            'name': self.name,
            'cluster_id': self.cluster_id,
            'action': self.action,
            'target': self.target,
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
            'depends_on': dep_on,
            'depended_by': dep_by,
            'created_at': utils.isotime(self.created_at),
            'updated_at': utils.isotime(self.updated_at),
            'data': self.data,
            'user': self.user,
            'project': self.project,
        }
        return action_dict


def ActionProc(ctx, action_id):
    """Action process."""

    # Step 1: materialize the action object
    action = Action.load(ctx, action_id=action_id, project_safe=False)
    if action is None:
        LOG.error('Action "%s" could not be found.', action_id)
        return False

    if action.is_cancelled():
        reason = '%(action)s [%(id)s] cancelled' % {
            'action': action.action, 'id': action.id[:8]}
        action.set_status(action.RES_CANCEL, reason)
        LOG.info(reason)
        return True

    EVENT.info(action, consts.PHASE_START, action_id[:8])

    reason = 'Action completed'
    success = True
    try:
        # Step 2: execute the action
        result, reason = action.execute()
        if result == action.RES_RETRY:
            success = False
    except Exception as ex:
        # We catch exception here to make sure the following logics are
        # executed.
        result = action.RES_ERROR
        reason = str(ex)
        LOG.exception('Unexpected exception occurred during action '
                      '%(action)s (%(id)s) execution: %(reason)s',
                      {'action': action.action, 'id': action.id,
                       'reason': reason})
        success = False
    finally:
        # NOTE: locks on action is eventually released here by status update
        action.set_status(result, reason)

    return success
