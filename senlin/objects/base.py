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

"""Senlin common internal object model"""
import re

from oslo_utils import versionutils
from oslo_versionedobjects import base
from oslo_versionedobjects import fields as base_fields

from senlin.common.i18n import _
from senlin import objects

VersionedObjectDictCompat = base.VersionedObjectDictCompat
VersionedObjectSerializer = base.VersionedObjectSerializer


class SenlinObject(base.VersionedObject):
    """Base class for senlin objects.

    This is the base class for all objects that can be remoted or instantiated
    via RPC. Simply defining a sub-class of this class would make it remotely
    instantiatable. Objects should implement the "get" class method and the
    "save" object method.
    """
    OBJ_SERIAL_NAMESPACE = 'senlin_object'
    OBJ_PROJECT_NAMESPACE = 'senlin'
    BASE_VERSION = '1.0'
    VERSION = '1.0'

    # list of version maps from api request version to object version
    # higher api versions after lower api versions. e.g.
    # {'1.2': '1.0', '1.4': '1.1'}
    VERSION_MAP = {}

    @staticmethod
    def _from_db_object(context, obj, db_obj):
        if db_obj is None:
            return None
        for field in obj.fields:
            if field == 'metadata':
                obj['metadata'] = db_obj['meta_data']
            else:
                obj[field] = db_obj[field]

        obj._context = context
        obj.obj_reset_changes()

        return obj

    @staticmethod
    def _transpose_metadata(values):
        """Utility function to translate metadata field."""
        if 'metadata' in values:
            value = values.pop('metadata')
            values['meta_data'] = value
        return values

    @classmethod
    def to_json_schema(cls):
        obj_name = cls.obj_name()
        schema = {
            '$schema': 'http://json-schema.org/draft-04/schema#',
            'title': obj_name,
        }

        schema.update(base_fields.Object(obj_name).get_schema())
        dataf = cls.OBJ_SERIAL_NAMESPACE + ".data"
        schema["properties"][dataf]["additionalProperties"] = False
        return schema

    @classmethod
    def obj_class_from_name(cls, objname, objver=None):
        if objver is None:
            objver = cls.VERSION
        return super(SenlinObject, cls).obj_class_from_name(objname, objver)

    @classmethod
    def find_version(cls, context):
        match = re.match(r"^([1-9]\d*)\.([1-9]\d*|0)$", context.api_version)
        req_major = int(match.group(1))
        req_minor = int(match.group(2))
        # base version is '1.0'
        matched_version = cls.BASE_VERSION
        for api_ver, obj_ver in cls.VERSION_MAP.items():
            match = re.match(r"^([1-9]\d*)\.([1-9]\d*|0)$", api_ver)
            api_major = int(match.group(1))
            api_minor = int(match.group(2))
            if (api_major, api_minor) <= (req_major, req_minor):
                matched_version = obj_ver
            else:
                break

        return matched_version

    @classmethod
    def normalize_req(cls, name, req, key=None):
        result = {
            cls.OBJ_SERIAL_NAMESPACE + '.version': cls.VERSION,
            cls.OBJ_SERIAL_NAMESPACE + '.namespace': cls.OBJ_PROJECT_NAMESPACE,
            cls.OBJ_SERIAL_NAMESPACE + '.name': name,
        }
        if key is not None:
            if key not in req:
                raise ValueError(_("Request body missing '%s' key.") % key)

            result[cls.OBJ_SERIAL_NAMESPACE + '.data'] = {
                key: {
                    cls.OBJ_SERIAL_NAMESPACE + '.version': cls.VERSION,
                    cls.OBJ_SERIAL_NAMESPACE + '.namespace':
                        cls.OBJ_PROJECT_NAMESPACE,
                    cls.OBJ_SERIAL_NAMESPACE + '.name': name + 'Body',
                    cls.OBJ_SERIAL_NAMESPACE + '.data': req[key]
                }
            }
        else:
            result[cls.OBJ_SERIAL_NAMESPACE + '.data'] = req

        return result


class SenlinObjectRegistry(base.VersionedObjectRegistry):

    notification_classes = []

    def registration_hook(self, cls, index):
        """Callback for object registration.

        When an object is registered, this function will be called for
        maintaining senlin.objects.$OBJECT as the highest-versioned
        implementation of a given object.
        """
        version = versionutils.convert_version_to_tuple(cls.VERSION)
        if not hasattr(objects, cls.obj_name()):
            setattr(objects, cls.obj_name(), cls)
        else:
            curr_version = versionutils.convert_version_to_tuple(
                getattr(objects, cls.obj_name()).VERSION)
            if version >= curr_version:
                setattr(objects, cls.obj_name(), cls)

    @classmethod
    def register_notification(cls, notification_cls):
        """Register a class as concrete notification.

        This is used only to register concrete notification or payload
        classes. Do NOT register base classes intended for inheritance only.
        """
        cls.register_if(False)(notification_cls)
        cls.notification_classes.append(notification_cls)
        return notification_cls
