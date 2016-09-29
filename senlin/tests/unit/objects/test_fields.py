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

from oslo_versionedobjects import fields
import testtools

from senlin.objects import base
from senlin.objects import fields as senlin_fields


class FakeFieldType(fields.FieldType):
    def coerce(self, obj, attr, value):
        return '*%s*' % value

    def to_primitive(self, obj, attr, value):
        return '!%s!' % value

    def from_primitive(self, obj, attr, value):
        return value[1:-1]


class TestField(testtools.TestCase):

    def setUp(self):
        super(TestField, self).setUp()
        self.field = fields.Field(FakeFieldType())
        self.coerce_good_values = [('foo', '*foo*')]
        self.coerce_bad_values = []
        self.to_primitive_values = [('foo', '!foo!')]
        self.from_primitive_values = [('!foo!', 'foo')]

    def test_coerce_good_values(self):
        for in_val, out_val in self.coerce_good_values:
            self.assertEqual(out_val, self.field.coerce('obj', 'attr', in_val))

    def test_coerce_bad_values(self):
        for in_val in self.coerce_bad_values:
            self.assertRaises((TypeError, ValueError),
                              self.field.coerce, 'obj', 'attr', in_val)

    def test_to_primitive(self):
        for in_val, prim_val in self.to_primitive_values:
            self.assertEqual(prim_val,
                             self.field.to_primitive('obj', 'attr', in_val))

    def test_from_primitive(self):
        class ObjectLikeThing(object):
            _context = 'context'

        for prim_val, out_val in self.from_primitive_values:
            self.assertEqual(out_val,
                             self.field.from_primitive(ObjectLikeThing, 'attr',
                                                       prim_val))

    def test_stringify(self):
        self.assertEqual('123', self.field.stringify(123))


class TestObject(TestField):

    def setUp(self):
        super(TestObject, self).setUp()

        @base.base.VersionedObjectRegistry.register
        class TestableObject(base.base.VersionedObject):
            fields = {
                'uuid': fields.StringField(),
            }

        test_inst = TestableObject()
        self._test_cls = TestableObject
        self.field = fields.Field(senlin_fields.Object('TestableObject'))
        self.coerce_good_values = [(test_inst, test_inst)]
        self.coerce_bad_values = [1, 'foo']
        self.to_primitive_values = [(test_inst, test_inst.obj_to_primitive())]
        self.from_primitive_values = [(test_inst.obj_to_primitive(),
                                       test_inst),
                                      (test_inst, test_inst)]

    def test_from_primitive(self):
        # we ignore this test case
        pass

    def test_stringify(self):
        # and this one is ignored as well
        pass

    def test_get_schema(self):
        self.assertEqual(
            {
                'properties': {
                    'versioned_object.changes': {
                        'items': {'type': 'string'}, 'type': 'array'
                    },
                    'versioned_object.data': {
                        'description': 'fields of TestableObject',
                        'properties': {
                            'uuid': {'readonly': False, 'type': ['string']}
                        },
                        'required': ['uuid'],
                        'type': 'object',
                    },
                    'versioned_object.name': {
                        'type': 'string',
                    },
                    'versioned_object.namespace': {
                        'type': 'string',
                    },
                    'versioned_object.version': {
                        'type': 'string',
                    },
                },
                'readonly': False,
                'required': [
                    'versioned_object.namespace',
                    'versioned_object.name',
                    'versioned_object.version',
                    'versioned_object.data',
                ],
                'type': 'object',
            },
            self.field.get_schema())


class TestJson(TestField):
    def setUp(self):
        super(TestJson, self).setUp()

        self.field = senlin_fields.JsonField()
        self.coerce_good_values = [('{"k": "v"}', {"k": "v"})]
        self.coerce_bad_values = ['{"K": "v"]']
        self.to_primitive_values = [({"k": "v"}, '{"k": "v"}')]
        self.from_primitive_values = [('{"k": "v"}', {"k": "v"})]

    def test_stringify(self):
        self.assertEqual("{'k': 'v'}", self.field.stringify({"k": "v"}))

    def test_stingify_invalid(self):
        self.assertRaises(ValueError,
                          self.field.stringify, self.coerce_bad_values[0])

    def test_get_schema(self):
        self.assertEqual(
            {'type': ['object'], 'readonly': False},
            self.field.get_schema()
        )


class TestNotificationPriority(TestField):
    def setUp(self):
        super(TestNotificationPriority, self).setUp()

        self.field = senlin_fields.NotificationPriorityField()
        self.coerce_good_values = [('audit', 'audit'),
                                   ('critical', 'critical'),
                                   ('debug', 'debug'),
                                   ('error', 'error'),
                                   ('sample', 'sample'),
                                   ('warn', 'warn')]
        self.coerce_bad_values = ['warning']
        self.to_primitive_values = self.coerce_good_values[0:1]
        self.from_primitive_values = self.coerce_good_values[0:1]

    def test_stringify(self):
        self.assertEqual("'warn'", self.field.stringify('warn'))

    def test_stingify_invalid(self):
        self.assertRaises(ValueError, self.field.stringify, 'warning')


class TestNotificationPhase(TestField):
    def setUp(self):
        super(TestNotificationPhase, self).setUp()

        self.field = senlin_fields.NotificationPhaseField()
        self.coerce_good_values = [('start', 'start'),
                                   ('end', 'end'),
                                   ('error', 'error')]
        self.coerce_bad_values = ['begin']

        self.to_primitive_values = self.coerce_good_values[0:1]
        self.from_primitive_values = self.coerce_good_values[0:1]

    def test_stringify(self):
        self.assertEqual("'error'", self.field.stringify('error'))

    def test_stingify_invalid(self):
        self.assertRaises(ValueError, self.field.stringify, 'begin')


class TestNotificationAction(TestField):
    def setUp(self):
        super(TestNotificationAction, self).setUp()

        self.field = senlin_fields.NotificationActionField()
        self.coerce_good_values = [('update', 'update')]
        self.coerce_bad_values = ['magic']

        self.to_primitive_values = self.coerce_good_values[0:1]
        self.from_primitive_values = self.coerce_good_values[0:1]

    def test_stringify(self):
        self.assertEqual("'update'", self.field.stringify('update'))

    def test_stingify_invalid(self):
        self.assertRaises(ValueError, self.field.stringify, 'magic')


class TestName(TestField):

    def setUp(self):
        super(TestName, self).setUp()

        self.field = senlin_fields.NameField()
        self.coerce_good_values = [
            ('name1', 'name1'),          # plain string
            ('name2.sec', 'name2.sec'),  # '.' okay
            ('123-sec', '123-sec'),      # '-' okay
            ('123_sec', '123_sec'),      # '_' okay
            ('123~sec', '123~sec'),      # '~' okay
            ('557', '557'),              # pure numeric okay
        ]
        self.coerce_bad_values = [
            '',              # too short
            's' * 300,       # too long
            'ab/',           # '/' illegal
            's123$',         # '$' illegal
            '13^gadf',       # '^' illegal
            'sad&cheer',     # '&' illegal
            'boo**',         # '*' illegal
            'kwsqu()',       # '(' and ')' illegal
            'bing+bang',     # '+' illegal
            'var=value',     # '=' illegal
            'quicksort[1]',  # '[' and ']' illegal
            'sdi{"gh"}',     # '{' and '}' illegal
            'gate open',     # ' ' illegal
            '12.64%',        # '%' illegal
            'name#sign',     # '#' illegal
            'back\slash',    # '\' illegal
            ' leading',      # leading blank illegal
            'trailing ',     # trailing blank illegal
            '!okay',         # '!' illegal
            '@author',       # '@' illegal
            '`info`',        # '`' illegal
            '"partial',      # '"' illegal
            "'single",       # ''' illegal
            '<max',          # '<' illegal
            '>min',          # '>' illegal
            'question?',     # '?' illegal
            'first,second',  # ',' illegal
        ]
        self.to_primitive_values = self.coerce_good_values[0:1]
        self.from_primitive_values = self.coerce_good_values[0:1]

    def test_stringify(self):
        self.assertEqual("'name1'", self.field.stringify('name1'))

    def test_init(self):
        sot = senlin_fields.Name(2, 200)

        self.assertEqual(2, sot.min_len)
        self.assertEqual(200, sot.max_len)

    def test_get_schema(self):
        sot = senlin_fields.Name(2, 200)
        self.assertEqual(
            {
                'type': ['string'],
                'minLength': 2,
                'maxLength': 200
            },
            sot.get_schema()
        )

    def test_get_schema_default(self):
        sot = senlin_fields.Name()
        self.assertEqual(
            {
                'type': ['string'],
                'minLength': 1,
                'maxLength': 255
            },
            sot.get_schema()
        )
