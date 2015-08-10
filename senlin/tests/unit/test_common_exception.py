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


import fixtures
import six

from senlin.common import exception
from senlin.common.i18n import _
from senlin.tests.unit.common import base


class TestException(exception.SenlinException):
    msg_fmt = _("Testing message %(text)s")


class TestSenlinException(base.SenlinTestCase):

    def test_fatal_exception_error(self):
        self.useFixture(fixtures.MonkeyPatch(
            'senlin.common.exception._FATAL_EXCEPTION_FORMAT_ERRORS',
            True))
        self.assertRaises(KeyError, TestException)

    def test_format_string_error_message(self):
        message = "This format %(message)s should work"
        err = exception.Error(message)
        self.assertEqual(message, six.text_type(err))
