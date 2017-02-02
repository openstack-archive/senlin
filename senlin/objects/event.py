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

"""Event object."""

from oslo_utils import uuidutils

from senlin.common import exception
from senlin.db import api as db_api
from senlin.objects import base
from senlin.objects import fields


@base.SenlinObjectRegistry.register
class Event(base.SenlinObject, base.VersionedObjectDictCompat):
    """Senlin event object."""

    fields = {
        'id': fields.UUIDField(),
        'timestamp': fields.DateTimeField(),
        'oid': fields.UUIDField(),
        'oname': fields.StringField(),
        'otype': fields.StringField(),
        'cluster_id': fields.StringField(nullable=True),
        'level': fields.StringField(),
        'user': fields.StringField(),
        'project': fields.StringField(),
        'action': fields.StringField(nullable=True),
        'status': fields.StringField(),
        'status_reason': fields.StringField(),
        'metadata': fields.JsonField(nullable=True),
    }

    @classmethod
    def create(cls, context, values):
        obj = db_api.event_create(context, values)
        return cls._from_db_object(context, cls(context), obj)

    @classmethod
    def find(cls, context, identity, **kwargs):
        """Find an event with the given identity.

        :param context: An instance of the request context.
        :param identity: The UUID, name or short-id of the event.
        :param dict kwargs: Other keyword query parameters.

        :return: A dictionary containing the details of the event.
        """
        event = None
        if uuidutils.is_uuid_like(identity):
            event = cls.get(context, identity, **kwargs)
        if not event:
            event = cls.get_by_short_id(context, identity, **kwargs)
        if not event:
            raise exception.ResourceNotFound(type='event', id=identity)

        return event

    @classmethod
    def get(cls, context, event_id, **kwargs):
        return db_api.event_get(context, event_id, **kwargs)

    @classmethod
    def get_by_short_id(cls, context, short_id, **kwargs):
        return db_api.event_get_by_short_id(context, short_id, **kwargs)

    @classmethod
    def get_all(cls, context, **kwargs):
        return db_api.event_get_all(context, **kwargs)

    @classmethod
    def count_by_cluster(cls, context, cluster_id, **kwargs):
        return db_api.event_count_by_cluster(context, cluster_id, **kwargs)

    @classmethod
    def get_all_by_cluster(cls, context, cluster_id, **kwargs):
        objs = db_api.event_get_all_by_cluster(context, cluster_id, **kwargs)
        return [cls._from_db_object(context, cls(), obj) for obj in objs]
