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
from oslo_config import cfg
from oslo_versionedobjects import fields
import six
import testtools

from senlin.common import consts
from senlin.objects import fields as senlin_fields

CONF = cfg.CONF


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


class TestBoolean(TestField):

    def setUp(self):
        super(TestBoolean, self).setUp()

        self.field = senlin_fields.BooleanField()
        self.coerce_good_values = [
            ('True', True),
            ('T', True),
            ('t', True),
            ('1', True),
            ('yes', True),
            ('on', True),
            ('False', False),
            ('F', False),
            ('f', False),
            ('0', False),
            ('no', False),
            ('off', False)
        ]
        self.coerce_bad_values = ['BOGUS']

        self.to_primitive_values = [
            (True, True),
            (False, False)
        ]

        self.from_primitive_values = [
            ('True', 'True'),
            ('False', 'False')
        ]

    def test_stringify(self):
        self.assertEqual('True', self.field.stringify(True))
        self.assertEqual('False', self.field.stringify(False))


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

    def test_stringify_invalid(self):
        self.assertRaises(ValueError,
                          self.field.stringify, self.coerce_bad_values[0])

    def test_get_schema(self):
        self.assertEqual(
            {'type': ['object'], 'readonly': False},
            self.field.get_schema()
        )


class TestUniqueDict(TestField):

    def setUp(self):
        super(TestUniqueDict, self).setUp()

        self.field = senlin_fields.UniqueDict(fields.String())
        self.coerce_good_values = [({"k": "v"}, {"k": "v"})]
        self.coerce_bad_values = ['{"K": "v"]']
        self.to_primitive_values = [({"k": "v"}, {"k": "v"})]
        self.from_primitive_values = [({"k": "v"}, {"k": "v"})]

    def test_stringify(self):
        self.assertEqual("{k='v'}", self.field.stringify({"k": "v"}))

    def test_coerce(self):
        res = self.field.coerce(None, 'attr', {'k1': 'v1'})
        self.assertEqual({'k1': 'v1'}, res)

    def test_coerce_failed_duplicate(self):
        ex = self.assertRaises(ValueError,
                               self.field.coerce,
                               None, 'attr', {'k1': 'v1', 'k2': 'v1'})

        self.assertEqual('Map contains duplicated values',
                         six.text_type(ex))


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

    def test_stringify_invalid(self):
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

    def test_stringify_invalid(self):
        self.assertRaises(ValueError, self.field.stringify, 'begin')


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

    def test_coerce_failed(self):
        obj = mock.Mock()
        sot = senlin_fields.Name()

        ex = self.assertRaises(ValueError,
                               sot.coerce,
                               obj, 'attr', 'value/bad')
        self.assertEqual("The value for the 'attr' (value/bad) contains "
                         "illegal characters. It must contain only "
                         "alphanumeric or \"_-.~\" characters and must start "
                         "with letter.",
                         six.text_type(ex))

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


class TestCapacity(TestField):

    def setUp(self):
        super(TestCapacity, self).setUp()

        self.field = senlin_fields.CapacityField()
        self.coerce_good_values = [
            (100, 100),          # plain integer
            ('100', 100),        # string of integer
            ('0123', 123),       # leading zeros ignored
        ]
        self.coerce_bad_values = [
            -1,              # less than 0
            'strval',        # illegal value
        ]
        self.to_primitive_values = self.coerce_good_values[0:1]
        self.from_primitive_values = self.coerce_good_values[0:1]

    def test_stringify(self):
        self.assertEqual('100', self.field.stringify(100))
        self.assertEqual('100', self.field.stringify('100'))

    def test_init(self):
        CONF.set_override('max_nodes_per_cluster', 300)
        sot = senlin_fields.Capacity()

        self.assertEqual(0, sot.minimum)
        self.assertEqual(300, sot.maximum)

    def test_init_with_values(self):
        CONF.set_override('max_nodes_per_cluster', 300)
        sot = senlin_fields.Capacity(2, 200)

        self.assertEqual(2, sot.minimum)
        self.assertEqual(200, sot.maximum)

    def test_init_invalid(self):
        CONF.set_override('max_nodes_per_cluster', 100)

        ex = self.assertRaises(ValueError,
                               senlin_fields.Capacity,
                               minimum=101)
        self.assertEqual("The value of 'minimum' cannot be greater than the "
                         "global constraint (100).", six.text_type(ex))

        ex = self.assertRaises(ValueError,
                               senlin_fields.Capacity,
                               maximum=101)
        self.assertEqual("The value of 'maximum' cannot be greater than the "
                         "global constraint (100).", six.text_type(ex))

        ex = self.assertRaises(ValueError,
                               senlin_fields.Capacity,
                               minimum=60, maximum=40)
        self.assertEqual("The value of 'maximum' must be greater than or equal"
                         " to that of the 'minimum' specified.",
                         six.text_type(ex))

    def test_coerce(self):
        sot = senlin_fields.Capacity(minimum=2, maximum=200)
        obj = mock.Mock()
        res = sot.coerce(obj, 'attr', 12)
        self.assertEqual(12, res)
        res = sot.coerce(obj, 'attr', 2)
        self.assertEqual(2, res)
        res = sot.coerce(obj, 'attr', 200)
        self.assertEqual(200, res)

        sot = senlin_fields.Capacity()

        res = sot.coerce(obj, 'attr', 12)
        self.assertEqual(12, res)
        res = sot.coerce(obj, 'attr', 0)
        self.assertEqual(0, res)
        res = sot.coerce(obj, 'attr', CONF.max_nodes_per_cluster)
        self.assertEqual(CONF.max_nodes_per_cluster, res)

    def test_coerce_failed(self):
        sot = senlin_fields.Capacity(minimum=2, maximum=200)
        obj = mock.Mock()

        ex = self.assertRaises(ValueError,
                               sot.coerce,
                               obj, 'attr', 1)
        self.assertEqual("The value for the attr field must be greater than "
                         "or equal to 2.", six.text_type(ex))

        ex = self.assertRaises(ValueError,
                               sot.coerce,
                               obj, 'attr', 201)
        self.assertEqual("The value for the attr field must be less than "
                         "or equal to 200.", six.text_type(ex))

        ex = self.assertRaises(ValueError,
                               sot.coerce,
                               obj, 'attr', 'badvalue')
        self.assertEqual("The value for attr must be an integer: 'badvalue'.",
                         six.text_type(ex))

    def test_get_schema(self):
        sot = senlin_fields.Capacity(minimum=2, maximum=200)
        self.assertEqual(
            {
                'type': ['integer', 'string'],
                'minimum': 2,
                'maximum': 200,
                'pattern': '^[0-9]*$',
            },
            sot.get_schema()
        )

    def test_get_schema_default(self):
        cfg.CONF.set_override('max_nodes_per_cluster', 100)
        sot = senlin_fields.Capacity()
        self.assertEqual(
            {
                'type': ['integer', 'string'],
                'minimum': 0,
                'maximum': 100,
                'pattern': '^[0-9]*$',
            },
            sot.get_schema()
        )


class TestSort(TestField):

    def setUp(self):
        super(TestSort, self).setUp()

        self.keys = ['key1', 'key2', 'key3']
        self.field = senlin_fields.Sort(valid_keys=self.keys)
        self.coerce_good_values = [
            ('key1', 'key1'),               # single key
            ('key1,key2', 'key1,key2'),     # multi keys
            ('key1:asc', 'key1:asc'),       # key with dir
            ('key2:desc', 'key2:desc'),     # key with different dir
            ('key1,key2:asc', 'key1,key2:asc'),  # mixed case
        ]
        self.coerce_bad_values = [
            'foo',              # unknown key
            ':desc',            # unspecified key
            'key1:up',          # unsupported dir
            'key1,key2:up',     # unsupported dir
            'foo,key2',         # unknown key
            'key2,:asc',        # unspecified key
            'key2,:desc',       # unspecified key
            'key1,',            # missing key
            ',key2',            # missing key
        ]
        self.to_primitive_values = self.coerce_good_values[0:1]
        self.from_primitive_values = self.coerce_good_values[0:1]

    def test_stringify(self):
        self.assertEqual("'key1,key2'", self.field.stringify('key1,key2'))

    def test_init(self):
        keys = ['foo', 'bar']
        sot = senlin_fields.Sort(valid_keys=keys)

        self.assertEqual(keys, sot.valid_keys)

    def test_coerce_failure(self):
        obj = mock.Mock()
        ex = self.assertRaises(ValueError,
                               self.field.coerce,
                               obj, 'attr', ':asc')
        self.assertEqual("Missing sort key for 'attr'.", six.text_type(ex))

        ex = self.assertRaises(ValueError,
                               self.field.coerce,
                               obj, 'attr', 'foo:asc')
        self.assertEqual("Unsupported sort key 'foo' for 'attr'.",
                         six.text_type(ex))

        ex = self.assertRaises(ValueError,
                               self.field.coerce,
                               obj, 'attr', 'key1:down')
        self.assertEqual("Unsupported sort dir 'down' for 'attr'.",
                         six.text_type(ex))

    def test_get_schema(self):
        self.assertEqual(
            {'type': ['string']},
            self.field.get_schema()
        )


class TestIdentityList(TestField):

    def setUp(self):
        super(TestIdentityList, self).setUp()

        self.field = senlin_fields.IdentityList(fields.String())

        self.coerce_good_values = [
            (['abc'], ['abc'])
        ]
        self.coerce_bad_values = [
            123
        ]
        self.to_primitive_values = self.coerce_good_values[0:1]
        self.from_primitive_values = self.coerce_good_values[0:1]

    def test_stringify(self):
        self.assertEqual("['abc','def']",
                         self.field.stringify(['abc', 'def']))

    def test_init_with_params(self):
        sot = senlin_fields.IdentityList(fields.String(), min_items=1,
                                         unique=False)

        self.assertEqual(1, sot.min_items)
        self.assertFalse(sot.unique_items)

    def test_coerce_not_unique_okay(self):
        sot = senlin_fields.IdentityList(fields.String(), min_items=1,
                                         unique=False)
        obj = mock.Mock()

        # not unique is okay
        res = sot.coerce(obj, 'attr', ['abc', 'abc'])
        self.assertEqual(['abc', 'abc'], res)

    def test_coerce_too_short(self):
        sot = senlin_fields.IdentityList(fields.String(), min_items=2,
                                         unique=False)
        obj = mock.Mock()

        # violating min_items
        ex = self.assertRaises(ValueError,
                               sot.coerce,
                               obj, 'attr', [])

        self.assertEqual("Value for 'attr' must have at least 2 item(s).",
                         six.text_type(ex))

    def test_coerce_not_unique_bad(self):
        obj = mock.Mock()

        # violating min_items
        ex = self.assertRaises(ValueError,
                               self.field.coerce,
                               obj, 'attr', ['abc', 'abc'])

        self.assertEqual("Items for 'attr' must be unique",
                         six.text_type(ex))

    def test_get_schema(self):
        self.assertEqual(
            {
                'type': ['array'],
                'items': {
                    'readonly': False,
                    'type': ['string'],
                },
                'minItems': 0,
                'uniqueItems': True
            },
            self.field.get_schema()
        )

        sot = senlin_fields.IdentityList(fields.String(), min_items=2,
                                         unique=False, nullable=True)
        self.assertEqual(
            {
                'type': ['array', 'null'],
                'items': {
                    'readonly': False,
                    'type': ['string'],
                },
                'minItems': 2,
                'uniqueItems': False
            },
            sot.get_schema()
        )


class TestAdjustmentTypeField(TestField):

    def setUp(self):
        super(TestAdjustmentTypeField, self).setUp()

        self.field = senlin_fields.AdjustmentTypeField()
        self.coerce_good_values = [
            ('EXACT_CAPACITY', 'EXACT_CAPACITY'),
            ('CHANGE_IN_CAPACITY', 'CHANGE_IN_CAPACITY'),
            ('CHANGE_IN_PERCENTAGE', 'CHANGE_IN_PERCENTAGE')
        ]
        self.coerce_bad_values = ['BOGUS']

        self.to_primitive_values = self.coerce_good_values[0:1]
        self.from_primitive_values = self.coerce_good_values[0:1]

    def test_stringify(self):
        self.assertEqual("'EXACT_CAPACITY'",
                         self.field.stringify('EXACT_CAPACITY'))

    def test_get_schema(self):
        self.assertEqual(
            {
                'type': ['string'],
                'readonly': False,
                'enum': ['EXACT_CAPACITY', 'CHANGE_IN_CAPACITY',
                         'CHANGE_IN_PERCENTAGE']
            },
            self.field.get_schema()
        )


class TestAdjustmentType(TestField):
    def setUp(self):
        super(TestAdjustmentType, self).setUp()

        self.field = senlin_fields.AdjustmentType()
        self.coerce_good_values = [
            ('EXACT_CAPACITY', 'EXACT_CAPACITY'),
            ('CHANGE_IN_CAPACITY', 'CHANGE_IN_CAPACITY'),
            ('CHANGE_IN_PERCENTAGE', 'CHANGE_IN_PERCENTAGE')
        ]
        self.coerce_bad_values = ['BOGUS']

        self.to_primitive_values = self.coerce_good_values[0:1]
        self.from_primitive_values = self.coerce_good_values[0:1]

    def test_stringify(self):
        self.assertEqual("'EXACT_CAPACITY'",
                         self.field.stringify('EXACT_CAPACITY'))

    def test_get_schema(self):
        self.assertEqual(
            {
                'type': ['string'],
                'enum': ['EXACT_CAPACITY', 'CHANGE_IN_CAPACITY',
                         'CHANGE_IN_PERCENTAGE']
            },
            self.field.get_schema()
        )


class TestClusterActionNameField(TestField):

    def setUp(self):
        super(TestClusterActionNameField, self).setUp()
        self.field = senlin_fields.ClusterActionNameField()
        self.coerce_good_values = [
            (action, action) for action in consts.CLUSTER_ACTION_NAMES]
        self.coerce_bad_values = ['BOGUS']

        self.to_primitive_values = self.coerce_good_values[0:1]
        self.from_primitive_values = self.coerce_good_values[0:1]

    def test_stringify(self):
        self.assertEqual("'CLUSTER_RESIZE'",
                         self.field.stringify('CLUSTER_RESIZE'))

    def test_get_schema(self):
        self.assertEqual(
            {
                'type': ['string'],
                'readonly': False,
                'enum': ['CLUSTER_CREATE', 'CLUSTER_DELETE',
                         'CLUSTER_UPDATE', 'CLUSTER_ADD_NODES',
                         'CLUSTER_DEL_NODES', 'CLUSTER_RESIZE',
                         'CLUSTER_CHECK', 'CLUSTER_RECOVER',
                         'CLUSTER_REPLACE_NODES', 'CLUSTER_SCALE_OUT',
                         'CLUSTER_SCALE_IN', 'CLUSTER_ATTACH_POLICY',
                         'CLUSTER_DETACH_POLICY', 'CLUSTER_UPDATE_POLICY',
                         'CLUSTER_OPERATION']
            },
            self.field.get_schema()
        )


class TestClusterActionName(TestField):

    def setUp(self):
        super(TestClusterActionName, self).setUp()
        self.field = senlin_fields.ClusterActionName()
        self.coerce_good_values = [
            (action, action) for action in consts.CLUSTER_ACTION_NAMES]
        self.coerce_bad_values = ['BOGUS']

        self.to_primitive_values = self.coerce_good_values[0:1]
        self.from_primitive_values = self.coerce_good_values[0:1]

    def test_stringify(self):
        self.assertEqual("'CLUSTER_RESIZE'",
                         self.field.stringify('CLUSTER_RESIZE'))

    def test_get_schema(self):
        self.assertEqual(
            {
                'type': ['string'],
                'enum': ['CLUSTER_CREATE', 'CLUSTER_DELETE',
                         'CLUSTER_UPDATE', 'CLUSTER_ADD_NODES',
                         'CLUSTER_DEL_NODES', 'CLUSTER_RESIZE',
                         'CLUSTER_CHECK', 'CLUSTER_RECOVER',
                         'CLUSTER_REPLACE_NODES', 'CLUSTER_SCALE_OUT',
                         'CLUSTER_SCALE_IN', 'CLUSTER_ATTACH_POLICY',
                         'CLUSTER_DETACH_POLICY', 'CLUSTER_UPDATE_POLICY',
                         'CLUSTER_OPERATION']
            },
            self.field.get_schema()
        )


class TestReceiverTypeField(TestField):

    def setUp(self):
        super(TestReceiverTypeField, self).setUp()
        self.field = senlin_fields.ReceiverTypeField()
        self.coerce_good_values = [
            (action, action) for action in consts.RECEIVER_TYPES]
        self.coerce_bad_values = ['BOGUS']

        self.to_primitive_values = self.coerce_good_values[0:1]
        self.from_primitive_values = self.coerce_good_values[0:1]

    def test_stringify(self):
        self.assertEqual("'message'",
                         self.field.stringify('message'))

    def test_get_schema(self):
        self.assertEqual(
            {
                'type': ['string'],
                'readonly': False,
                'enum': ['webhook', 'message']
            },
            self.field.get_schema()
        )


class TestReceiverType(TestField):

    def setUp(self):
        super(TestReceiverType, self).setUp()
        self.field = senlin_fields.ReceiverType()
        self.coerce_good_values = [
            (action, action) for action in consts.RECEIVER_TYPES]
        self.coerce_bad_values = ['BOGUS']

        self.to_primitive_values = self.coerce_good_values[0:1]
        self.from_primitive_values = self.coerce_good_values[0:1]

    def test_stringify(self):
        self.assertEqual("'message'",
                         self.field.stringify('message'))

    def test_get_schema(self):
        self.assertEqual(
            {
                'type': ['string'],
                'enum': ['webhook', 'message']
            },
            self.field.get_schema()
        )
