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

import mock
import pep8
import textwrap

from senlin.hacking import checks
from senlin.tests.unit.common import base


class HackingTestCase(base.SenlinTestCase):
    @mock.patch('pep8._checks',
                {'physical_line': {}, 'logical_line': {}, 'tree': {}})
    def _run_check(self, code, checker, filename=None):
        pep8.register_check(checker)

        lines = textwrap.dedent(code).strip().splitlines(True)

        checker = pep8.Checker(filename=filename, lines=lines)
        checker.check_all()
        checker.report._deferred_print.sort()
        return checker.report._deferred_print

    def _assert_has_errors(self, code, checker, expected_errors=None,
                           filename=None):
        actual_errors = [e[:3] for e in
                         self._run_check(code, checker, filename)]
        self.assertEqual(expected_errors or [], actual_errors)

    def _assert_has_no_errors(self, code, checker, filename=None):
        self._assert_has_errors(code, checker, filename=filename)

    def test_assert_equal_none(self):
        self.assertEqual(1, len(list(checks.assert_equal_none(
            "self.assertEqual(A, None)"))))

        self.assertEqual(1, len(list(checks.assert_equal_none(
            "self.assertEqual(None, A)"))))

        self.assertEqual(0, len(list(checks.assert_equal_none(
            "self.assertIsNone()"))))

    def test_use_jsonutils(self):
        def __get_msg(fun):
            msg = ("S319: jsonutils.%(fun)s must be used instead of "
                   "json.%(fun)s" % {'fun': fun})
            return [(0, msg)]

        for method in ('dump', 'dumps', 'load', 'loads'):
            self.assertEqual(__get_msg(method), list(checks.use_jsonutils(
                "json.%s(" % method, "./senlin/engine/cluster.py")))
            self.assertEqual(0, len(list(checks.use_jsonutils(
                "jsonx.%s(" % method, "./senlin/engine/cluster.py"))))
        self.assertEqual(0, len(list(checks.use_jsonutils(
            "json.dumb", "./senlin/engine/cluster.py"))))

    def test_no_mutable_default_args(self):
        self.assertEqual(1, len(list(checks.no_mutable_default_args(
            "def create_cluster(mapping={}, **params)"))))

        self.assertEqual(0, len(list(checks.no_mutable_default_args(
            "defined = []"))))

        self.assertEqual(0, len(list(checks.no_mutable_default_args(
            "defined, undefined = [], {}"))))

    def test_api_version_decorator(self):
        code = """
            @some_other_decorator
            @wsgi.api_version("2.2")
            def my_method():
                pass
            """

        actual_error = self._run_check(code,
                                       checks.check_api_version_decorator)[0]

        self.assertEqual(2, actual_error[0])
        self.assertEqual(0, actual_error[1])
        self.assertEqual('S321', actual_error[2])
        self.assertEqual(' The api_version decorator must be the first '
                         'decorator on a method.',
                         actual_error[3])

    def test_api_version_decorator_good(self):
        code = """
            class SomeController():
                @wsgi.api_version("2.2")
                def my_method():
                    pass

            """

        actual_error = self._run_check(code,
                                       checks.check_api_version_decorator)
        self.assertEqual(0, len(actual_error))

    def test_no_log_warn(self):
        code = """
                  LOG.warn("LOG.warn is deprecated")
               """
        errors = [(1, 0, 'S322')]
        self._assert_has_errors(code, checks.no_log_warn,
                                expected_errors=errors)
        code = """
                  LOG.warning("LOG.warn is deprecated")
               """
        self._assert_has_no_errors(code, checks.no_log_warn)

    def test_assert_equal_true(self):
        test_value = True
        self.assertEqual(0, len(list(checks.assert_equal_true(
            "assertTrue(True)"))))
        self.assertEqual(1, len(list(checks.assert_equal_true(
            "assertEqual(True, %s)" % test_value))))
        self.assertEqual(1, len(list(checks.assert_equal_true(
            "assertEqual(%s, True)" % test_value))))
