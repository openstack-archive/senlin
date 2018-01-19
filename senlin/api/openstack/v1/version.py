# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

from oslo_serialization import jsonutils
from oslo_utils import encodeutils
import webob.dec

from senlin.api.common import version_request as vr


class VersionController(object):
    """WSGI controller for version in Senlin v1 API."""

    # NOTE: A version change is required when you make any change to the API.
    # This includes any semantic changes which may not affect the input or
    # output formats or even originate in the API code layer.
    _MIN_API_VERSION = "1.0"
    _MAX_API_VERSION = "1.9"

    DEFAULT_API_VERSION = _MIN_API_VERSION

    def __init__(self, conf):
        self.conf = conf

    @webob.dec.wsgify
    def __call__(self, req):
        info = self.version(req)
        body = jsonutils.dumps(info)
        response = webob.Response(request=req, content_type='application/json')
        response.body = encodeutils.safe_encode(body)

        return response

    @classmethod
    def version_info(cls):
        return {
            "id": "1.0",
            "status": "CURRENT",
            "updated": "2016-01-18T00:00:00Z",
            "media-types": [
                {
                    "base": "application/json",
                    "type": "application/vnd.openstack.clustering-v1+json"
                }
            ],
            "links": [{
                "href": "/v1",
                "rel": "self"}, {
                "rel": "help",
                "href": "https://developer.openstack.org/api-ref/clustering"
            }],
            "min_version": cls._MIN_API_VERSION,
            "max_version": cls._MAX_API_VERSION,
        }

    def version(self, req):
        return {"version": self.version_info()}

    @classmethod
    def min_api_version(cls):
        return vr.APIVersionRequest(cls._MIN_API_VERSION)

    @classmethod
    def max_api_version(cls):
        return vr.APIVersionRequest(cls._MAX_API_VERSION)

    @classmethod
    def is_supported(cls, req, min_ver=None, max_ver=None):
        """Check if API request version satisfies version restrictions.

        :param req: request object
        :param min_ver: minimal version of API needed.
        :param max_ver: maximum version of API needed.
        :returns: True if request satisfies minimal and maximum API version
                 requirements. False in other case.
        """
        min_version = min_ver or cls._MIN_API_VERSION
        max_version = max_ver or cls._MAX_API_VERSION
        return (vr.APIVersionRequest(max_version) >= req.version_request >=
                vr.APIVersionRequest(min_version))
