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
import tempfile
import time

import fixtures
from oslo_config import cfg
from oslo_db import options
from oslo_log import log as logging
from oslo_serialization import jsonutils
import shutil
import testscenarios
import testtools

from senlin.common import messaging
from senlin.db import api as db_api
from senlin.engine import service


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


class DatabaseFixture(fixtures.Fixture):
    fixture = None

    @staticmethod
    def mktemp():
        tmpfs_path = '/dev/shm'
        if not os.path.isdir(tmpfs_path):
            tmpfs_path = '/tmp'
        return tempfile.mkstemp(
            prefix='senlin-', suffix='.sqlite', dir=tmpfs_path)[1]

    @staticmethod
    def get_fixture():
        if not DatabaseFixture.fixture:
            DatabaseFixture.fixture = DatabaseFixture()
        return DatabaseFixture.fixture

    def __init__(self):
        super(DatabaseFixture, self).__init__()
        self.golden_path = self.mktemp()
        self.golden_url = 'sqlite:///%s' % self.golden_path
        db_api.db_sync(self.golden_url)
        self.working_path = self.mktemp()
        self.working_url = 'sqlite:///%s' % self.working_path

    def setUp(self):
        super(DatabaseFixture, self).setUp()
        shutil.copy(self.golden_path, self.working_path)

    def cleanup(self):
        if os.path.exists(self.working_path):
            os.remove(self.working_path)


class SenlinTestCase(testscenarios.WithScenarios,
                     testtools.TestCase, FakeLogMixin):

    TIME_STEP = 0.1

    def setUp(self):
        super(SenlinTestCase, self).setUp()
        self.setup_logging()
        service.ENABLE_SLEEP = False
        self.useFixture(fixtures.MonkeyPatch(
            'senlin.common.exception._FATAL_EXCEPTION_FORMAT_ERRORS',
            True))

        def enable_sleep():
            service.ENABLE_SLEEP = True

        self.addCleanup(enable_sleep)
        self.addCleanup(cfg.CONF.reset)

        messaging.setup("fake://", optional=True)
        self.addCleanup(messaging.cleanup)

        self.db_fixture = self.useFixture(DatabaseFixture.get_fixture())
        self.addCleanup(self.db_fixture.cleanup)

        options.cfg.set_defaults(
            options.database_opts, sqlite_synchronous=False
        )
        options.set_defaults(cfg.CONF, connection=self.db_fixture.working_url)

    def stub_wallclock(self):
        # Overrides scheduler wallclock to speed up tests expecting timeouts.
        self._wallclock = time.time()

        def fake_wallclock():
            self._wallclock += self.TIME_STEP
            return self._wallclock

        self.m.StubOutWithMock(service, 'wallclock')
        service.wallclock = fake_wallclock

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
        if isinstance(expected, str):
            expected = jsonutils.loads(expected)
        if isinstance(observed, str):
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
