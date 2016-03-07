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

from oslo_log import log as logging

from senlin.common import exception
from senlin.common.i18n import _
from senlin.common import schema
from senlin.common import utils
from senlin.drivers import base as driver_base
from senlin.engine import scheduler
from senlin.profiles import base

LOG = logging.getLogger(__name__)


class StackProfile(base.Profile):
    '''Profile for an OpenStack Heat stack.

    When this profile is used, the whole cluster is a collection of Heat
    stacks.
    '''

    KEYS = (
        TEMPLATE, CONTEXT, PARAMETERS, FILES,
        TIMEOUT, DISABLE_ROLLBACK, ENVIRONMENT,
    ) = (
        'template', 'context', 'parameters', 'files',
        'timeout', 'disable_rollback', 'environment',
    )

    properties_schema = {
        CONTEXT: schema.Map(
            _('A dictionary for specifying the customized context for '
              'stack operations'),
            default={},
        ),
        TEMPLATE: schema.Map(
            _('Heat stack template.'),
            required=True,
            updatable=True,
        ),
        PARAMETERS: schema.Map(
            _('Parameters to be passed to Heat for stack operations.'),
            default={},
            updatable=True,
        ),
        FILES: schema.Map(
            _('Contents of files referenced by the template, if any.'),
            default={},
            updatable=True,
        ),
        TIMEOUT: schema.Integer(
            _('A integer that specifies the number of minutes that a '
              'stack operation times out.'),
            updatable=True,
        ),
        DISABLE_ROLLBACK: schema.Boolean(
            _('A boolean specifying whether a stack operation can be '
              'rolled back.'),
            default=True,
            updatable=True,
        ),
        ENVIRONMENT: schema.Map(
            _('A map that specifies the environment used for stack '
              'operations.'),
            default={},
            updatable=True,
        )
    }

    def __init__(self, type_name, name, **kwargs):
        super(StackProfile, self).__init__(type_name, name, **kwargs)

        self.hc = None
        self.stack_id = None

    def heat(self, obj):
        '''Construct heat client using the combined context.'''

        if self.hc:
            return self.hc
        params = self._build_conn_params(obj.user, obj.project)
        self.hc = driver_base.SenlinDriver().orchestration(params)
        return self.hc

    def do_validate(self, obj):
        '''Validate if the spec has provided info for stack creation.'''

        kwargs = {
            'stack_name': obj.name,
            'template': self.properties[self.TEMPLATE],
            'timeout_mins': self.properties[self.TIMEOUT],
            'disable_rollback': self.properties[self.DISABLE_ROLLBACK],
            'parameters': self.properties[self.PARAMETERS],
            'files': self.properties[self.FILES],
            'environment': self.properties[self.ENVIRONMENT],
        }
        try:
            self.heat(obj).stacks.validate(**kwargs)
        except Exception as ex:
            msg = _('Failed validate stack template due to '
                    '"%s"') % six.text_type(ex)
            raise exception.InvalidSpec(message=msg)

        return True

    def _check_action_complete(self, obj, action):
        stack = self.heat(obj).stack_get(self.stack_id)

        status = stack.status.split('_', 1)

        if status[0] == action:
            if status[1] == 'IN_PROGRESS':
                return False

            if status[1] == 'COMPLETE':
                return True

            raise exception.ResourceStatusError(resource_id=self.stack_id,
                                                status=stack.status,
                                                reason=stack.status_reason)
        else:
            return False

    def do_create(self, obj):
        '''Create a stack using the given profile.'''

        kwargs = {
            'stack_name': obj.name + '-' + utils.random_name(8),
            'template': self.properties[self.TEMPLATE],
            'timeout_mins': self.properties[self.TIMEOUT],
            'disable_rollback': self.properties[self.DISABLE_ROLLBACK],
            'parameters': self.properties[self.PARAMETERS],
            'files': self.properties[self.FILES],
            'environment': self.properties[self.ENVIRONMENT],
        }

        LOG.info('Creating stack: %s' % kwargs)
        stack = self.heat(obj).stack_create(**kwargs)
        self.stack_id = stack.id

        # Wait for action to complete/fail
        while not self._check_action_complete(obj, 'CREATE'):
            scheduler.sleep(1)

        return stack.id

    def do_delete(self, obj):
        self.stack_id = obj.physical_id

        try:
            self.heat(obj).stack_delete(self.stack_id, True)
            self.heat(obj).wait_for_stack_delete(self.stack_id)
        except Exception as ex:
            LOG.error('Error: %s' % six.text_type(ex))
            raise ex

        return True

    def do_update(self, obj, new_profile, **params):
        '''Perform update on object.

        :param obj: the node object to operate on
        :param new_profile: the new profile used for updating
        :param params: other parametes for the update request.
        '''
        self.stack_id = obj.physical_id
        if not self.stack_id:
            return True

        if not self.validate_for_update(new_profile):
            return False

        fields = {}
        new_template = new_profile.properties[new_profile.TEMPLATE]
        if new_template != self.properties[self.TEMPLATE]:
            fields['template'] = new_template

        new_params = new_profile.properties[new_profile.PARAMETERS]
        if new_params != self.properties[self.PARAMETERS]:
            fields['parameters'] = new_params

        new_timeout = new_profile.properties[new_profile.TIMEOUT]
        if new_timeout != self.properties[self.TIMEOUT]:
            fields['timeout_mins'] = new_timeout

        new_dr = new_profile.properties[new_profile.DISABLE_ROLLBACK]
        if new_dr != self.properties[self.DISABLE_ROLLBACK]:
            fields['disable_rollback'] = new_dr

        new_files = new_profile.properties[new_profile.FILES]
        if new_files != self.properties[self.FILES]:
            fields['files'] = new_files

        new_environment = new_profile.properties[new_profile.ENVIRONMENT]
        if new_environment != self.properties[self.ENVIRONMENT]:
            fields['environment'] = new_environment

        if fields:
            try:
                self.heat(obj).stack_update(self.stack_id, **fields)
            except Exception as ex:
                LOG.exception(_('Failed in updating stack: %s'
                                ), six.text_type(ex))
                return False

            # Wait for action to complete/fail
            while not self._check_action_complete(obj, 'UPDATE'):
                scheduler.sleep(1)

        return True

    def do_check(self, obj):
        """Check stack status."""
        hc = self.heat(obj)
        try:
            stack = hc.stack_get(obj.physical_id)
        except Exception as ex:
            raise ex
        # When the stack is in a status which can't be checked(
        # CREATE_IN_PROGRESS, DELETE_IN_PROGRESS, etc), return False.
        try:
            stack.check(hc.session)
        except Exception:
            return False

        status = stack.status
        while status == 'CHECK_IN_PROGRESS':
            status = hc.stack_get(obj.physical_id).status
        if status == 'CHECK_COMPLETE':
            return True
        else:
            return False

    def do_get_details(self, obj):
        if obj.physical_id is None or obj.physical_id == '':
            return {}

        return self.heat(obj).stack_get(obj.physical_id)
