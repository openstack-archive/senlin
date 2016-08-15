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

from senlin.api.openstack.v1 import version as v1_controller


class Controller(object):
    """A controller that produces information on the senlin API versions."""

    Controllers = {
        '1.0': v1_controller.VersionController,
    }

    def __init__(self, conf):
        self.conf = conf

    @webob.dec.wsgify
    def __call__(self, req):
        """Respond to a request for all OpenStack API versions."""

        versions = []
        for ver, vc in self.Controllers.items():
            versions.append(vc.version_info())

        body = jsonutils.dumps(dict(versions=versions))

        response = webob.Response(request=req,
                                  status=http_client.MULTIPLE_CHOICES,
                                  content_type='application/json')
        response.body = encodeutils.safe_encode(body)

        return response

    def get_controller(self, version):
        """Return the version specific controller.

        :param version: The version string for mapping.
        :returns: A version controller instance or ``None``.
        """
        return self.Controllers.get(version, None)
