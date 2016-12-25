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
from senlin.common import exception as exc
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

        err = self.assertRaises(exc.ESchema, s.validate, 3)
        self.assertEqual("'3' must be one of the allowed values: 1, 2, 4",
                         six.text_type(err))

        self.assertIsNone(s.validate('1'))
        err = self.assertRaises(exc.ESchema, s.validate, '3')
        self.assertEqual("'3' must be one of the allowed values: 1, 2, 4",
                         six.text_type(err))

        # Allowed values defined as integer strings
        s = schema.Integer(
            constraints=[constraints.AllowedValues(['1', '2', '4'])]
        )
        # ... and value as number or string
        self.assertIsNone(s.validate(1))
        err = self.assertRaises(exc.ESchema, s.validate, 3)
        self.assertEqual("'3' must be one of the allowed values: 1, 2, 4",
                         six.text_type(err))

        self.assertIsNone(s.validate('1'))
        err = self.assertRaises(exc.ESchema, s.validate, '3')
        self.assertEqual("'3' must be one of the allowed values: 1, 2, 4",
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
        err = self.assertRaises(exc.ESchema, s.validate_constraints, 3.3)
        self.assertEqual("'3.3' must be one of the allowed values: "
                         "1.1, 2.2, 4.4", six.text_type(err))
        self.assertIsNone(s.validate_constraints('1.1', s))
        err = self.assertRaises(exc.ESchema, s.validate_constraints, '3.3')
        self.assertEqual("'3.3' must be one of the allowed values: "
                         "1.1, 2.2, 4.4", six.text_type(err))

        # Allowed values defined as strings
        s = schema.Number(
            constraints=[constraints.AllowedValues(['1.1', '2.2', '4.4'])]
        )
        # ... and value as number or string
        self.assertIsNone(s.validate_constraints(1.1, s))
        err = self.assertRaises(exc.ESchema, s.validate_constraints, 3.3, s)
        self.assertEqual("'3.3' must be one of the allowed values: "
                         "1.1, 2.2, 4.4", six.text_type(err))
        self.assertIsNone(s.validate_constraints('1.1', s))
        err = self.assertRaises(exc.ESchema, s.validate_constraints, '3.3', s)
        self.assertEqual("'3.3' must be one of the allowed values: "
                         "1.1, 2.2, 4.4", six.text_type(err))

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

    def test_schema_validate_good(self):
        c = constraints.AllowedValues(['foo', 'bar'])
        s = schema.String('A string', default='wibble', required=True,
                          constraints=[c])
        self.assertIsNone(s.validate('foo'))

    def test_schema_validate_fail(self):
        c = constraints.AllowedValues(['foo', 'bar'])
        s = schema.String('A string', default='wibble', required=True,
                          constraints=[c])
        err = self.assertRaises(exc.ESchema, s.validate, 'zoo')
        self.assertIn("'zoo' must be one of the allowed values: foo, bar",
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
        err = self.assertRaises(exc.ESchema, s.validate, {'Foo': 'zoo'})

        self.assertIn("'zoo' must be one of the allowed values: foo, bar",
                      six.text_type(err))
