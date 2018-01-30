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

from senlin.drivers import base
from senlin.drivers import sdk


class GlanceClient(base.DriverBase):
    """Glance V2 driver."""

    def __init__(self, params):
        super(GlanceClient, self).__init__(params)
        self.conn = sdk.create_connection(params)
        self.session = self.conn.session

    @sdk.translate_exception
    def image_find(self, name_or_id, ignore_missing=True):
        return self.conn.image.find_image(name_or_id, ignore_missing)

    @sdk.translate_exception
    def image_get(self, image):
        return self.conn.image.get_image(image)

    @sdk.translate_exception
    def image_delete(self, name_or_id, ignore_missing=False):
        return self.conn.image.delete_image(name_or_id, ignore_missing)
