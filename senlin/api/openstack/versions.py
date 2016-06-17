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
Controller that returns information on the senlin API versions
"""

from oslo_serialization import jsonutils
from oslo_utils import encodeutils
from six.moves import http_client
import webob.dec

from senlin.api.common import version_request as vr


# NOTE: A version change is required when you make any change to the API. This
# includes any semantic changes which may not affect the input or output
# formats or even originate in the API code layer.
#
# The minimum and maximum versions of the API supported, where the default api
# version request is defined to be the minimum version supported.
_MIN_API_VERSION = "1.0"
_MAX_API_VERSION = "1.2"
DEFAULT_API_VERSION = _MIN_API_VERSION


# min and max versions declared as functions so we can mock them for unittests.
# Do not use the constants directly anywhere else.
def min_api_version():
    return vr.APIVersionRequest(_MIN_API_VERSION)


def max_api_version():
    return vr.APIVersionRequest(_MAX_API_VERSION)


def is_supported(req, min_version=_MIN_API_VERSION,
                 max_version=_MAX_API_VERSION):
    """Check if API request version satisfies version restrictions.

    :param req: request object
    :param min_version: minimal version of API needed.
    :param max_version: maximum version of API needed.
    :returns: True if request satisfies minimal and maximum API version
             requirements. False in other case.
    """
    return (vr.APIVersionRequest(max_version) >= req.version_request >=
            vr.APIVersionRequest(min_version))


class Controller(object):
    """A controller that produces information on the senlin API versions."""

    def __init__(self, conf):
        self.conf = conf

    @webob.dec.wsgify
    def __call__(self, req):
        """Respond to a request for all OpenStack API versions."""
        version_objs = [
            {
                "id": "1.0",
                "status": "CURRENT",
                "updated": "2016-01-18T00:00:00Z",
                "media-types": [
                    {
                        "base": "application/json",
                        "type": "application/vnd.openstack.clustering-v1+json"
                    }
                ],
                "links": [
                    {
                        "rel": "self",
                        "href": "/v1/"
                    }
                ],
                "min_version": _MIN_API_VERSION,
                "max_version": _MAX_API_VERSION,
            }]

        body = jsonutils.dumps(dict(versions=version_objs))

        response = webob.Response(request=req,
                                  status=http_client.MULTIPLE_CHOICES,
                                  content_type='application/json')
        response.body = encodeutils.safe_encode(body)

        return response
