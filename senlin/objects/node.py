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

"""Node object."""

from oslo_utils import uuidutils

from senlin.common import exception
from senlin.common import utils
from senlin.db import api as db_api
from senlin.objects import base
from senlin.objects import fields


@base.SenlinObjectRegistry.register
class Node(base.SenlinObject, base.VersionedObjectDictCompat):
    """Senlin node object."""

    fields = {
        'id': fields.UUIDField(),
        'name': fields.StringField(),
        'profile_id': fields.UUIDField(),
        # This field is treated as string because we may store '' into it
        'cluster_id': fields.StringField(),
        'physical_id': fields.StringField(nullable=True),
        'index': fields.IntegerField(),
        'role': fields.StringField(nullable=True),
        'init_at': fields.DateTimeField(),
        'created_at': fields.DateTimeField(nullable=True),
        'updated_at': fields.DateTimeField(nullable=True),
        'status': fields.StringField(),
        'status_reason': fields.StringField(nullable=True),
        'metadata': fields.JsonField(nullable=True),
        'data': fields.JsonField(nullable=True),
        'user': fields.StringField(),
        'project': fields.StringField(),
        'domain': fields.StringField(nullable=True),
        'dependents': fields.JsonField(nullable=True),
        'profile_name': fields.StringField(nullable=True),
        'profile_created_at': fields.StringField(nullable=True),
    }

    @staticmethod
    def _from_db_object(context, obj, db_obj):
        if db_obj is None:
            return None
        for field in obj.fields:
            if field == 'metadata':
                obj['metadata'] = db_obj['meta_data']
            elif field == 'profile_name':
                p = db_obj['profile']
                obj['profile_name'] = p.name if p else 'Unknown'
            elif field == 'profile_created_at':
                p = db_obj['profile']
                obj['profile_created_at'] = p.created_at if p else None
            else:
                obj[field] = db_obj[field]

        obj._context = context
        obj.obj_reset_changes()

        return obj

    @classmethod
    def create(cls, context, values):
        values = cls._transpose_metadata(values)
        obj = db_api.node_create(context, values)
        # NOTE: We need an extra DB call to make sure the profile is loaded
        #       and bound to the node created.
        obj = db_api.node_get(context, obj.id)
        return cls._from_db_object(context, cls(), obj)

    @classmethod
    def find(cls, context, identity, project_safe=True):
        """Find a node with the given identity.

        :param context: An instance of the request context.
        :param identity: The UUID, name or short-id of a node.
        :param project_safe: A boolean indicating whether only nodes from the
                             same project as the requesting one are qualified
                             to be returned.
        :return: A DB object of Node.
        :raises: An exception of ``ResourceNotFound`` if no matching node is
                 or an exception of ``MultipleChoices`` more than one node
                 found matching the criteria.
        """
        node = None
        if uuidutils.is_uuid_like(identity):
            node = cls.get(context, identity, project_safe=project_safe)
            if not node:
                node = cls.get_by_name(context, identity,
                                       project_safe=project_safe)
        else:
            node = cls.get_by_name(context, identity,
                                   project_safe=project_safe)
            if not node:
                node = cls.get_by_short_id(context, identity,
                                           project_safe=project_safe)

        if node is None:
            raise exception.ResourceNotFound(type='node', id=identity)

        return node

    @classmethod
    def get(cls, context, node_id, **kwargs):
        obj = db_api.node_get(context, node_id, **kwargs)
        return cls._from_db_object(context, cls(), obj)

    @classmethod
    def get_by_name(cls, context, name, **kwargs):
        obj = db_api.node_get_by_name(context, name, **kwargs)
        return cls._from_db_object(context, cls(), obj)

    @classmethod
    def get_by_short_id(cls, context, short_id, **kwargs):
        obj = db_api.node_get_by_short_id(context, short_id, **kwargs)
        return cls._from_db_object(context, cls(), obj)

    @classmethod
    def get_all(cls, context, **kwargs):
        objs = db_api.node_get_all(context, **kwargs)
        return [cls._from_db_object(context, cls(), obj) for obj in objs]

    @classmethod
    def get_all_by_cluster(cls, context, cluster_id, filters=None,
                           project_safe=True):
        objs = db_api.node_get_all_by_cluster(
            context, cluster_id, filters=filters, project_safe=project_safe)
        return [cls._from_db_object(context, cls(), obj) for obj in objs]

    @classmethod
    def ids_by_cluster(cls, context, cluster_id, filters=None):
        """An internal API for retrieving node ids only."""
        return db_api.node_ids_by_cluster(context, cluster_id, filters=filters)

    @classmethod
    def count_by_cluster(cls, context, cluster_id, **kwargs):
        return db_api.node_count_by_cluster(context, cluster_id, **kwargs)

    @classmethod
    def update(cls, context, obj_id, values):
        values = cls._transpose_metadata(values)
        db_api.node_update(context, obj_id, values)

    @classmethod
    def migrate(cls, context, obj_id, to_cluster, timestamp, role=None):
        return db_api.node_migrate(context, obj_id, to_cluster, timestamp,
                                   role=role)

    @classmethod
    def delete(cls, context, obj_id):
        return db_api.node_delete(context, obj_id)

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'cluster_id': self.cluster_id,
            'physical_id': self.physical_id,
            'profile_id': self.profile_id,
            'user': self.user,
            'project': self.project,
            'domain': self.domain,
            'index': self.index,
            'role': self.role,
            'init_at': utils.isotime(self.init_at),
            'created_at': utils.isotime(self.created_at),
            'updated_at': utils.isotime(self.updated_at),
            'status': self.status,
            'status_reason': self.status_reason,
            'data': self.data,
            'metadata': self.metadata,
            'dependents': self.dependents,
            'profile_name': self.profile_name,
        }
