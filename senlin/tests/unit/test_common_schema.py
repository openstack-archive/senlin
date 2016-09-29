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

import collections

import mock
import six

from senlin.common import exception as exc
from senlin.common import schema
from senlin.tests.unit.common import base


class FakeSchema(schema.SchemaBase):

    def __getitem__(self, key):
        if key == self.TYPE:
            return self.STRING
        return super(FakeSchema, self).__getitem__(key)

    def resolve(self, value):
        return str(value)

    def validate(self, value, context=None):
        return


class TestAnyIndexDict(base.SenlinTestCase):

    def test_basic(self):
        sot = schema.AnyIndexDict('*')

        self.assertIsInstance(sot, collections.Mapping)

        self.assertEqual('*', sot.value)
        self.assertEqual('*', sot[1])
        self.assertEqual('*', sot[2])
        self.assertEqual('*', sot['*'])

        for a in sot:
            self.assertEqual('*', a)

        self.assertEqual(1, len(sot))

    def test_bad_index(self):
        sot = schema.AnyIndexDict('*')

        ex = self.assertRaises(KeyError, sot.__getitem__, 'foo')

        # the following test is not interesting
        self.assertEqual("'Invalid key foo'", str(ex))


class TestSchemaBase(base.SenlinTestCase):

    def test_basic(self):
        sot = FakeSchema(description='desc', default='default', required=True,
                         schema=None, constraints=None, min_version='1.0',
                         max_version='2.0')
        self.assertEqual('desc', sot.description)
        self.assertEqual('default', sot.default)
        self.assertTrue(sot.required)
        self.assertIsNone(sot.schema)
        self.assertEqual([], sot.constraints)
        self.assertEqual('1.0', sot.min_version)
        self.assertEqual('2.0', sot.max_version)
        self.assertTrue(sot.has_default())

    def test_init_schema_invalid(self):
        ex = self.assertRaises(exc.InvalidSchemaError,
                               FakeSchema,
                               schema=mock.Mock())
        self.assertEqual('Schema valid only for List or Map, not String',
                         six.text_type(ex))

    def test_get_default(self):
        sot = FakeSchema(default='DEFAULT')
        mock_resolve = self.patchobject(sot, 'resolve', return_value='VVV')

        res = sot.get_default()

        self.assertEqual('VVV', res)
        mock_resolve.assert_called_once_with('DEFAULT')

    def test__validate_default(self):
        sot = FakeSchema()

        self.assertIsNone(sot._validate_default(mock.Mock()))

    def test__validate_default_with_value(self):
        sot = FakeSchema(default='DEFAULT')
        mock_validate = self.patchobject(sot, 'validate', return_value=None)
        fake_context = mock.Mock()

        res = sot._validate_default(fake_context)

        self.assertIsNone(res)
        mock_validate.assert_called_once_with('DEFAULT', fake_context)

    def test__validate_default_with_value_but_failed(self):
        sot = FakeSchema(default='DEFAULT')
        mock_validate = self.patchobject(sot, 'validate',
                                         side_effect=ValueError('boom'))
        fake_context = mock.Mock()

        ex = self.assertRaises(exc.InvalidSchemaError,
                               sot._validate_default,
                               fake_context)

        mock_validate.assert_called_once_with('DEFAULT', fake_context)
        self.assertEqual('Invalid default DEFAULT: boom', six.text_type(ex))

    def test_validate_constraints(self):
        c1 = mock.Mock()
        c2 = mock.Mock()
        sot = FakeSchema(constraints=[c1, c2])
        ctx = mock.Mock()

        res = sot.validate_constraints('VALUE', context=ctx)

        self.assertIsNone(res)
        c1.validate.assert_called_once_with('VALUE', schema=None, context=ctx)
        c2.validate.assert_called_once_with('VALUE', schema=None, context=ctx)

    def test_validate_constraints_failed(self):
        c1 = mock.Mock()
        c1.validate.side_effect = ValueError('BOOM')
        sot = FakeSchema(constraints=[c1])
        ctx = mock.Mock()

        ex = self.assertRaises(exc.SpecValidationFailed,
                               sot.validate_constraints,
                               'FOO', context=ctx)

        c1.validate.assert_called_once_with('FOO', schema=None, context=ctx)
        self.assertEqual('BOOM', six.text_type(ex))

    def test__validate_version(self):
        sot = FakeSchema(min_version='1.0', max_version='2.0')

        res = sot._validate_version('field', '1.0')
        self.assertIsNone(res)

        res = sot._validate_version('field', '1.1')
        self.assertIsNone(res)

        # there is a warning, but validation passes
        res = sot._validate_version('field', '2.0')
        self.assertIsNone(res)

        ex = self.assertRaises(exc.SpecValidationFailed,
                               sot._validate_version,
                               'field', '0.9')
        self.assertEqual('field (min_version=1.0) is not supported by '
                         'spec version 0.9.',
                         six.text_type(ex))

        ex = self.assertRaises(exc.SpecValidationFailed,
                               sot._validate_version,
                               'field', '2.1')
        self.assertEqual('field (max_version=2.0) is not supported by '
                         'spec version 2.1.',
                         six.text_type(ex))

    def test__validate_version_no_min_version(self):
        sot = FakeSchema(max_version='2.0')

        res = sot._validate_version('field', '1.0')
        self.assertIsNone(res)

        res = sot._validate_version('field', '2.0')
        self.assertIsNone(res)

        ex = self.assertRaises(exc.SpecValidationFailed,
                               sot._validate_version,
                               'field', '2.1')
        self.assertEqual('field (max_version=2.0) is not supported by '
                         'spec version 2.1.',
                         six.text_type(ex))

    def test__validate_version_no_max_version(self):
        sot = FakeSchema(min_version='1.0')

        res = sot._validate_version('field', '1.0')
        self.assertIsNone(res)

        res = sot._validate_version('field', '2.3')
        self.assertIsNone(res)

        ex = self.assertRaises(exc.SpecValidationFailed,
                               sot._validate_version,
                               'field', '0.5')
        self.assertEqual('field (min_version=1.0) is not supported by '
                         'spec version 0.5.',
                         six.text_type(ex))

    def test__validate_version_no_version_resitriction(self):
        sot = FakeSchema()

        res = sot._validate_version('field', '1.0')
        self.assertIsNone(res)

        res = sot._validate_version('field', '2.3')
        self.assertIsNone(res)

    def test__getitem__(self):
        sot = FakeSchema(description='desc', default='default', required=False,
                         constraints=[{'foo': 'bar'}])

        self.assertEqual('desc', sot['description'])
        self.assertEqual('default', sot['default'])
        self.assertEqual(False, sot['required'])
        self.assertEqual([{'foo': 'bar'}], sot['constraints'])
        self.assertRaises(KeyError, sot.__getitem__, 'bogus')

        sot = schema.List(schema=schema.String())
        self.assertEqual(
            {
                '*': {
                    'required': False,
                    'type': 'String',
                    'updatable': False
                }
            },
            sot['schema'])

    def test__iter__(self):
        sot = FakeSchema(description='desc', default='default', required=False,
                         constraints=[{'foo': 'bar'}])

        res = list(iter(sot))

        self.assertIn('type', res)
        self.assertIn('description', res)
        self.assertIn('default', res)
        self.assertIn('required', res)
        self.assertIn('constraints', res)

    def test__len__(self):
        sot = FakeSchema()

        res = list(iter(sot))

        self.assertIn('type', res)
        self.assertIn('required', res)
        self.assertEqual(2, len(sot))


class TestPropertySchema(base.SenlinTestCase):

    def setUp(self):
        super(TestPropertySchema, self).setUp()

        class TestProperty(schema.PropertySchema):

            def __getitem__(self, key):
                if key == self.TYPE:
                    return 'TEST'
                return super(TestProperty, self).__getitem__(key)

        self.cls = TestProperty

    def test_basic(self):
        sot = self.cls()

        self.assertIsNone(sot.description)
        self.assertIsNone(sot.default)
        self.assertFalse(sot.required)
        self.assertIsNone(sot.schema)
        self.assertEqual([], sot.constraints)
        self.assertIsNone(sot.min_version)
        self.assertIsNone(sot.max_version)
        self.assertFalse(sot.updatable)

    def test__getitem__(self):
        sot = self.cls(updatable=True)

        res = sot['updatable']

        self.assertTrue(res)
        self.assertTrue(sot.updatable)


class TestBoolean(base.SenlinTestCase):

    pass
