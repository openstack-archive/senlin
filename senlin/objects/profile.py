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

"""Profile object."""
from oslo_utils import uuidutils

from senlin.common import exception
from senlin.common import utils
from senlin.db import api as db_api
from senlin.objects import base
from senlin.objects import fields


@base.SenlinObjectRegistry.register
class Profile(base.SenlinObject, base.VersionedObjectDictCompat):
    """Senlin profile object."""

    fields = {
        'id': fields.UUIDField(),
        'name': fields.StringField(),
        'type': fields.StringField(),
        'context': fields.JsonField(),
        'spec': fields.JsonField(),
        'created_at': fields.DateTimeField(),
        'updated_at': fields.DateTimeField(nullable=True),
        'user': fields.StringField(),
        'project': fields.StringField(),
        'domain': fields.StringField(nullable=True),
        'permission': fields.StringField(nullable=True),
        'metadata': fields.JsonField(nullable=True),
    }

    @classmethod
    def create(cls, context, values):
        values = cls._transpose_metadata(values)
        obj = db_api.profile_create(context, values)
        return cls._from_db_object(context, cls(context), obj)

    @classmethod
    def find(cls, context, identity, **kwargs):
        """Find a profile with the given identity.

        :param context: An instance of the request context.
        :param identity: The UUID, name or short-id of a profile.
        :param project_safe: A boolean indicating whether profile from
                             projects other than the requesting one can be
                             returned.
        :return: A DB object of profile or an exception `ResourceNotFound`
                 if no matching object is found.
        """
        if uuidutils.is_uuid_like(identity):
            profile = cls.get(context, identity, **kwargs)
            if not profile:
                profile = cls.get_by_name(context, identity, **kwargs)
        else:
            profile = cls.get_by_name(context, identity, **kwargs)
            if not profile:
                profile = cls.get_by_short_id(context, identity, **kwargs)

        if not profile:
            raise exception.ResourceNotFound(type='profile', id=identity)

        return profile

    @classmethod
    def get(cls, context, profile_id, **kwargs):
        obj = db_api.profile_get(context, profile_id, **kwargs)
        return cls._from_db_object(context, cls(), obj)

    @classmethod
    def get_by_name(cls, context, name, **kwargs):
        obj = db_api.profile_get_by_name(context, name, **kwargs)
        return cls._from_db_object(context, cls(), obj)

    @classmethod
    def get_by_short_id(cls, context, short_id, **kwargs):
        obj = db_api.profile_get_by_short_id(context, short_id, **kwargs)
        return cls._from_db_object(context, cls(), obj)

    @classmethod
    def get_all(cls, context, **kwargs):
        objs = db_api.profile_get_all(context, **kwargs)
        return [cls._from_db_object(context, cls(), obj) for obj in objs]

    @classmethod
    def update(cls, context, obj_id, values):
        values = cls._transpose_metadata(values)
        obj = db_api.profile_update(context, obj_id, values)
        return cls._from_db_object(context, cls(), obj)

    @classmethod
    def delete(cls, context, obj_id):
        db_api.profile_delete(context, obj_id)

    def to_dict(self):
        profile_dict = {
            'id': self.id,
            'name': self.name,
            'type': self.type,
            'user': self.user,
            'project': self.project,
            'domain': self.domain,
            'spec': self.spec,
            'metadata': self.metadata,
            'created_at': utils.isotime(self.created_at),
            'updated_at': utils.isotime(self.updated_at)
        }
        return profile_dict
