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

"""Policy object."""

from oslo_utils import uuidutils

from senlin.common import exception
from senlin.db import api as db_api
from senlin.objects import base
from senlin.objects import fields


@base.SenlinObjectRegistry.register
class Policy(base.SenlinObject, base.VersionedObjectDictCompat):
    """Senlin policy object."""

    fields = {
        'id': fields.UUIDField(),
        'name': fields.StringField(),
        'type': fields.StringField(),
        'spec': fields.JsonField(),
        'cooldown': fields.IntegerField(nullable=True),
        'level': fields.IntegerField(nullable=True),
        'data': fields.JsonField(nullable=True),
        'created_at': fields.DateTimeField(),
        'updated_at': fields.DateTimeField(nullable=True),
        'user': fields.StringField(),
        'project': fields.StringField(),
        'domain': fields.StringField(nullable=True),
    }

    @classmethod
    def create(cls, context, values):
        values = cls._transpose_metadata(values)
        obj = db_api.policy_create(context, values)
        return cls._from_db_object(context, cls(context), obj)

    @classmethod
    def find(cls, context, identity, **kwargs):
        """Find a policy with the given identity.

        :param context: An instance of the request context.
        :param identity: The UUID, name or short-id of a profile.
        :param project_safe: A boolean indicating whether policies from
                             projects other than the requesting one should be
                             evaluated.
        :return: A DB object of policy or an exception of `ResourceNotFound`
                 if no matching object is found.
        """
        if uuidutils.is_uuid_like(identity):
            policy = cls.get(context, identity, **kwargs)
            if not policy:
                policy = cls.get_by_name(context, identity, **kwargs)
        else:
            policy = cls.get_by_name(context, identity, **kwargs)
            if not policy:
                policy = cls.get_by_short_id(context, identity, **kwargs)

        if not policy:
            raise exception.ResourceNotFound(type='policy', id=identity)

        return policy

    @classmethod
    def get(cls, context, policy_id, **kwargs):
        obj = db_api.policy_get(context, policy_id, **kwargs)
        return cls._from_db_object(context, cls(), obj)

    @classmethod
    def get_by_name(cls, context, name, **kwargs):
        obj = db_api.policy_get_by_name(context, name, **kwargs)
        return cls._from_db_object(context, cls(), obj)

    @classmethod
    def get_by_short_id(cls, context, short_id, **kwargs):
        obj = db_api.policy_get_by_short_id(context, short_id, **kwargs)
        return cls._from_db_object(context, cls(), obj)

    @classmethod
    def get_all(cls, context, **kwargs):
        objs = db_api.policy_get_all(context, **kwargs)
        return [cls._from_db_object(context, cls(), obj) for obj in objs]

    @classmethod
    def update(cls, context, obj_id, values):
        values = cls._transpose_metadata(values)
        obj = db_api.policy_update(context, obj_id, values)
        return cls._from_db_object(context, cls(), obj)

    @classmethod
    def delete(cls, context, obj_id):
        db_api.policy_delete(context, obj_id)

    def to_dict(self):
        policy_dict = {
            'id': self.id,
            'name': self.name,
            'type': self.type,
            'user': self.user,
            'project': self.project,
            'domain': self.domain,
            'spec': self.spec,
            'created_at': self.created_at,
            'updated_at': self.updated_at,
            'data': self.data
        }
        return policy_dict
