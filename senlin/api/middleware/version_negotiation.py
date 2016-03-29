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

from oslo_log import log as logging
import six
import webob

from senlin.api.common import version_request as vr
from senlin.api.common import wsgi
from senlin.api.openstack import versions as os_ver
from senlin.common import exception

LOG = logging.getLogger(__name__)


class VersionNegotiationFilter(wsgi.Middleware):

    def __init__(self, version_controller, app, conf, **local_conf):
        self.versions_app = version_controller(conf)
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

        # Check if there is a requested (micro-)version for API
        self.check_version_request(req)
        match = self._match_version_string(req.path_info_peek(), req)
        if match:
            major = req.environ['api.major']
            minor = req.environ['api.minor']

            if (major == 1 and minor == 0):
                LOG.debug("Matched versioned URI. Version: %(major)d.%(minor)d"
                          % {'major': major, 'minor': minor})
                # Strip the version from the path
                req.path_info_pop()
                return None
            else:
                LOG.debug("Unknown version in versioned URI: "
                          "%(major)d.%(minor)d. Returning version choices."
                          % {'major': major, 'minor': minor})
                return self.versions_app

        accept = str(req.accept)
        if accept.startswith('application/vnd.openstack.clustering-'):
            token_loc = len('application/vnd.openstack.clustering-')
            accept_version = accept[token_loc:]
            match = self._match_version_string(accept_version, req)
            if match:
                major = req.environ['api.major']
                minor = req.environ['api.minor']
                if (major == 1 and minor == 0):
                    LOG.debug("Matched versioned media type. Version: "
                              "%(major)d.%(minor)d"
                              % {'major': major, 'minor': minor})
                    return None
                else:
                    LOG.debug("Unknown version in accept header: "
                              "%(major)d.%(minor)d..."
                              "returning version choices."
                              % {'major': major, 'minor': minor})
                    return self.versions_app
        else:
            if req.accept not in ('*/*', ''):
                LOG.debug("Returning HTTP 404 due to unknown Accept header: "
                          "%s ", req.accept)
            return webob.exc.HTTPNotFound()

        return None

    def _match_version_string(self, subject, req):
        """Do version matching.

        Given a subject string, tries to match a major and/or minor version
        number. If found, sets the api.major and api.minor environ variables.

        :param subject: The string to check
        :param req: Webob.Request object
        :returns: True if there was a match, false otherwise.
        """
        match = self.version_uri_regex.match(subject)
        if match:
            major, minor = match.groups(0)
            major = int(major)
            minor = int(minor)
            req.environ['api.major'] = major
            req.environ['api.minor'] = minor

        return match is not None

    def check_version_request(self, req):
        """Set API version request based on the request header."""
        api_version = wsgi.DEFAULT_API_VERSION
        key = wsgi.API_VERSION_KEY
        if key in req.headers:
            versions = req.headers[key].split(',')
            for version in versions:
                svc_ver = version.strip().split(' ')
                if svc_ver[0].lower() in wsgi.SERVICE_ALIAS:
                    api_version = svc_ver[1]
                    break
        if api_version.lower() == 'latest':
            req.version_request = os_ver.max_api_version()
            return

        try:
            ver = vr.APIVersionRequest(api_version)
        except exception.InvalidAPIVersionString as e:
            raise webob.exc.HTTPBadRequest(six.text_type(e))

        if not ver.matches(os_ver.min_api_version(), os_ver.max_api_version()):
            raise exception.InvalidGlobalAPIVersion(
                req_ver=api_version,
                min_ver=six.text_type(os_ver.min_api_version()),
                max_ver=six.text_type(os_ver.max_api_version()))

        req.version_request = ver
