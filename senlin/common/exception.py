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
from senlin.common.i18n import _LE

_FATAL_EXCEPTION_FORMAT_ERRORS = False
LOG = logging.getLogger(__name__)


class SenlinException(Exception):
    '''Base Senlin Exception.

    To correctly use this class, inherit from it and define
    a 'msg_fmt' property. That msg_fmt will get printf'd
    with the keyword arguments provided to the constructor.
    '''

    message = _("An unknown exception occurred.")

    def __init__(self, **kwargs):
        self.kwargs = kwargs

        try:
            self.message = self.msg_fmt % kwargs
        except KeyError:
            # exc_info = sys.exc_info()
            # if kwargs doesn't match a variable in the message
            # log the issue and the kwargs
            LOG.exception(_LE('Exception in string format operation'))
            for name, value in six.iteritems(kwargs):
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
    msg_fmt = _("The request is malformed: %(msg)s")


class InvalidAPIVersionString(SenlinException):
    msg_fmt = _("API Version String (%(version)s) is of invalid format. It "
                "must be of format 'major.minor'.")


class MethodVersionNotFound(SenlinException):
    msg_fmt = _("API version %(version)s is not supported on this method.")


class InvalidGlobalAPIVersion(SenlinException):
    msg_fmt = _("Version %(req_ver)s is not supported by the API. Minimum is "
                "%(min_ver)s and maximum is %(max_ver)s.")


class MultipleChoices(SenlinException):
    msg_fmt = _("Multiple results found matching the query criteria %(arg)s. "
                "Please be more specific.")


class InvalidParameter(SenlinException):
    msg_fmt = _("Invalid value '%(value)s' specified for '%(name)s'")


class ClusterNotFound(SenlinException):
    msg_fmt = _("The cluster (%(cluster)s) could not be found.")


class ClusterBusy(SenlinException):
    msg_fmt = _("The cluster (%(cluster)s) cannot be deleted: %(reason)s")


class NodeNotFound(SenlinException):
    msg_fmt = _("The node (%(node)s) could not be found.")


class ProfileTypeNotFound(SenlinException):
    msg_fmt = _("Profile type (%(profile_type)s) is not found.")


class ProfileTypeNotMatch(SenlinException):
    msg_fmt = _("%(message)s")


class ProfileNotFound(SenlinException):
    msg_fmt = _("The profile (%(profile)s) could not be found.")


class ProfileNotSpecified(SenlinException):
    msg_fmt = _("Profile not specified.")


class ProfileOperationFailed(SenlinException):
    msg_fmt = _("%(message)s")


class ProfileOperationTimeout(SenlinException):
    msg_fmt = _("%(message)s")


class PolicyNotSpecified(SenlinException):
    msg_fmt = _("Policy not specified.")


class PolicyTypeNotFound(SenlinException):
    msg_fmt = _("Policy type (%(policy_type)s) is not found.")


class PolicyNotFound(SenlinException):
    msg_fmt = _("The policy (%(policy)s) could not be found.")


class PolicyBindingNotFound(SenlinException):
    msg_fmt = _("The policy (%(policy)s) is not found attached to the "
                "specified cluster (%(identity)s).")


class PolicyTypeConflict(SenlinException):
    msg_fmt = _("The policy with type (%(policy_type)s) already exists.")


class InvalidSchemaError(SenlinException):
    msg_fmt = _("%(message)s")


class SpecValidationFailed(SenlinException):
    msg_fmt = _("%(message)s")


class FeatureNotSupported(SenlinException):
    msg_fmt = _("%(feature)s is not supported.")


class Error(SenlinException):
    msg_fmt = "%(message)s"

    def __init__(self, msg):
        super(Error, self).__init__(message=msg)


class ResourceInUse(SenlinException):
    msg_fmt = _("The %(resource_type)s (%(resource_id)s) is still in use.")


class InvalidContentType(SenlinException):
    msg_fmt = _("Invalid content type %(content_type)s")


class RequestLimitExceeded(SenlinException):
    msg_fmt = _('Request limit exceeded: %(message)s')


class WebhookNotFound(SenlinException):
    msg_fmt = _("The webhook (%(webhook)s) could not be found.")


class ReceiverNotFound(SenlinException):
    msg_fmt = _("The receiver (%(receiver)s) could not be found.")


class ActionNotFound(SenlinException):
    msg_fmt = _("The action (%(action)s) could not be found.")


class ActionInProgress(SenlinException):
    msg_fmt = _("Cluster %(cluster_name)s already has an action (%(action)s) "
                "in progress.")


class EventNotFound(SenlinException):
    msg_fmt = _("The event (%(event)s) could not be found.")


class NodeNotOrphan(SenlinException):
    msg_fmt = _("%(message)s")


class InternalError(SenlinException):
    '''A base class for internal exceptions in senlin.

    The internal exception classes which inherit from :class:`InternalError`
    class should be translated to a user facing exception type if need to be
    made user visible.
    '''
    msg_fmt = _('ERROR %(code)s happens for %(message)s.')
    message = _('Internal error happens')

    def __init__(self, **kwargs):
        super(InternalError, self).__init__(**kwargs)
        if 'code' in kwargs:
            self.code = kwargs.get('code', 500)
            self.message = kwargs.get('message', self.message)


class ResourceBusyError(InternalError):
    msg_fmt = _("The %(resource_type)s (%(resource_id)s) is busy now.")


class TrustNotFound(InternalError):
    # Internal exception, not to be exposed to end user.
    msg_fmt = _("The trust for trustor (%(trustor)s) could not be found.")


class ResourceCreationFailure(InternalError):
    # Used when creating resources in other services
    msg_fmt = _("Failed in creating %(rtype)s.")


class ResourceUpdateFailure(InternalError):
    # Used when updating resources from other services
    msg_fmt = _("Failed in updating %(resource)s.")


class ResourceDeletionFailure(InternalError):
    # Used when deleting resources from other services
    msg_fmt = _("Failed in deleting %(resource)s.")


class ResourceNotFound(InternalError):
    # Used when retrieving resources from other services
    msg_fmt = _("The resource (%(resource)s) could not be found.")


class ResourceStatusError(InternalError):
    msg_fmt = _("The resource %(resource_id)s is in error status "
                "- '%(status)s' due to '%(reason)s'.")


class InvalidPlugin(InternalError):
    msg_fmt = _("%(message)s")


class InvalidSpec(InternalError):
    msg_fmt = _("%(message)s")


class PolicyNotAttached(InternalError):
    msg_fmt = _("The policy (%(policy)s) is not attached to the specified "
                "cluster (%(cluster)s).")


class HTTPExceptionDisguise(Exception):
    """Disguises HTTP exceptions.

    The purpose is to let them be handled by the webob fault application
    in the wsgi pipeline.
    """

    def __init__(self, exception):
        self.exc = exception
        self.tb = sys.exc_info()[2]
