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


import six
import testtools

from senlin.common import constraints
from senlin.common import exception
from senlin.common.i18n import _
from senlin.common import schema


class TestConstraintsSchema(testtools.TestCase):
    def test_allowed_values(self):
        d = {
            'constraint': ['foo', 'bar'],
            'type': 'AllowedValues'
        }
        r = constraints.AllowedValues(['foo', 'bar'])

        self.assertEqual(d, dict(r))

    def test_allowed_values_numeric_int(self):
        '''Test AllowedValues constraint for numeric integer values.

        Test if the AllowedValues constraint works for numeric values in any
        combination of numeric strings or numbers in the constraint and
        numeric strings or numbers as value.
        '''

        # Allowed values defined as integer numbers
        s = schema.Integer(
            constraints=[constraints.AllowedValues([1, 2, 4])]
        )
        # ... and value as number or string
        self.assertIsNone(s.validate(1))

        err = self.assertRaises(exception.SpecValidationFailed,
                                s.validate, 3)
        self.assertEqual('"3" must be one of the allowed values: 1, 2, 4',
                         six.text_type(err))

        self.assertIsNone(s.validate('1'))
        err = self.assertRaises(exception.SpecValidationFailed,
                                s.validate, '3')
        self.assertEqual('"3" must be one of the allowed values: 1, 2, 4',
                         six.text_type(err))

        # Allowed values defined as integer strings
        s = schema.Integer(
            constraints=[constraints.AllowedValues(['1', '2', '4'])]
        )
        # ... and value as number or string
        self.assertIsNone(s.validate(1))
        err = self.assertRaises(exception.SpecValidationFailed,
                                s.validate, 3)
        self.assertEqual('"3" must be one of the allowed values: 1, 2, 4',
                         six.text_type(err))

        self.assertIsNone(s.validate('1'))
        err = self.assertRaises(exception.SpecValidationFailed,
                                s.validate, '3')
        self.assertEqual('"3" must be one of the allowed values: 1, 2, 4',
                         six.text_type(err))

    def test_allowed_values_numeric_float(self):
        '''Test AllowedValues constraint for numeric floating point values.

        Test if the AllowedValues constraint works for numeric values in any
        combination of numeric strings or numbers in the constraint and
        numeric strings or numbers as value.
        '''

        # Allowed values defined as numbers
        s = schema.Number(
            constraints=[constraints.AllowedValues([1.1, 2.2, 4.4])]
        )
        # ... and value as number or string
        self.assertIsNone(s.validate_constraints(1.1))
        err = self.assertRaises(exception.SpecValidationFailed,
                                s.validate_constraints, 3.3)
        self.assertEqual('"3.3" must be one of the allowed values: '
                         '1.1, 2.2, 4.4', six.text_type(err))
        self.assertIsNone(s.validate_constraints('1.1', s))
        err = self.assertRaises(exception.SpecValidationFailed,
                                s.validate_constraints, '3.3')
        self.assertEqual('"3.3" must be one of the allowed values: '
                         '1.1, 2.2, 4.4', six.text_type(err))

        # Allowed values defined as strings
        s = schema.Number(
            constraints=[constraints.AllowedValues(['1.1', '2.2', '4.4'])]
        )
        # ... and value as number or string
        self.assertIsNone(s.validate_constraints(1.1, s))
        err = self.assertRaises(exception.SpecValidationFailed,
                                s.validate_constraints, 3.3, s)
        self.assertEqual('"3.3" must be one of the allowed values: '
                         '1.1, 2.2, 4.4', six.text_type(err))
        self.assertIsNone(s.validate_constraints('1.1', s))
        err = self.assertRaises(exception.SpecValidationFailed,
                                s.validate_constraints, '3.3', s)
        self.assertEqual('"3.3" must be one of the allowed values: '
                         '1.1, 2.2, 4.4', six.text_type(err))

    def test_schema_all(self):
        d = {
            'type': 'String',
            'description': 'A string',
            'default': 'wibble',
            'required': True,
            'updatable': False,
            'constraints': [{
                'constraint': ['foo', 'bar'],
                'type': 'AllowedValues'
            }]
        }
        c = constraints.AllowedValues(['foo', 'bar'])
        s = schema.String('A string', default='wibble', required=True,
                          constraints=[c])
        self.assertEqual(d, dict(s))

    def test_schema_list_schema(self):
        d = {
            'type': 'List',
            'description': 'A list',
            'schema': {
                '*': {
                    'type': 'String',
                    'description': 'A string',
                    'default': 'wibble',
                    'required': True,
                    'updatable': False,
                    'constraints': [{
                        'constraint': ['foo', 'bar'],
                        'type': 'AllowedValues'
                    }]
                }
            },
            'required': False,
            'updatable': False,
        }
        c = constraints.AllowedValues(['foo', 'bar'])
        s = schema.String('A string', default='wibble', required=True,
                          constraints=[c])
        l = schema.List('A list', schema=s)
        self.assertEqual(d, dict(l))

    def test_schema_map_schema(self):
        d = {
            'type': 'Map',
            'description': 'A map',
            'schema': {
                'Foo': {
                    'type': 'String',
                    'description': 'A string',
                    'default': 'wibble',
                    'required': True,
                    'updatable': False,
                    'constraints': [{
                        'type': 'AllowedValues',
                        'constraint': ['foo', 'bar']
                    }]
                }
            },
            'required': False,
            'updatable': False,
        }
        c = constraints.AllowedValues(['foo', 'bar'])
        s = schema.String('A string', default='wibble', required=True,
                          constraints=[c])
        m = schema.Map('A map', schema={'Foo': s})
        self.assertEqual(d, dict(m))

    def test_schema_map_resolve_json(self):
        m = schema.Map('A map')
        self.assertEqual({'foo': 'bar'}, m.resolve('{"foo": "bar"}'))

    def test_schema_map_resolve_invalid(self):
        m = schema.Map('A map')
        ex = self.assertRaises(TypeError, m.resolve, 'oops')
        self.assertEqual('"oops" is not a Map', six.text_type(ex))

    def test_schema_nested_schema(self):
        d = {
            'type': 'List',
            'description': 'A list',
            'schema': {
                '*': {
                    'type': 'Map',
                    'description': 'A map',
                    'schema': {
                        'Foo': {
                            'type': 'String',
                            'description': 'A string',
                            'default': 'wibble',
                            'required': True,
                            'updatable': False,
                            'constraints': [{
                                'type': 'AllowedValues',
                                'constraint': ['foo', 'bar']
                            }]
                        }
                    },
                    'required': False,
                    'updatable': False,
                }
            },
            'required': False,
            'updatable': False,
        }
        c = constraints.AllowedValues(['foo', 'bar'])
        s = schema.String('A string', default='wibble', required=True,
                          constraints=[c])
        m = schema.Map('A map', schema={'Foo': s})
        l = schema.List('A list', schema=m)
        self.assertEqual(d, dict(l))

    def test_schema_invalid_type(self):
        self.assertRaises(exception.InvalidSchemaError,
                          schema.String,
                          schema=schema.String('String'))

    def test_schema_validate_good(self):
        c = constraints.AllowedValues(['foo', 'bar'])
        s = schema.String('A string', default='wibble', required=True,
                          constraints=[c])
        self.assertIsNone(s.validate('foo'))

    def test_schema_validate_fail(self):
        c = constraints.AllowedValues(['foo', 'bar'])
        s = schema.String('A string', default='wibble', required=True,
                          constraints=[c])
        err = self.assertRaises(exception.SpecValidationFailed,
                                s.validate,
                                'zoo')
        self.assertIn('"zoo" must be one of the allowed values: foo, bar',
                      six.text_type(err))

    def test_schema_nested_validate_good(self):
        c = constraints.AllowedValues(['foo', 'bar'])
        nested = schema.String('A string', default='wibble', required=True,
                               constraints=[c])
        s = schema.Map('A map', schema={'Foo': nested})
        self.assertIsNone(s.validate({'Foo': 'foo'}))

    def test_schema_nested_validate_fail(self):
        c = constraints.AllowedValues(['foo', 'bar'])
        nested = schema.String('A string', default='wibble', required=True,
                               constraints=[c])
        s = schema.Map('A map', schema={'Foo': nested})
        err = self.assertRaises(exception.SpecValidationFailed, s.validate,
                                {'Foo': 'zoo'})

        self.assertIn('"zoo" must be one of the allowed values: foo, bar',
                      six.text_type(err))

    def test_spec_validate_good(self):
        spec_schema = {
            'key1': schema.String('first key', default='value1'),
            'key2': schema.Integer('second key', required=True),
        }

        data = {'key1': 'value1', 'key2': 2}
        spec = schema.Spec(spec_schema, data)
        self.assertIsNone(spec.validate())

        data = {'key2': 2}
        spec = schema.Spec(spec_schema, data)
        self.assertIsNone(spec.validate())

    def test_spec_validate_fail_value_type_incorrect(self):
        spec_schema = {
            'key1': schema.String('first key', default='value1'),
            'key2': schema.Integer('second key', required=True),
        }

        data = {'key1': 'value1', 'key2': 'abc'}
        spec = schema.Spec(spec_schema, data)
        ex = self.assertRaises(exception.SpecValidationFailed,
                               spec.validate)
        msg = _('The value "%s" cannot be converted into an '
                'integer.') % data['key2']
        self.assertNotEqual(-1, six.text_type(ex.message).find(msg))

    def test_policy_validate_fail_unrecognizable_key(self):
        spec_schema = {
            'key1': schema.String('first key', default='value1'),
        }

        data = {'key1': 'value1', 'key2': 2}
        spec = schema.Spec(spec_schema, data)
        ex = self.assertRaises(exception.SpecValidationFailed,
                               spec.validate)
        msg = _('Unrecognizable spec item "%s"') % 'key2'
        self.assertNotEqual(-1, six.text_type(ex.message).find(msg))

    def test_policy_validate_fail_required_key_missing(self):
        spec_schema = {
            'key1': schema.String('first key', default='value1'),
            'key2': schema.Integer('second key', required=True),
        }

        data = {'key1': 'value1'}
        spec = schema.Spec(spec_schema, data)
        ex = self.assertRaises(exception.SpecValidationFailed,
                               spec.validate)
        msg = _('Required spec item "%s" not assigned') % 'key2'
        self.assertNotEqual(-1, six.text_type(ex.message).find(msg))


class TestSpecVersionChecking(testtools.TestCase):

    def test_spec_version_okay(self):
        spec = {'type': 'Foo', 'version': 'version string'}
        res = schema.get_spec_version(spec)
        self.assertEqual(('Foo', 'version string'), res)

        spec = {'type': 'Foo', 'version': 1.5}
        res = schema.get_spec_version(spec)
        self.assertEqual(('Foo', '1.5'), res)

    def test_spec_version_not_dict(self):
        spec = 'a string'
        ex = self.assertRaises(exception.SpecValidationFailed,
                               schema.get_spec_version, spec)
        self.assertEqual('The provided spec is not a map.',
                         six.text_type(ex))

    def test_spec_version_no_type_key(self):
        spec = {'tpye': 'a string'}
        ex = self.assertRaises(exception.SpecValidationFailed,
                               schema.get_spec_version, spec)
        self.assertEqual("The 'type' key is missing from the provided "
                         "spec map.", six.text_type(ex))

    def test_spec_version_no_version_key(self):
        spec = {'type': 'a string', 'ver': '123'}
        ex = self.assertRaises(exception.SpecValidationFailed,
                               schema.get_spec_version, spec)
        self.assertEqual("The 'version' key is missing from the provided "
                         "spec map.", six.text_type(ex))
