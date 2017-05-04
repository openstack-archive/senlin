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

import datetime
import os
import time

import fixtures
from oslo_config import cfg
from oslo_log import log as logging
from oslo_serialization import jsonutils
import six
import testscenarios
import testtools

from senlin.common import messaging
from senlin.engine import scheduler
from senlin.tests.unit.common import utils


TEST_DEFAULT_LOGLEVELS = {'migrate': logging.WARN,
                          'sqlalchemy': logging.WARN}
_LOG_FORMAT = "%(levelname)8s [%(name)s] %(message)s"
_TRUE_VALUES = ('True', 'true', '1', 'yes')


class FakeLogMixin(object):
    def setup_logging(self):
        # Assign default logs to self.LOG so we can still
        # assert on senlin logs.
        default_level = logging.INFO
        if os.environ.get('OS_DEBUG') in _TRUE_VALUES:
            default_level = logging.DEBUG

        self.LOG = self.useFixture(
            fixtures.FakeLogger(level=default_level, format=_LOG_FORMAT))
        base_list = set([nlog.split('.')[0] for nlog in
                         logging.getLogger().logger.manager.loggerDict])
        for base in base_list:
            if base in TEST_DEFAULT_LOGLEVELS:
                self.useFixture(fixtures.FakeLogger(
                    level=TEST_DEFAULT_LOGLEVELS[base],
                    name=base, format=_LOG_FORMAT))
            elif base != 'senlin':
                self.useFixture(fixtures.FakeLogger(
                    name=base, format=_LOG_FORMAT))


class SenlinTestCase(testscenarios.WithScenarios,
                     testtools.TestCase, FakeLogMixin):

    TIME_STEP = 0.1

    def setUp(self):
        super(SenlinTestCase, self).setUp()
        self.setup_logging()
        scheduler.ENABLE_SLEEP = False
        self.useFixture(fixtures.MonkeyPatch(
            'senlin.common.exception._FATAL_EXCEPTION_FORMAT_ERRORS',
            True))

        def enable_sleep():
            scheduler.ENABLE_SLEEP = True

        self.addCleanup(enable_sleep)
        self.addCleanup(cfg.CONF.reset)

        messaging.setup("fake://", optional=True)
        self.addCleanup(messaging.cleanup)

        utils.setup_dummy_db()
        self.addCleanup(utils.reset_dummy_db)

    def stub_wallclock(self):
        # Overrides scheduler wallclock to speed up tests expecting timeouts.
        self._wallclock = time.time()

        def fake_wallclock():
            self._wallclock += self.TIME_STEP
            return self._wallclock

        self.m.StubOutWithMock(scheduler, 'wallclock')
        scheduler.wallclock = fake_wallclock

    def patchobject(self, obj, attr, **kwargs):
        mockfixture = self.useFixture(fixtures.MockPatchObject(obj, attr,
                                                               **kwargs))
        return mockfixture.mock

    # NOTE(pshchelo): this overrides the testtools.TestCase.patch method
    # that does simple monkey-patching in favor of mock's patching
    def patch(self, target, **kwargs):
        mockfixture = self.useFixture(fixtures.MockPatch(target, **kwargs))
        return mockfixture.mock

    def assertJsonEqual(self, expected, observed):
        """Asserts that 2 complex data structures are json equivalent.

        This code is from Nova.
        """
        if isinstance(expected, six.string_types):
            expected = jsonutils.loads(expected)
        if isinstance(observed, six.string_types):
            observed = jsonutils.loads(observed)

        def sort_key(x):
            if isinstance(x, (set, list)) or isinstance(x, datetime.datetime):
                return str(x)
            if isinstance(x, dict):
                items = ((sort_key(k), sort_key(v)) for k, v in x.items())
                return sorted(items)
            return x

        def inner(expected, observed):
            if isinstance(expected, dict) and isinstance(observed, dict):
                self.assertEqual(len(expected), len(observed))
                expected_keys = sorted(expected)
                observed_keys = sorted(observed)
                self.assertEqual(expected_keys, observed_keys)

                for key in list(expected.keys()):
                    inner(expected[key], observed[key])
            elif (isinstance(expected, (list, tuple, set)) and
                  isinstance(observed, (list, tuple, set))):
                self.assertEqual(len(expected), len(observed))

                expected_values_iter = iter(sorted(expected, key=sort_key))
                observed_values_iter = iter(sorted(observed, key=sort_key))

                for i in range(len(expected)):
                    inner(next(expected_values_iter),
                          next(observed_values_iter))
            else:
                self.assertEqual(expected, observed)

        try:
            inner(expected, observed)
        except testtools.matchers.MismatchError as e:
            inner_mismatch = e.mismatch
            # inverting the observed / expected because testtools
            # error messages assume expected is second. Possibly makes
            # reading the error messages less confusing.
            raise testtools.matchers.MismatchError(
                observed, expected, inner_mismatch, verbose=True)
