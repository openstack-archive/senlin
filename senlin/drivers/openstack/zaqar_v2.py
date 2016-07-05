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

from oslo_log import log

from senlin.drivers import base
from senlin.drivers.openstack import sdk

LOG = log.getLogger(__name__)


class ZaqarClient(base.DriverBase):
    '''Zaqar V2 driver.'''

    def __init__(self, params):
        super(ZaqarClient, self).__init__(params)
        self.conn = sdk.create_connection(params)
        self.session = self.conn.session

    @sdk.translate_exception
    def queue_create(self, **attrs):
        return self.conn.message.create_queue(**attrs)

    @sdk.translate_exception
    def queue_get(self, queue):
        return self.conn.message.get_queue(queue)

    @sdk.translate_exception
    def queue_list(self, **query):
        return [q for q in self.conn.message.queues(**query)]

    @sdk.translate_exception
    def queue_delete(self, queue, ignore_missing=True):
        return self.conn.message.delete_queue(queue, ignore_missing)
