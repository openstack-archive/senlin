#
# Copyright 2010 United States Government as represented by the
# Administrator of the National Aeronautics and Space Administration.
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

'''
Senlin exception subclasses.
'''

import sys

from oslo_log import log as logging
import six

from senlin.common.i18n import _

_FATAL_EXCEPTION_FORMAT_ERRORS = False
LOG = logging.getLogger(__name__)


class SenlinException(Exception):
    """Base Senlin Exception.

    To correctly use this class, inherit from it and define a 'msg_fmt'
    property. That msg_fmt will get printed with the keyword arguments
    provided to the constructor.
    """
    message = _("An unknown exception occurred.")

    def __init__(self, **kwargs):
        self.kwargs = kwargs

        try:
            self.message = self.msg_fmt % kwargs
            # if last char is '.', wipe out redundant '.'
            if self.message[-1] == '.':
                self.message = self.message.rstrip('.') + '.'
        except KeyError:
            # exc_info = sys.exc_info()
            # if kwargs doesn't match a variable in the message
            # log the issue and the kwargs
            LOG.exception('Exception in string format operation')
            for name, value in kwargs.items():
                LOG.error("%s: %s" % (name, value))  # noqa

            if _FATAL_EXCEPTION_FORMAT_ERRORS:
                raise
                # raise exc_info[0], exc_info[1], exc_info[2]

    def __str__(self):
        return six.text_type(self.message)

    def __unicode__(self):
        return six.text_type(self.message)

    def __deepcopy__(self, memo):
        return self.__class__(**self.kwargs)


class SIGHUPInterrupt(SenlinException):
    msg_fmt = _("System SIGHUP signal received.")


class NotAuthenticated(SenlinException):
    msg_fmt = _("You are not authenticated.")


class Forbidden(SenlinException):
    msg_fmt = _("You are not authorized to complete this operation.")


class BadRequest(SenlinException):
    msg_fmt = _("%(msg)s.")


class InvalidAPIVersionString(SenlinException):
    msg_fmt = _("API Version String '%(version)s' is of invalid format. It "
                "must be of format 'major.minor'.")


class MethodVersionNotFound(SenlinException):
    msg_fmt = _("API version '%(version)s' is not supported on this method.")


class InvalidGlobalAPIVersion(SenlinException):
    msg_fmt = _("Version '%(req_ver)s' is not supported by the API. Minimum "
                "is '%(min_ver)s' and maximum is '%(max_ver)s'.")


class MultipleChoices(SenlinException):
    msg_fmt = _("Multiple results found matching the query criteria "
                "'%(arg)s'. Please be more specific.")


class ResourceNotFound(SenlinException):
    """Generic exception for resource not found.

    The resource type here can be 'cluster', 'node', 'profile',
    'policy', 'receiver', 'webhook', 'profile_type', 'policy_type',
    'action', 'event' and so on.
    """
    msg_fmt = _("The %(type)s '%(id)s' could not be found.")

    @staticmethod
    def enhance_msg(enhance, ex):
        enhance_msg = ex.message[:4] + enhance + ' ' + ex.message[4:]
        return enhance_msg


class ResourceInUse(SenlinException):
    """Generic exception for resource in use.

    The resource type here can be 'cluster', 'node', 'profile',
    'policy', 'receiver', 'webhook', 'profile_type', 'policy_type',
    'action', 'event' and so on.
    """
    msg_fmt = _("The %(type)s '%(id)s' cannot be deleted: %(reason)s.")


class ProfileNotSpecified(SenlinException):
    msg_fmt = _("Profile not specified.")


class ProfileOperationFailed(SenlinException):
    msg_fmt = _("%(message)s")


class ProfileOperationTimeout(SenlinException):
    msg_fmt = _("%(message)s")


class PolicyNotSpecified(SenlinException):
    msg_fmt = _("Policy not specified.")


class PolicyBindingNotFound(SenlinException):
    msg_fmt = _("The policy '%(policy)s' is not found attached to the "
                "specified cluster '%(identity)s'.")


class PolicyTypeConflict(SenlinException):
    msg_fmt = _("The policy with type '%(policy_type)s' already exists.")


class InvalidSpec(SenlinException):
    msg_fmt = _("%(message)s")


class FeatureNotSupported(SenlinException):
    msg_fmt = _("%(feature)s is not supported.")


class Error(SenlinException):
    msg_fmt = "%(message)s"

    def __init__(self, msg):
        super(Error, self).__init__(message=msg)


class InvalidContentType(SenlinException):
    msg_fmt = _("Invalid content type %(content_type)s")


class RequestLimitExceeded(SenlinException):
    msg_fmt = _('Request limit exceeded: %(message)s')


class ActionInProgress(SenlinException):
    msg_fmt = _("The %(type)s '%(id)s' is in status %(status)s.")


class NodeNotOrphan(SenlinException):
    msg_fmt = _("%(message)s")


class InternalError(SenlinException):
    """A base class for internal exceptions in senlin.

    The internal exception classes which inherit from :class:`SenlinException`
    class should be translated to a user facing exception type if need to be
    made user visible.
    """
    msg_fmt = _("%(message)s")
    message = _('Internal error happened')

    def __init__(self, **kwargs):
        self.code = kwargs.pop('code', 500)
        self.message = kwargs.pop('message', self.message)
        super(InternalError, self).__init__(
            code=self.code, message=self.message, **kwargs)


class EResourceBusy(InternalError):
    # Internal exception, not to be exposed to end user.
    msg_fmt = _("The %(type)s '%(id)s' is busy now.")


class TrustNotFound(InternalError):
    # Internal exception, not to be exposed to end user.
    msg_fmt = _("The trust for trustor '%(trustor)s' could not be found.")


class EResourceCreation(InternalError):
    # Used when creating resources in other services
    def __init__(self, **kwargs):
        self.resource_id = kwargs.pop('resource_id', None)
        super(EResourceCreation, self).__init__(
            resource_id=self.resource_id, **kwargs)
    msg_fmt = _("Failed in creating %(type)s: %(message)s.")


class EResourceUpdate(InternalError):
    # Used when updating resources from other services
    msg_fmt = _("Failed in updating %(type)s '%(id)s': %(message)s.")


class EResourceDeletion(InternalError):
    # Used when deleting resources from other services
    msg_fmt = _("Failed in deleting %(type)s '%(id)s': %(message)s.")


class EServerNotFound(InternalError):
    # Used when deleting resources from other services
    msg_fmt = _("Failed in found %(type)s '%(id)s': %(message)s.")


class EResourceOperation(InternalError):
    """Generic exception for resource fail operation.

    The op here can be 'recovering','rebuilding', 'checking' and
    so on. And the op 'creating', 'updating' and 'deleting' we can
    use separately class `EResourceCreation`,`EResourceUpdate` and
    `EResourceDeletion`.
    The type here is resource's driver type.It can be 'server',
    'stack', 'container' and so on.
    The id is resource's id.
    The message here can be message from class 'ResourceNotFound',
    'ResourceInUse' and so on, or developer can specified message.
    """
    # Used when operating resources from other services
    msg_fmt = _("Failed in %(op)s %(type)s '%(id)s': %(message)s.")


class ESchema(InternalError):
    msg_fmt = _("%(message)s")


class InvalidPlugin(InternalError):
    msg_fmt = _("%(message)s")


class PolicyNotAttached(InternalError):
    msg_fmt = _("The policy '%(policy)s' is not attached to the specified "
                "cluster '%(cluster)s'.")


class HTTPExceptionDisguise(Exception):
    """Disguises HTTP exceptions.

    The purpose is to let them be handled by the webob fault application
    in the wsgi pipeline.
    """

    def __init__(self, exception):
        self.exc = exception
        self.tb = sys.exc_info()[2]
