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

from senlin.common import constraints
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
        ex = self.assertRaises(exc.ESchema, FakeSchema, schema=mock.Mock())
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

        ex = self.assertRaises(exc.ESchema,
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

        ex = self.assertRaises(exc.ESchema,
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

        ex = self.assertRaises(exc.ESchema,
                               sot._validate_version,
                               'field', '0.9')
        self.assertEqual('field (min_version=1.0) is not supported by '
                         'spec version 0.9.',
                         six.text_type(ex))

        ex = self.assertRaises(exc.ESchema,
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

        ex = self.assertRaises(exc.ESchema,
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

        ex = self.assertRaises(exc.ESchema,
                               sot._validate_version,
                               'field', '0.5')
        self.assertEqual('field (min_version=1.0) is not supported by '
                         'spec version 0.5.',
                         six.text_type(ex))

    def test__validate_version_no_version_restriction(self):
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

    def test_basic(self):
        sot = schema.Boolean('desc')

        self.assertEqual('Boolean', sot['type'])
        self.assertEqual('desc', sot['description'])

    def test_to_schema_type(self):
        sot = schema.Boolean('desc')

        res = sot.to_schema_type(True)
        self.assertTrue(res)

        res = sot.to_schema_type('true')
        self.assertTrue(res)

        res = sot.to_schema_type('trUE')
        self.assertTrue(res)

        res = sot.to_schema_type('False')
        self.assertFalse(res)

        res = sot.to_schema_type('FALSE')
        self.assertFalse(res)

        ex = self.assertRaises(exc.ESchema, sot.to_schema_type, 'bogus')
        self.assertEqual("The value 'bogus' is not a valid Boolean",
                         six.text_type(ex))

    def test_resolve(self):
        sot = schema.Boolean()

        res = sot.resolve(True)
        self.assertTrue(res)

        res = sot.resolve(False)
        self.assertFalse(res)

        res = sot.resolve('Yes')
        self.assertTrue(res)

    def test_validate(self):
        sot = schema.Boolean()

        res = sot.validate(True)
        self.assertIsNone(res)

        res = sot.validate('No')
        self.assertIsNone(res)

        ex = self.assertRaises(exc.ESchema, sot.validate, 'bogus')
        self.assertEqual("The value 'bogus' is not a valid Boolean",
                         six.text_type(ex))


class TestInteger(base.SenlinTestCase):

    def test_basic(self):
        sot = schema.Integer('desc')

        self.assertEqual('Integer', sot['type'])
        self.assertEqual('desc', sot['description'])

    def test_to_schema_type(self):
        sot = schema.Integer('desc')

        res = sot.to_schema_type(123)
        self.assertEqual(123, res)

        res = sot.to_schema_type('123')
        self.assertEqual(123, res)

        res = sot.to_schema_type(False)
        self.assertEqual(0, res)

        self.assertIsNone(sot.to_schema_type(None))

        ex = self.assertRaises(exc.ESchema, sot.to_schema_type, '456L')
        self.assertEqual("The value '456L' is not a valid Integer",
                         six.text_type(ex))

    def test_resolve(self):
        sot = schema.Integer()

        res = sot.resolve(1)
        self.assertEqual(1, res)

        res = sot.resolve(True)
        self.assertEqual(1, res)

        res = sot.resolve(False)
        self.assertEqual(0, res)

        self.assertIsNone(sot.resolve(None))

        ex = self.assertRaises(exc.ESchema, sot.resolve, '456L')
        self.assertEqual("The value '456L' is not a valid Integer",
                         six.text_type(ex))

    def test_validate(self):
        sot = schema.Integer()

        res = sot.validate(1)
        self.assertIsNone(res)

        res = sot.validate('1')
        self.assertIsNone(res)

        res = sot.validate(True)
        self.assertIsNone(res)

        mock_constraints = self.patchobject(sot, 'validate_constraints',
                                            return_value=None)

        res = sot.validate(1)
        self.assertIsNone(res)
        mock_constraints.assert_called_once_with(1, schema=sot, context=None)
        ex = self.assertRaises(exc.ESchema, sot.validate, 'bogus')
        self.assertEqual("The value 'bogus' is not a valid Integer",
                         six.text_type(ex))


class TestString(base.SenlinTestCase):

    def test_basic(self):
        sot = schema.String('desc')

        self.assertEqual('String', sot['type'])
        self.assertEqual('desc', sot['description'])

    def test_invalid_constructor(self):
        self.assertRaises(exc.ESchema,
                          schema.String,
                          schema=schema.String('String'))

    def test_to_schema_type(self):
        sot = schema.String('desc')

        res = sot.to_schema_type(123)
        self.assertEqual('123', res)

        res = sot.to_schema_type('123')
        self.assertEqual('123', res)

        res = sot.to_schema_type(False)
        self.assertEqual('False', res)

        res = sot.to_schema_type(None)
        self.assertIsNone(res)

        res = sot.to_schema_type(u'\u4e2d\u6587')
        self.assertEqual(u'\u4e2d\u6587', res)

    def test_resolve(self):
        sot = schema.String()

        res = sot.resolve(1)
        self.assertEqual('1', res)

        res = sot.resolve(True)
        self.assertEqual('True', res)

        res = sot.resolve(None)
        self.assertIsNone(res)

    def test_validate(self):
        sot = schema.String()

        res = sot.validate('1')
        self.assertIsNone(res)

        res = sot.validate(u'unicode')
        self.assertIsNone(res)

        ex = self.assertRaises(exc.ESchema, sot.validate, 1)
        self.assertEqual("The value '1' is not a valid string.",
                         six.text_type(ex))

        mock_constraints = self.patchobject(sot, 'validate_constraints',
                                            return_value=None)

        res = sot.validate("abcd")
        self.assertIsNone(res)
        mock_constraints.assert_called_once_with(
            "abcd", schema=sot, context=None)


class TestNumber(base.SenlinTestCase):

    def test_basic(self):
        sot = schema.Number('desc')

        self.assertEqual('Number', sot['type'])
        self.assertEqual('desc', sot['description'])

    def test_to_schema_type(self):
        sot = schema.Number('desc')

        res = sot.to_schema_type(123)
        self.assertEqual(123, res)

        res = sot.to_schema_type(123.34)
        self.assertEqual(123.34, res)

        res = sot.to_schema_type(False)
        self.assertEqual(False, res)

    def test_resolve(self):
        sot = schema.Number()
        mock_convert = self.patchobject(sot, 'to_schema_type')

        res = sot.resolve(1)
        self.assertEqual(mock_convert.return_value, res)
        mock_convert.assert_called_once_with(1)

    def test_validate(self):
        sot = schema.Number()

        res = sot.validate(1)
        self.assertIsNone(res)

        res = sot.validate('1')
        self.assertIsNone(res)

        ex = self.assertRaises(exc.ESchema, sot.validate, "bogus")
        self.assertEqual("The value 'bogus' is not a valid number.",
                         six.text_type(ex))

        mock_constraints = self.patchobject(sot, 'validate_constraints',
                                            return_value=None)

        res = sot.validate('1234')
        self.assertIsNone(res)
        mock_constraints.assert_called_once_with(
            1234, schema=sot, context=None)


class TestList(base.SenlinTestCase):

    def test_basic(self):
        sot = schema.List('desc')

        self.assertEqual('List', sot['type'])
        self.assertEqual('desc', sot['description'])

    def test__get_children(self):
        sot = schema.List('desc', schema=schema.String())

        res = sot._get_children(['v1', 'v2'], [0, 1])
        self.assertEqual(['v1', 'v2'], list(res))

    def test_resolve(self):
        sot = schema.List(schema=schema.String())

        res = sot.resolve(['v1', 'v2'])

        self.assertEqual(['v1', 'v2'], res)

        self.assertRaises(TypeError,
                          sot.resolve,
                          123)

    def test_validate(self):
        sot = schema.List(schema=schema.String())

        res = sot.validate(['abc', 'def'])

        self.assertIsNone(res)

    def test_validate_failed(self):
        sot = schema.List(schema=schema.String())

        ex = self.assertRaises(exc.ESchema, sot.validate, None)
        self.assertEqual("'None' is not a List", six.text_type(ex))


class TestMap(base.SenlinTestCase):

    def test_basic(self):
        sot = schema.Map('desc')

        self.assertEqual('Map', sot['type'])
        self.assertEqual('desc', sot['description'])

    def test__get_children(self):
        sot = schema.Map('desc', schema={'foo': schema.String()})

        res = sot._get_children({'foo': 'bar'})

        self.assertEqual({'foo': 'bar'}, dict(res))

    def test_get_default(self):
        sot = schema.Map(schema={'foo': schema.String()})
        self.assertEqual({}, sot.get_default())

        sot = schema.Map(default={'foo': 'bar'},
                         schema={'foo': schema.String()})
        self.assertEqual({'foo': 'bar'}, sot.get_default())

        sot = schema.Map(default='bad', schema={'foo': schema.String()})
        ex = self.assertRaises(exc.ESchema, sot.get_default)
        self.assertEqual("'bad' is not a Map", six.text_type(ex))

    def test_resolve(self):
        sot = schema.Map(schema={'foo': schema.String()})

        res = sot.resolve({"foo": "bar"})
        self.assertEqual({'foo': 'bar'}, res)

        res = sot.resolve('{"foo": "bar"}')
        self.assertEqual({'foo': 'bar'}, res)

        ex = self.assertRaises(exc.ESchema, sot.resolve, 'plainstring')
        self.assertEqual("'plainstring' is not a Map", six.text_type(ex))

    def test_validate(self):
        sot = schema.Map(schema={'foo': schema.String()})

        res = sot.validate({"foo": "bar"})

        self.assertIsNone(res)

    def test_validate_failed(self):
        sot = schema.Map(schema={'foo': schema.String()})

        ex = self.assertRaises(exc.ESchema, sot.validate, None)
        self.assertEqual("'None' is not a Map", six.text_type(ex))

        ex = self.assertRaises(exc.ESchema, sot.validate, 'bogus')
        self.assertEqual("'bogus' is not a Map", six.text_type(ex))


class TestStringParam(base.SenlinTestCase):

    def test_basic(self):
        sot = schema.StringParam()
        self.assertEqual('String', sot['type'])
        self.assertEqual(False, sot['required'])

    def test_validate(self):
        sot = schema.StringParam()
        result = sot.validate('foo')
        self.assertIsNone(result)

    def test_validate_bad_type(self):
        sot = schema.StringParam()
        self.assertRaises(TypeError,
                          sot.validate,
                          ['123'])

    def test_validate_failed_constraint(self):
        sot = schema.StringParam(
            constraints=[constraints.AllowedValues(('abc', 'def'))])

        ex = self.assertRaises(exc.ESchema, sot.validate, '123')

        self.assertEqual("'123' must be one of the allowed values: abc, def",
                         six.text_type(ex))


class TestIntegerParam(base.SenlinTestCase):

    def test_basic(self):
        sot = schema.IntegerParam()
        self.assertEqual('Integer', sot['type'])
        self.assertEqual(False, sot['required'])

    def test_validate(self):
        sot = schema.IntegerParam()
        result = sot.validate(123)
        self.assertIsNone(result)

    def test_validate_bad_type(self):
        sot = schema.IntegerParam()
        self.assertRaises(ValueError,
                          sot.validate,
                          'not int')

    def test_validate_failed_constraint(self):
        sot = schema.IntegerParam(
            constraints=[constraints.AllowedValues((123, 124))])

        ex = self.assertRaises(exc.ESchema, sot.validate, 12)

        self.assertEqual("'12' must be one of the allowed values: 123, 124",
                         six.text_type(ex))


class TestOperation(base.SenlinTestCase):

    def test_basic(self):
        sot = schema.Operation()
        self.assertEqual('Undocumented', sot['description'])
        self.assertEqual({}, sot['parameters'])

    def test_initialized(self):
        sot = schema.Operation('des', schema={'foo': schema.StringParam()})
        self.assertEqual('des', sot['description'])
        self.assertEqual({'foo': {'required': False, 'type': 'String'}},
                         sot['parameters'])

    def test_validate(self):
        sot = schema.Operation('des', schema={'foo': schema.StringParam()})
        res = sot.validate({'foo': 'bar'})
        self.assertIsNone(res)

    def test_validate_unrecognizable_param(self):
        sot = schema.Operation('des', schema={'foo': schema.StringParam()})

        ex = self.assertRaises(exc.ESchema, sot.validate,
                               {'baar': 'baar'})

        self.assertEqual("Unrecognizable parameter 'baar'", six.text_type(ex))

    def test_validate_failed_type(self):
        sot = schema.Operation('des', schema={'foo': schema.StringParam()})

        ex = self.assertRaises(exc.ESchema, sot.validate,
                               {'foo': ['baaar']})

        self.assertEqual("value is not a string",
                         six.text_type(ex))

    def test_validate_failed_constraint(self):
        sot = schema.Operation(
            'des',
            schema={
                'foo': schema.StringParam(
                    constraints=[constraints.AllowedValues(['bar'])])
            }
        )

        ex = self.assertRaises(exc.ESchema, sot.validate,
                               {'foo': 'baaar'})

        self.assertEqual("'baaar' must be one of the allowed values: bar",
                         six.text_type(ex))

    def test_validate_failed_required(self):
        sot = schema.Operation(
            'des',
            schema={
                'foo': schema.StringParam(),
                'bar': schema.StringParam(required=True)
            }
        )

        ex = self.assertRaises(exc.ESchema, sot.validate,
                               {'foo': 'baaar'})

        self.assertEqual("Required parameter 'bar' not provided",
                         six.text_type(ex))

    def test_validate_failed_version(self):
        sot = schema.Operation(
            'des',
            schema={
                'foo': schema.StringParam(min_version='2.0'),
            }
        )

        ex = self.assertRaises(exc.ESchema, sot.validate,
                               {'foo': 'baaar'}, '1.0')

        self.assertEqual("foo (min_version=2.0) is not supported by spec "
                         "version 1.0.", six.text_type(ex))


class TestSpec(base.SenlinTestCase):
    spec_schema = {
        'key1': schema.String('first key', default='value1'),
        'key2': schema.Integer('second key', required=True),
    }

    def test_init(self):
        data = {'key1': 'value1', 'key2': 2}
        sot = schema.Spec(self.spec_schema, data)

        self.assertEqual(self.spec_schema, sot._schema)
        self.assertEqual(data, sot._data)
        self.assertIsNone(sot._version)

    def test_init_with_version(self):
        data = {'key1': 'value1', 'key2': 2}
        sot = schema.Spec(self.spec_schema, data, version='1.2')

        self.assertEqual(self.spec_schema, sot._schema)
        self.assertEqual(data, sot._data)
        self.assertEqual('1.2', sot._version)

    def test_validate(self):
        data = {'key1': 'value1', 'key2': 2}
        sot = schema.Spec(self.spec_schema, data)
        res = sot.validate()
        self.assertIsNone(res)

        data1 = {'key2': 2}
        sot = schema.Spec(self.spec_schema, data1)
        res = sot.validate()
        self.assertIsNone(res)

    def test_validate_fail_unrecognizable_key(self):
        spec_schema = {
            'key1': schema.String('first key', default='value1'),
        }
        data = {'key1': 'value1', 'key2': 2}
        sot = schema.Spec(spec_schema, data, version='1.0')
        ex = self.assertRaises(exc.ESchema, sot.validate)

        self.assertIn("Unrecognizable spec item 'key2'",
                      six.text_type(ex.message))

    def test_validate_fail_value_type_incorrect(self):
        spec_schema = {
            'key1': schema.String('first key', default='value1'),
            'key2': schema.Integer('second key', required=True),
        }

        data = {'key1': 'value1', 'key2': 'abc'}
        spec = schema.Spec(spec_schema, data, version='1.0')
        ex = self.assertRaises(exc.ESchema, spec.validate)
        self.assertIn("The value 'abc' is not a valid Integer",
                      six.text_type(ex.message))

    def test_validate_version_good(self):
        spec_schema = {
            'type': schema.String('Type name', required=True),
            'version': schema.String('Version number', required=True),
            'key1': schema.String('first key', default='value1'),
            'key2': schema.Integer('second key', required=True,
                                   min_version='1.0', max_version='1.2'),
        }

        data = {
            'key1': 'value1',
            'key2': 2,
            'type': 'test-type',
            'version': '1.0'
        }
        spec = schema.Spec(spec_schema, data)
        self.assertIsNone(spec.validate())

        data = {'key2': 2, 'type': 'test-type', 'version': '1.2'}
        spec = schema.Spec(spec_schema, data)
        self.assertIsNone(spec.validate())

    def test_validate_version_fail_unsupported_version(self):
        spec_schema = {
            'type': schema.String('Type name', required=True),
            'version': schema.String('Version number', required=True),
            'key1': schema.String('first key', default='value1',
                                  min_version='1.1'),
            'key2': schema.Integer('second key', required=True),
        }

        data = {
            'key1': 'value1',
            'key2': 2,
            'type': 'test-type',
            'version': '1.0'
        }
        spec = schema.Spec(spec_schema, data, version='1.0')
        ex = self.assertRaises(exc.ESchema, spec.validate)
        msg = 'key1 (min_version=1.1) is not supported by spec version 1.0.'
        self.assertIn(msg, six.text_type(ex.message))

    def test_validate_version_fail_version_over_max(self):
        spec_schema = {
            'type': schema.String('Type name', required=True),
            'version': schema.String('Version number', required=True),
            'key1': schema.String('first key', default='value1',
                                  max_version='2.0'),
            'key2': schema.Integer('second key', required=True),
        }

        data = {
            'key1': 'value1',
            'key2': 2,
            'type': 'test-type',
            'version': '3.0'
        }
        spec = schema.Spec(spec_schema, data, version='3.0')
        ex = self.assertRaises(exc.ESchema, spec.validate)
        msg = 'key1 (max_version=2.0) is not supported by spec version 3.0.'
        self.assertIn(msg, six.text_type(ex.message))

    def test_resolve_value(self):
        data = {'key2': 2}
        sot = schema.Spec(self.spec_schema, data, version='1.2')

        res = sot.resolve_value('key2')
        self.assertEqual(2, res)

        res = sot.resolve_value('key1')
        self.assertEqual('value1', res)

        ex = self.assertRaises(exc.ESchema, sot.resolve_value, 'key3')
        self.assertEqual("Invalid spec item: key3", six.text_type(ex))

    def test_resolve_value_required_key_missing(self):
        data = {'key1': 'value1'}
        sot = schema.Spec(self.spec_schema, data, version='1.0')

        ex = self.assertRaises(exc.ESchema, sot.resolve_value, 'key2')
        self.assertIn("Required spec item 'key2' not provided",
                      six.text_type(ex.message))

    def test___getitem__(self):
        data = {'key2': 2}
        sot = schema.Spec(self.spec_schema, data, version='1.2')

        res = sot['key1']
        self.assertEqual('value1', res)
        res = sot['key2']
        self.assertEqual(2, res)

    def test___len__(self):
        data = {'key2': 2}
        sot = schema.Spec(self.spec_schema, data, version='1.2')

        res = len(sot)
        self.assertEqual(2, res)

    def test___contains__(self):
        data = {'key2': 2}
        sot = schema.Spec(self.spec_schema, data, version='1.2')

        self.assertIn('key1', sot)
        self.assertIn('key2', sot)
        self.assertNotIn('key3', sot)

    def test__iter__(self):
        data = {'key2': 2}
        sot = schema.Spec(self.spec_schema, data, version='1.2')

        res = [k for k in iter(sot)]

        self.assertIn('key1', res)
        self.assertIn('key2', res)


class TestSpecVersionChecking(base.SenlinTestCase):

    def test_spec_version_okay(self):
        spec = {'type': 'Foo', 'version': 'version string'}
        res = schema.get_spec_version(spec)
        self.assertEqual(('Foo', 'version string'), res)

        spec = {'type': 'Foo', 'version': 1.5}
        res = schema.get_spec_version(spec)
        self.assertEqual(('Foo', '1.5'), res)

    def test_spec_version_not_dict(self):
        spec = 'a string'
        ex = self.assertRaises(exc.ESchema, schema.get_spec_version, spec)
        self.assertEqual('The provided spec is not a map.',
                         six.text_type(ex))

    def test_spec_version_no_type_key(self):
        spec = {'tpye': 'a string'}
        ex = self.assertRaises(exc.ESchema, schema.get_spec_version, spec)
        self.assertEqual("The 'type' key is missing from the provided "
                         "spec map.", six.text_type(ex))

    def test_spec_version_no_version_key(self):
        spec = {'type': 'a string', 'ver': '123'}
        ex = self.assertRaises(exc.ESchema, schema.get_spec_version, spec)
        self.assertEqual("The 'version' key is missing from the provided "
                         "spec map.", six.text_type(ex))
