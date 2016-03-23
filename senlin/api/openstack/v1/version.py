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

from senlin.api.common import wsgi


class VersionController(wsgi.Controller):
    """WSGI controller for version in Senlin v1 API."""

    def __init__(self, conf):
        self.conf = conf

    def version(self, req):
        version_info = {
            'id': '1.0',
            'status': 'CURRENT',
            'updated': '2016-01-18T00:00:00Z',
            'media-types': [
                {
                    'base': 'application/json',
                    'type': 'application/vnd.openstack.clustering-v1+json'
                }
            ],
            'links': [
                {
                    'href': '.',
                    'rel': 'self'
                }
            ]
        }

        return {'version': version_info}
