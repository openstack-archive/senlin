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

from oslo_log import log as logging
import six

from senlin.common import consts
from senlin.common import exception as exc
from senlin.common.i18n import _, _LE
from senlin.common import schema
from senlin.common import utils
from senlin.profiles import base

LOG = logging.getLogger(__name__)


class StackProfile(base.Profile):
    """Profile for an OpenStack Heat stack."""

    VERSIONS = {
        '1.0': [
            {'status': consts.SUPPORTED, 'since': '2016.04'}
        ]
    }

    KEYS = (
        CONTEXT, TEMPLATE, TEMPLATE_URL, PARAMETERS,
        FILES, TIMEOUT, DISABLE_ROLLBACK, ENVIRONMENT,
    ) = (
        'context', 'template', 'template_url', 'parameters',
        'files', 'timeout', 'disable_rollback', 'environment',
    )

    properties_schema = {
        CONTEXT: schema.Map(
            _('A dictionary for specifying the customized context for '
              'stack operations'),
            default={},
        ),
        TEMPLATE: schema.Map(
            _('Heat stack template.'),
            default={},
            updatable=True,
        ),
        TEMPLATE_URL: schema.String(
            _('Heat stack template url.'),
            default='',
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

    OP_NAMES = (
        OP_ABANDON,
    ) = (
        'abandon',
    )

    OPERATIONS = {
        OP_ABANDON: schema.Map(
            _('Abandon a heat stack node.'),
        )
    }

    def __init__(self, type_name, name, **kwargs):
        super(StackProfile, self).__init__(type_name, name, **kwargs)
        self.stack_id = None

    def validate(self, validate_props=False):
        '''Validate the schema and the data provided.'''
        # general validation
        self.spec_data.validate()
        self.properties.validate()
        # validate template
        template = self.properties[self.TEMPLATE]
        template_url = self.properties[self.TEMPLATE_URL]
        if not template and not template_url:
            msg = _("Both template and template_url are not specified "
                    "for profile '%s'.") % self.name
            raise exc.InvalidSpec(message=msg)

        if validate_props:
            self.do_validate(obj=self)

    def do_validate(self, obj):
        """Validate the stack template used by a node.

        :param obj: Node object to operate.
        :returns: True if validation succeeds.
        :raises: `InvalidSpec` exception is raised if template is invalid.
        """
        kwargs = {
            'stack_name': utils.random_name(),
            'template': self.properties[self.TEMPLATE],
            'template_url': self.properties[self.TEMPLATE_URL],
            'parameters': self.properties[self.PARAMETERS],
            'files': self.properties[self.FILES],
            'environment': self.properties[self.ENVIRONMENT],
            'preview': True,
        }
        try:
            self.orchestration(obj).stack_create(**kwargs)
        except exc.InternalError as ex:
            msg = _('Failed in validating template: %s') % six.text_type(ex)
            raise exc.InvalidSpec(message=msg)

        return True

    def do_create(self, obj):
        """Create a heat stack using the given node object.

        :param obj: The node object to operate on.
        :returns: The UUID of the heat stack created.
        """
        kwargs = {
            'stack_name': obj.name + '-' + utils.random_name(8),
            'template': self.properties[self.TEMPLATE],
            'template_url': self.properties[self.TEMPLATE_URL],
            'timeout_mins': self.properties[self.TIMEOUT],
            'disable_rollback': self.properties[self.DISABLE_ROLLBACK],
            'parameters': self.properties[self.PARAMETERS],
            'files': self.properties[self.FILES],
            'environment': self.properties[self.ENVIRONMENT],
        }

        try:
            stack = self.orchestration(obj).stack_create(**kwargs)

            # Timeout = None means we will use the 'default_action_timeout'
            # It can be overridden by the TIMEOUT profile propertie
            timeout = None
            if self.properties[self.TIMEOUT]:
                timeout = self.properties[self.TIMEOUT] * 60

            self.orchestration(obj).wait_for_stack(stack.id, 'CREATE_COMPLETE',
                                                   timeout=timeout)
            return stack.id
        except exc.InternalError as ex:
            raise exc.EResourceCreation(type='stack', message=ex.message)

    def do_delete(self, obj, **params):
        """Delete the physical stack behind the node object.

        :param obj: The node object to operate on.
        :param kwargs params: Optional keyword arguments for the delete
                              operation.
        :returns: This operation always return True unless exception is
                  caught.
        :raises: `EResourceDeletion` if interaction with heat fails.
        """
        stack_id = obj.physical_id

        ignore_missing = params.get('ignore_missing', True)
        try:
            self.orchestration(obj).stack_delete(stack_id, ignore_missing)
            self.orchestration(obj).wait_for_stack_delete(stack_id)
        except exc.InternalError as ex:
            raise exc.EResourceDeletion(type='stack', id=stack_id,
                                        message=six.text_type(ex))
        return True

    def do_update(self, obj, new_profile, **params):
        """Perform update on object.

        :param obj: the node object to operate on
        :param new_profile: the new profile used for updating
        :param params: other parameters for the update request.
        :returns: A boolean indicating whether the operation is successful.
        """
        self.stack_id = obj.physical_id
        if not self.stack_id:
            return False

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

        if not fields:
            return True

        try:
            hc = self.orchestration(obj)
            # Timeout = None means we will use the 'default_action_timeout'
            # It can be overridden by the TIMEOUT profile propertie
            timeout = None
            if self.properties[self.TIMEOUT]:
                timeout = self.properties[self.TIMEOUT] * 60
            hc.stack_update(self.stack_id, **fields)
            hc.wait_for_stack(self.stack_id, 'UPDATE_COMPLETE',
                              timeout=timeout)
        except exc.InternalError as ex:
            raise exc.EResourceUpdate(type='stack', id=self.stack_id,
                                      message=ex.message)

        return True

    def do_check(self, obj):
        """Check stack status.

        :param obj: Node object to operate.
        :returns: True if check succeeded, or False otherwise.
        """
        stack_id = obj.physical_id
        if stack_id is None:
            return False

        hc = self.orchestration(obj)
        try:
            # Timeout = None means we will use the 'default_action_timeout'
            # It can be overridden by the TIMEOUT profile propertie
            timeout = None
            if self.properties[self.TIMEOUT]:
                timeout = self.properties[self.TIMEOUT] * 60
            hc.stack_check(stack_id)
            hc.wait_for_stack(stack_id, 'CHECK_COMPLETE', timeout=timeout)
        except exc.InternalError as ex:
            LOG.error(_LE('Failed in checking stack: %s.'), ex)
            return False

        return True

    def do_get_details(self, obj):
        if not obj.physical_id:
            return {}

        try:
            stack = self.orchestration(obj).stack_get(obj.physical_id)
            return stack.to_dict()
        except exc.InternalError as ex:
            return {
                'Error': {
                    'code': ex.code,
                    'message': six.text_type(ex)
                }
            }

    def handle_abandon(self, obj, **options):
        """Handler for abandoning a heat stack node."""
        pass
