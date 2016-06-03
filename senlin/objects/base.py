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

from oslo_utils import versionutils
from oslo_versionedobjects import base

from senlin import objects

VersionedObjectDictCompat = base.VersionedObjectDictCompat


class SenlinObject(base.VersionedObject):
    """Base class for senlin objects.

    This is the base class for all objects that can be remoted or instantiated
    via RPC. Simply defining a sub-class of this class would make it remotely
    instantiatable. Objects should implement the "get" class method and the
    "save" object method.
    """

    OBJ_PROJECT_NAMESPACE = 'senlin'
    VERSION = '1.0'

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


class SenlinObjectRegistry(base.VersionedObjectRegistry):

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
