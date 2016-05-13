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

from senlin.common.i18n import _
from senlin.common import schema
from senlin.profiles import base


class DockerProfile(base.Profile):
    """Profile for a docker container."""

    KEYS = (
        CONTEXT, IMAGE, NAME, COMMAND,
    ) = (
        'context', 'image', 'name', 'command',
    )

    properties_schema = {
        CONTEXT: schema.Map(
            _('Customized security context for operationg containers.')
        ),
        IMAGE: schema.String(
            _('The image used to create a container')
        ),
        NAME: schema.String(
            _('The name of the container.')
        ),
        COMMAND: schema.String(
            _('The command to run when container is started.')
        ),
    }

    def __init__(self, type_name, name, **kwargs):
        super(DockerProfile, self).__init__(type_name, name, **kwargs)

        self._dockerclient = None
