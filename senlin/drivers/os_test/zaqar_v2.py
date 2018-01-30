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

FAKE_SUBSCRIPTION_ID = "0d8dbb71-1538-42ac-99fb-bb52d0ad1b6f"
FAKE_MESSAGE_ID = "51db6f78c508f17ddc924357"
FAKE_CLAIM_ID = "51db7067821e727dc24df754"


class ZaqarClient(base.DriverBase):
    '''Fake zaqar V2 driver for test.'''

    def __init__(self, ctx):
        self.fake_subscription = {
            "subscription_id": FAKE_SUBSCRIPTION_ID
        }
        self.fake_claim = {
            "messages": [
                {
                    "body": {
                        "event": "BackupStarted"
                    },
                    "age": 239,
                    "href": "/v2/queues/demoqueue/messages/" +
                            FAKE_MESSAGE_ID + "?claim_id=" + FAKE_CLAIM_ID,
                    "ttl": 300
                }
            ]
        }
        self.fake_message = {
            "resources": [
                "/v2/queues/demoqueue/messages/" + FAKE_MESSAGE_ID
            ]
        }

    def queue_create(self, **attrs):
        return

    def queue_exists(self, queue_name):
        return True

    def queue_delete(self, queue, ignore_missing=True):
        return None

    def subscription_create(self, queue_name, **attrs):
        return sdk.FakeResourceObject(self.fake_subscription)

    def subscription_delete(self, queue_name, subscription,
                            ignore_missing=True):
        return None

    def claim_create(self, queue_name, **attrs):
        return sdk.FakeResourceObject(self.fake_claim)

    def claim_delete(self, queue_name, claim, ignore_missing=True):
        return None

    def message_delete(self, queue_name, message, claim_id=None,
                       ignore_missing=True):
        return None

    def message_post(self, queue_name, message):
        return sdk.FakeResourceObject(self.fake_message)
