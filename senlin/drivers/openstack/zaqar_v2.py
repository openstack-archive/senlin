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
from senlin.drivers.openstack import sdk


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

    @sdk.translate_exception
    def message_post(self, queue_name, messages):
        return self.conn.message.post_message(queue_name, messages)

    @sdk.translate_exception
    def message_list(self, queue_name, **query):
        return [m for m in self.conn.message.messages(queue_name, **query)]

    @sdk.translate_exception
    def message_get(self, queue_name, message):
        return self.conn.message.get_message(queue_name, message)

    @sdk.translate_exception
    def message_delete(self, queue_name, message, ignore_missing=True):
        return self.conn.message.delete_message(queue_name, message,
                                                ignore_missing)

    @sdk.translate_exception
    def subscription_create(self, queue_name, **attrs):
        return self.conn.message.create_subscription(queue_name, **attrs)

    @sdk.translate_exception
    def subscription_list(self, queue_name, **query):
        return [s for s in self.conn.message.subscriptions(queue_name,
                                                           **query)]

    @sdk.translate_exception
    def subscription_get(self, queue_name, subscription):
        return self.conn.message.get_subscription(queue_name, subscription)

    @sdk.translate_exception
    def subscription_delete(self, queue_name, subscription,
                            ignore_missing=True):
        return self.conn.message.delete_subscription(queue_name, subscription,
                                                     ignore_missing)

    @sdk.translate_exception
    def claim_create(self, queue_name, **attrs):
        return self.conn.message.create_claim(queue_name, **attrs)

    @sdk.translate_exception
    def claim_update(self, queue_name, claim, **attrs):
        return self.conn.message.update_claim(queue_name, claim, **attrs)

    @sdk.translate_exception
    def claim_get(self, queue_name, claim):
        return self.conn.message.get_claim(queue_name, claim)

    @sdk.translate_exception
    def claim_delete(self, queue_name, claim, ignore_missing=True):
        return self.conn.message.delete_claim(queue_name, claim,
                                              ignore_missing)
