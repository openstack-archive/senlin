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

import testtools

from senlin.common import exception as senlin_exc
from senlin.objects.notifications import exception as exception_notification


class TestExceptionPayload(testtools.TestCase):

    def test_create(self):
        ex = exception_notification.ExceptionPayload(
            module='fake_module',
            function='fake_function',
            exception='fake_exception',
            message='fake_message')

        self.assertEqual('fake_module', ex.module)
        self.assertEqual('fake_function', ex.function)
        self.assertEqual('fake_exception', ex.exception)
        self.assertEqual('fake_message', ex.message)

    def test_create_from_exception(self):
        ex = None
        pload = None

        try:
            {}['key']
        except Exception:
            ex = senlin_exc.BadRequest(msg="It is really bad.")
            pload = exception_notification.ExceptionPayload.from_exception(ex)

        self.assertIsNotNone(ex)
        self.assertIsNotNone(pload)

        # 'senlin.tests.unit.objects.notifications.test_exception',
        self.assertEqual(self.__module__, pload.module)
        self.assertEqual('test_create_from_exception', pload.function)
        self.assertEqual('BadRequest', pload.exception)
        self.assertEqual('The request is malformed: It is really bad.',
                         pload.message)
