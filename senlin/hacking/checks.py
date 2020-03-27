# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

import re

from hacking import core

asse_equal_end_with_none_re = re.compile(r"assertEqual\(.*?,\s+None\)$")
asse_equal_start_with_none_re = re.compile(r"assertEqual\(None,")
asse_equal_start_with_true_re = re.compile(r"assertEqual\(True,")
asse_equal_end_with_true_re = re.compile(r"assertEqual\(.*?,\s+True\)$")
mutable_default_args = re.compile(r"^\s*def .+\((.+=\{\}|.+=\[\])")
api_version_dec = re.compile(r"@.*api_version")
decorator_re = re.compile(r"@.*")


@core.flake8ext
def assert_equal_none(logical_line):
    """Check for assertEqual(A, None) or assertEqual(None, A) sentences

    S318
    """
    res = (asse_equal_start_with_none_re.search(logical_line) or
           asse_equal_end_with_none_re.search(logical_line))
    if res:
        yield (0, "S318: assertEqual(A, None) or assertEqual(None, A) "
               "sentences not allowed")


@core.flake8ext
def use_jsonutils(logical_line, filename):
    msg = "S319: jsonutils.%(fun)s must be used instead of json.%(fun)s"

    if "json." in logical_line:
        json_funcs = ['dumps(', 'dump(', 'loads(', 'load(']
        for f in json_funcs:
            pos = logical_line.find('json.%s' % f)
            if pos != -1:
                yield (pos, msg % {'fun': f[:-1]})


@core.flake8ext
def no_mutable_default_args(logical_line):
    msg = "S320: Method's default argument shouldn't be mutable!"
    if mutable_default_args.match(logical_line):
        yield (0, msg)


@core.flake8ext
def no_log_warn(logical_line):
    """Disallow 'LOG.warn('

    Deprecated LOG.warn(), instead use LOG.warning
    https://bugs.launchpad.net/senlin/+bug/1508442

    S322
    """

    msg = ("S322: LOG.warn is deprecated, please use LOG.warning!")
    if "LOG.warn(" in logical_line:
        yield (0, msg)


@core.flake8ext
def assert_equal_true(logical_line):
    """Check for assertEqual(A, True) or assertEqual(True, A) sentences

    S323
    """
    res = (asse_equal_start_with_true_re.search(logical_line) or
           asse_equal_end_with_true_re.search(logical_line))
    if res:
        yield (0, "S323: assertEqual(A, True) or assertEqual(True, A) "
               "sentences not allowed")


@core.flake8ext
def check_api_version_decorator(logical_line, previous_logical, blank_before,
                                filename):
    msg = ("S321: The api_version decorator must be the first decorator on "
           "a method.")
    if (blank_before == 0 and re.match(api_version_dec, logical_line) and
            re.match(decorator_re, previous_logical)):
        yield(0, msg)
