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

import eventlet
import oslo_i18n

from senlin import objects


def fake_translate_msgid(msgid, domain, desired_locale=None):
    return msgid

oslo_i18n.enable_lazy()

# To ensure messages don't really get translated while running tests.
# As there are lots of places where matching is expected when comparing
# exception message(translated) with raw message.
oslo_i18n._translate_msgid = fake_translate_msgid

eventlet.monkey_patch(os=False)

# The following has to be done after eventlet monkey patching or else the
# threading.local() store used in oslo_messaging will be initialized to
# thread-local storage rather than green-thread local. This will cause context
# sets and deletes in that storage to clobber each other.
# Make sure we have all objects loaded. This is done at module import time,
# because we may be using mock decorators in our tests that run at import
# time.
objects.register_all()
