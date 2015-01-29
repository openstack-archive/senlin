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

import six

from senlin.common import context
from senlin.common import exception
from senlin.engine import scheduler
from senlin.profiles import base


class StackProfile(base.Profile):
    '''
    Profile for an OpenStack Heat stack.
    When this profile is used, the whole cluster is a collection of Heat
    stacks.
    '''

    KEYS = (
        TEMPLATE, CONTEXT, PARAMETERS,
        TIMEOUT, ENABLE_ROLLBACK,
    ) = (
        'template', 'context', 'parameters',
        'timeout', 'enable_rollback'
    )

    def __init__(self, type_name, name, **kwargs):
        super(StackProfile, self).__init__(type_name, name, **kwargs)

        self.template = self.spec.get('template', {})
        self.profile_context = self.spec.get('context', {})
        self.parameters = self.spec.get('parameters', {})
        self.files = self.spec.get('files', {})
        self.disable_rollback = self.spec.get('disable_rollback', True)
        self.timeout = self.spec.get('timeout', 60)

        self.hc = None
        self.stack_context = None
        self.stack_id = None

    def heat(self, context):
        '''
        Construct heat client using the combined context.
        '''
        if self.hc:
            return self.hc

        ctx = context
        if self.profile_context:
            ctx.update(self.profile_context)
        self.stack_context = context.RequestContext.from_dict(ctx)
        self.hc = self.stack_context.clients.heat()

    def do_validate(self, context, obj):
        '''
        Validate if the spec has provided reasonable info for stack creation.
        '''
        kwargs = {
            'stack_name': obj.name,
            'template': self.template,
            'timeout_mins': self.timeout,
            'disable_rollback': self.disable_rollback,
            'parameters': self.parameters,
            # 'files':
            'environment': {}
        }
        try:
            self.heat(context).stacks.validate(**kwargs)
        except Exception as ex:
            msg = _('Failed validate stack template due to '
                    '"%s"') % six.text_type(ex)
            raise exception.ProfileValidationFailed(message=msg)

        return True

    def _check_action_complete(self, obj, action):
        stack = self.heat(context).stacks.get(stack_id=self.stack_id)
        if stack.action == action:
            if stack.status == 'IN_PROGRESS':
                return False

            if stack.status == 'COMPLETE':
                return True

            if stack.status == 'FAILED':
                raise exception.NodeStatusError(
                    status=stack.stack_status,
                    reason=stack.stack_status_reason)
            else:
                raise exception.NodeStatusError(
                    status=stack.stack_status,
                    reason=stack.stack_status_reason)
        else:
            msg = _('Node action mismatch detected: expected=%(expected)s '
                    'actual=%(actual)s') % dict(expected=action,
                                                actual=stack.action)
            raise exception.NodeStatusError(status=stack.stack_status,
                                            reason=msg)

    def do_create(self, context, obj):
        '''
        Create a stack using the given profile.
        '''
        kwargs = {
            'stack_name': obj.name,
            'template': self.template,
            'timeout_mins': self.timeout,
            'disable_rollback': self.disable_rollback,
            'parameters': self.parameters,
            # 'files':
            'environment': {}
        }

        stack = self.heat(context).stacks.create(**kwargs)
        self.stack_id = stack['stack']['id']

        # Wait for action to complete/fail
        while not self._check_action_complete(obj, 'CREATE'):
            scheduler.sleep(1)

        return True

    def do_delete(self, context, obj):
        self.stack_id = obj.physical_id

        if not self.stack_id:
            return True

        try:
            self.heat(context).stacks.delete(stack_id=self.stack_id)
        except Exception as ex:
            if isinstance(ex, exception.NotFound):
                pass
            raise ex

        # Wait for action to complete/fail
        while not self._check_action_complete(obj, 'DELETE'):
            scheduler.sleep(1)

        return True

    def do_update(self, context, obj, new_profile):
        '''
        :param obj: the node object to operate on
        :param new_profile: the new profile used for updating
        '''
        self.stack_id = obj.physical_id
        if not self.stack_id:
            return True

        # TODO(anyone): Check if template differs
        # TODO(anyone): Check if params differs
        fields = {
            'stack_id': self.stack_id,
            'parameters': new_profile.params,
            'template': new_profile.template,
            'timeout_mins': new_profile.timeout,
            'disable_rollback': new_profile.disable_rollback,
            #'files': self.stack.t.files,
            'environment': {},
        }

        self.heat(context).stacks.update(**fields)

        # Wait for action to complete/fail
        while not self._check_action_complete(obj, 'UPDATE'):
            scheduler.sleep(1)

        return True

    def do_check(self, context, id):
        #TODO(liuh): add actual checking logic
        return True
