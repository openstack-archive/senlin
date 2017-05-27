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

"""Receiver object."""

from oslo_utils import uuidutils

from senlin.common import exception
from senlin.common import utils
from senlin.db import api as db_api
from senlin.objects import base
from senlin.objects import fields


@base.SenlinObjectRegistry.register
class Receiver(base.SenlinObject, base.VersionedObjectDictCompat):
    """Senlin receiver object."""

    fields = {
        'id': fields.UUIDField(),
        'name': fields.StringField(),
        'type': fields.StringField(),
        'cluster_id': fields.StringField(nullable=True),
        'actor': fields.JsonField(nullable=True),
        'action': fields.StringField(nullable=True),
        'params': fields.JsonField(nullable=True),
        'channel': fields.JsonField(nullable=True),
        'created_at': fields.DateTimeField(nullable=True),
        'updated_at': fields.DateTimeField(nullable=True),
        'user': fields.StringField(),
        'project': fields.StringField(),
        'domain': fields.StringField(nullable=True),
    }

    @classmethod
    def create(cls, context, values):
        obj = db_api.receiver_create(context, values)
        return cls._from_db_object(context, cls(context), obj)

    @classmethod
    def find(cls, context, identity, **kwargs):
        """Find a receiver with the given identity.

        :param context: An instance of the request context.
        :param identity: The UUID, name or short-id of a receiver.
        :param project_safe: A boolean indicating whether receiver from other
                             projects other than the requesting one can be
                             returned.
        :return: A DB object of receiver or an exception `ResourceNotFound`
                 if no matching receiver is found.
        """
        if uuidutils.is_uuid_like(identity):
            receiver = cls.get(context, identity, **kwargs)
            if not receiver:
                receiver = cls.get_by_name(context, identity, **kwargs)
        else:
            receiver = cls.get_by_name(context, identity, **kwargs)
            if not receiver:
                receiver = cls.get_by_short_id(context, identity, **kwargs)

        if not receiver:
            raise exception.ResourceNotFound(type='receiver', id=identity)

        return receiver

    @classmethod
    def get(cls, context, receiver_id, **kwargs):
        obj = db_api.receiver_get(context, receiver_id, **kwargs)
        return cls._from_db_object(context, cls(), obj)

    @classmethod
    def get_by_name(cls, context, name, **kwargs):
        obj = db_api.receiver_get_by_name(context, name, **kwargs)
        return cls._from_db_object(context, cls(), obj)

    @classmethod
    def get_by_short_id(cls, context, short_id, **kwargs):
        obj = db_api.receiver_get_by_short_id(context, short_id, **kwargs)
        return cls._from_db_object(context, cls(), obj)

    @classmethod
    def get_all(cls, context, **kwargs):
        objs = db_api.receiver_get_all(context, **kwargs)
        return [cls._from_db_object(context, cls(), obj) for obj in objs]

    @classmethod
    def update(cls, context, receiver_id, values):
        values = cls._transpose_metadata(values)
        obj = db_api.receiver_update(context, receiver_id, values)
        return cls._from_db_object(context, cls(), obj)

    @classmethod
    def delete(cls, context, receiver_id):
        db_api.receiver_delete(context, receiver_id)

    def to_dict(self):
        receiver_dict = {
            'id': self.id,
            'name': self.name,
            'type': self.type,
            'user': self.user,
            'project': self.project,
            'domain': self.domain,
            'created_at': utils.isotime(self.created_at),
            'updated_at': utils.isotime(self.updated_at),
            'cluster_id': self.cluster_id,
            'actor': self.actor,
            'action': self.action,
            'params': self.params,
            'channel': self.channel,
        }
        return receiver_dict
