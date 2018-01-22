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
from oslo_versionedobjects import base as ovo_base
from oslo_versionedobjects import exception as exc
import six

from senlin.objects import base as obj_base
from senlin.objects import fields as obj_fields
from senlin.tests.unit.common import base


class FakeObject(obj_base.SenlinObject):

    VERSION_MAP = {
        '1.3': '1.2'
    }


class TestBaseObject(base.SenlinTestCase):

    def test_base_class(self):
        obj = obj_base.SenlinObject()
        self.assertEqual(obj_base.SenlinObject.OBJ_PROJECT_NAMESPACE,
                         obj.OBJ_PROJECT_NAMESPACE)
        self.assertEqual(obj_base.SenlinObject.VERSION,
                         obj.VERSION)

    @mock.patch.object(obj_base.SenlinObject, "obj_reset_changes")
    def test_from_db_object(self, mock_obj_reset_ch):
        class TestSenlinObject(obj_base.SenlinObject,
                               obj_base.VersionedObjectDictCompat):
            fields = {
                "key1": obj_fields.StringField(),
                "key2": obj_fields.StringField(),
                "metadata": obj_fields.JsonField()
            }

        obj = TestSenlinObject()
        context = mock.Mock()
        db_obj = {
            "key1": "value1",
            "key2": "value2",
            "meta_data": {"key3": "value3"}
        }
        res = obj_base.SenlinObject._from_db_object(context, obj, db_obj)
        self.assertIsNotNone(res)
        self.assertEqual("value1", obj["key1"])
        self.assertEqual("value2", obj["key2"])
        self.assertEqual({"key3": "value3"}, obj["metadata"])
        self.assertEqual(obj._context, context)
        mock_obj_reset_ch.assert_called_once_with()

    def test_from_db_object_none(self):
        obj = obj_base.SenlinObject()
        db_obj = None
        context = mock.Mock()

        res = obj_base.SenlinObject._from_db_object(context, obj, db_obj)
        self.assertIsNone(res)

    def test_to_json_schema(self):
        obj = obj_base.SenlinObject()
        self.assertRaises(exc.UnsupportedObjectError, obj.to_json_schema)

    @mock.patch.object(ovo_base.VersionedObject, 'obj_class_from_name')
    def test_obj_class_from_name_with_version(self, mock_convert):
        res = obj_base.SenlinObject.obj_class_from_name('Foo', '1.23')

        self.assertEqual(mock_convert.return_value, res)
        mock_convert.assert_called_once_with('Foo', '1.23')

    @mock.patch.object(ovo_base.VersionedObject, 'obj_class_from_name')
    def test_obj_class_from_name_no_version(self, mock_convert):
        res = obj_base.SenlinObject.obj_class_from_name('Foo')

        self.assertEqual(mock_convert.return_value, res)
        mock_convert.assert_called_once_with(
            'Foo', obj_base.SenlinObject.VERSION)

    def test_find_version_default(self):
        ctx = mock.Mock(api_version='1.1')

        res = FakeObject.find_version(ctx)

        self.assertEqual('1.0', res)

    def test_find_version_match(self):
        ctx = mock.Mock(api_version='1.3')

        res = FakeObject.find_version(ctx)

        self.assertEqual('1.2', res)

    def test_find_version_above(self):
        ctx = mock.Mock(api_version='1.4')

        res = FakeObject.find_version(ctx)

        self.assertEqual('1.2', res)

    def test_normalize_req(self):
        req = {'primary': {'bar': 'zoo'}}
        name = 'reqname'
        key = 'primary'
        expected = {
            'senlin_object.namespace': 'senlin',
            'senlin_object.version': obj_base.SenlinObject.VERSION,
            'senlin_object.name': name,
            'senlin_object.data': {
                'primary': {
                    'senlin_object.namespace': 'senlin',
                    'senlin_object.version': obj_base.SenlinObject.VERSION,
                    'senlin_object.name': 'reqnameBody',
                    'senlin_object.data': {
                        'bar': 'zoo'
                    }
                }
            }
        }

        res = obj_base.SenlinObject.normalize_req(name, req, key)

        self.assertEqual(expected, res)

    def test_normalize_req_no_key(self):
        req = {'bar': 'zoo'}
        name = 'reqname'
        expected = {
            'senlin_object.namespace': 'senlin',
            'senlin_object.version': obj_base.SenlinObject.VERSION,
            'senlin_object.name': name,
            'senlin_object.data': {
                'bar': 'zoo'
            }
        }

        res = obj_base.SenlinObject.normalize_req(name, req)

        self.assertEqual(expected, res)

    def test_normalize_req_missing_key(self):
        req = {'bar': 'zoo'}
        name = 'reqname'

        ex = self.assertRaises(ValueError,
                               obj_base.SenlinObject.normalize_req,
                               name, req, 'foo')

        self.assertEqual("Request body missing 'foo' key.", six.text_type(ex))
