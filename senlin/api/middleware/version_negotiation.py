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

"""
A filter middleware that inspects the requested URI for a version string
and/or Accept headers and attempts to negotiate an API controller to
return
"""

import re

import microversion_parse as mp
from oslo_log import log as logging
import six
import webob

from senlin.api.common import version_request as vr
from senlin.api.common import wsgi
from senlin.api.openstack import versions as os_ver
from senlin.common import exception

LOG = logging.getLogger(__name__)


class VersionNegotiationFilter(wsgi.Middleware):

    def __init__(self, app, conf):
        self.versions_app = os_ver.Controller(conf)
        self.version_uri_regex = re.compile(r"^v([1-9]\d*)\.?([1-9]\d*|0)?$")
        self.conf = conf
        super(VersionNegotiationFilter, self).__init__(app)

    def process_request(self, req):
        """Process WSGI requests.

        If there is a version identifier in the URI, simply return the correct
        API controller, otherwise, if we find an Accept: header, process it
        """
        msg = ("Processing request: %(m)s %(p)s Accept: %(a)s" %
               {'m': req.method, 'p': req.path, 'a': req.accept})
        LOG.debug(msg)

        # If the request is for /versions, just return the versions container
        if req.path_info_peek() in ("versions", ""):
            return self.versions_app

        accept = str(req.accept)

        # Check if there is a requested (micro-)version for API
        controller = self._get_controller(req.path_info_peek() or '', req)
        if controller:
            self._check_version_request(req, controller)
            major = req.environ['api.major']
            minor = req.environ['api.minor']
            LOG.debug("Matched versioned URI. Version: %(major)d.%(minor)d"
                      % {'major': major, 'minor': minor})
            # Strip the version from the path
            req.path_info_pop()
            path = req.path_info_peek()
            if path is None or path == '/':
                return controller(self.conf)
            return None
        else:
            LOG.debug("Unknown version in URI")

        # Try another path
        if accept.startswith('application/vnd.openstack.clustering-'):
            token_loc = len('application/vnd.openstack.clustering-')
            accept_version = accept[token_loc:]
            controller = self._get_controller(accept_version, req)
            if controller:
                self._check_version_request(req, controller)
                major = req.environ['api.major']
                minor = req.environ['api.minor']
                LOG.debug("Matched versioned media type. Version: "
                          "%(major)d.%(minor)d",
                          {'major': major, 'minor': minor})
                path = req.path_info_peek()
                if path is None or path == '/':
                    return controller(self.conf)
                return None
            else:
                LOG.debug("Unknown version in request header")

        if accept not in ('*/*', ''):
            LOG.debug("Returning HTTP 404 due to unknown Accept header: %s ",
                      accept)
            return webob.exc.HTTPNotFound()

        return self.versions_app

    def _get_controller(self, subject, req):
        """Get a version specific controller based on endpoint version.

        Given a subject string, tries to match a major and/or minor version
        number. If found, sets the api.major and api.minor environ variables.

        :param subject: The string to check
        :param req: Webob.Request object
        :returns: A version controller instance or None.
        """
        match = self.version_uri_regex.match(subject)
        if not match:
            return None

        major, minor = match.groups(0)
        major = int(major)
        minor = int(minor)
        req.environ['api.major'] = major
        req.environ['api.minor'] = minor
        version = '%s.%s' % (major, minor)
        return self.versions_app.get_controller(version)

    def _check_version_request(self, req, controller):
        """Set API version request based on the request header and controller.

        :param req: The webob.Request object.
        :param controller: The API version controller.
        :returns: ``None``
        :raises: ``HTTPBadRequest`` if API version string is bad.
        """
        api_version = mp.get_version(req.headers, service_type='clustering')
        if api_version is None:
            api_version = controller.DEFAULT_API_VERSION
        elif api_version.lower() == 'latest':
            req.version_request = controller.max_api_version()
            return

        try:
            ver = vr.APIVersionRequest(api_version)
        except exception.InvalidAPIVersionString as e:
            raise webob.exc.HTTPBadRequest(six.text_type(e))

        if not ver.matches(controller.min_api_version(),
                           controller.max_api_version()):
            raise exception.InvalidGlobalAPIVersion(
                req_ver=api_version,
                min_ver=six.text_type(controller.min_api_version()),
                max_ver=six.text_type(controller.max_api_version()))

        req.version_request = ver
