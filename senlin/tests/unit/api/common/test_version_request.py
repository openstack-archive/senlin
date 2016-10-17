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

from senlin.api.common import version_request as vr
from senlin.common import exception
from senlin.tests.unit.common import base


class APIVersionRequestTests(base.SenlinTestCase):

    def test_valid_version_strings(self):
        def _test_string(version, exp_major, exp_minor):
            v = vr.APIVersionRequest(version)
            self.assertEqual(v.major, exp_major)
            self.assertEqual(v.minor, exp_minor)

        _test_string("1.1", 1, 1)
        _test_string("2.10", 2, 10)
        _test_string("5.234", 5, 234)
        _test_string("12.5", 12, 5)
        _test_string("2.0", 2, 0)
        _test_string("2.200", 2, 200)

    def test_null_version(self):
        v = vr.APIVersionRequest()
        self.assertTrue(v.is_null())

    def test_invalid_version_strings(self):
        self.assertRaises(exception.InvalidAPIVersionString,
                          vr.APIVersionRequest, "2")

        self.assertRaises(exception.InvalidAPIVersionString,
                          vr.APIVersionRequest, "200")

        self.assertRaises(exception.InvalidAPIVersionString,
                          vr.APIVersionRequest, "2.1.4")

        self.assertRaises(exception.InvalidAPIVersionString,
                          vr.APIVersionRequest, "200.23.66.3")

        self.assertRaises(exception.InvalidAPIVersionString,
                          vr.APIVersionRequest, "5 .3")

        self.assertRaises(exception.InvalidAPIVersionString,
                          vr.APIVersionRequest, "5. 3")

        self.assertRaises(exception.InvalidAPIVersionString,
                          vr.APIVersionRequest, "5.03")

        self.assertRaises(exception.InvalidAPIVersionString,
                          vr.APIVersionRequest, "02.1")

        self.assertRaises(exception.InvalidAPIVersionString,
                          vr.APIVersionRequest, "2.001")

        self.assertRaises(exception.InvalidAPIVersionString,
                          vr.APIVersionRequest, "")

        self.assertRaises(exception.InvalidAPIVersionString,
                          vr.APIVersionRequest, " 2.1")

        self.assertRaises(exception.InvalidAPIVersionString,
                          vr.APIVersionRequest, "2.1 ")

    def test_version_comparisons(self):
        vers1 = vr.APIVersionRequest("2.0")
        vers2 = vr.APIVersionRequest("2.5")
        vers3 = vr.APIVersionRequest("5.23")
        vers4 = vr.APIVersionRequest("2.0")
        v_null = vr.APIVersionRequest()

        self.assertTrue(v_null < vers2)
        self.assertTrue(vers1 < vers2)
        self.assertTrue(vers1 <= vers2)
        self.assertTrue(vers1 <= vers4)
        self.assertTrue(vers2 > v_null)
        self.assertTrue(vers3 > vers2)
        self.assertTrue(vers1 >= vers4)
        self.assertTrue(vers3 >= vers2)
        self.assertTrue(vers1 != vers2)
        self.assertTrue(vers1 == vers4)
        self.assertTrue(vers1 != v_null)
        self.assertTrue(v_null == v_null)
        self.assertRaises(TypeError, vers1.__lt__, "2.1")

    def test_version_matches(self):
        vers1 = vr.APIVersionRequest("1.0")
        vers2 = vr.APIVersionRequest("1.1")
        vers3 = vr.APIVersionRequest("1.2")
        vers4 = vr.APIVersionRequest("1.3")
        v_null = vr.APIVersionRequest()

        self.assertTrue(vers2.matches(vers1, vers3))
        self.assertTrue(vers2.matches(vers1, vers4))
        self.assertTrue(vers2.matches(vers1, v_null))
        self.assertFalse(vers1.matches(vers2, vers3))
        self.assertFalse(vers1.matches(vers2, vers4))
        self.assertFalse(vers2.matches(vers4, vers1))

        self.assertRaises(ValueError, v_null.matches, vers1, vers4)

    def test_as_string(self):
        vers1_string = "3.23"
        vers1 = vr.APIVersionRequest(vers1_string)
        self.assertEqual(vers1_string, str(vers1))
