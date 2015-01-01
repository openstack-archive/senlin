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

import datetime

from senlin.common import exception
from senlin.db import api as db_api
from senlin.engine import environment


class Node(object):
    '''
    A node is an object that can belong to at most one single cluster.

    All operations are performed without further checking because the
    checkings are supposed to be de done before/after/during an action is
    excuted.
    '''

    statuses = (
        INIT, ACTIVE, ERROR, DELETED, UPDATING,
    ) = (
        'INITIALIZING', 'ACTIVE', 'ERROR', 'DELETED', 'UPDATING',
    )

    def __init__(self, name, profile_id, cluster_id=None, **kwargs):
        self.id = kwargs.get('id', None)
        if name:
            self.name = name
        else:
            # TODO(Qiming): Use self.physical_resource_name() to
            #               generate a unique name
            self.name = 'node-name-tmp'

        self.physical_id = kwargs.get('physical_id', '')
        self.profile_id = profile_id
        self.cluster_id = cluster_id or ''
        self.index = kwargs.get('index', -1)
        self.role = kwargs.get('role', '')
        self.created_time = kwargs.get('created_time', None)
        self.updated_time = kwargs.get('updated_time', None)
        self.deleted_time = kwargs.get('deleted_time', None)

        self.status = kwargs.get('status', self.INIT)
        self.status_reason = kwargs.get('status_reason', 'Initializing')
        self.data = kwargs.get('data', {})
        self.tags = kwargs.get('tags', {})

    def store(self):
        '''
        Store the node record into database table.

        The invocation of DB API could be a node_create or a node_update,
        depending on whether node has an ID assigned.
        '''

        values = {
            'name': self.name,
            'physical_id': self.physical_id,
            'cluster_id': self.cluster_id,
            'profile_id': self.profile_id,
            'index': self.index,
            'role': self.role,
            'created_time': self.created_time,
            'updated_time': self.updated_time,
            'deleted_time': self.deleted_time,
            'status': self.status,
            'status_reason': self.status_reason,
            'data': self.data,
            'tags': self.tags,
        }

        if self.id:
            db_api.node_update(self.context, self.id, values)
            # TODO(Qiming): create event/log
        else:
            node = db_api.node_create(self.context, values)
            # TODO(Qiming): create event/log
            self.id = node.id

        return self.id

    @classmethod
    def from_db_record(cls, context, record):
        '''
        Construct a node object from database record.
        :param context: the context used for DB operations;
        :param record: a DB node object that contains all fields;
        '''
        kwargs = {
            'id': record.id,
            'physical_id': record.physical_id,
            'index': record.index,
            'role': record.role,
            'created_time': record.created_time,
            'updated_time': record.updated_time,
            'deleted_time': record.deleted_time,
            'status': record.status,
            'status_reason': record.status_reason,
            'data': record.data,
            'tags': record.tags,
        }
        return cls(context, record.name, record.profile_id, record.size,
                   **kwargs)

    @classmethod
    def load(cls, context, node_id):
        '''
        Retrieve a node from database.
        '''
        node = db_api.node_get(context, node_id)

        if node is None:
            msg = _('No node with id "%s" exists') % node_id
            raise exception.NotFound(msg)

        return cls.from_db_record(context, node)

    @classmethod
    def load_all(cls, context, cluster_id):
        '''
        Retrieve all nodes of from database.
        '''
        records = db_api.node_get_all_by_cluster(context, cluster_id)

        for record in records:
            yield cls.from_db_record(context, record)

    def create(self, name, profile_id, cluster_id=None, **kwargs):
        # TODO(Qiming): invoke profile to create new object and get the
        #               physical id
        # TODO(Qiming): log events?
        self.created_time = datetime.datetime.utcnnow()
        profile = db_api.get_profile(profile_id)
        profile_cls = environment.global_env().get_profile(profile.type)
        node = profile_cls.create_object(self.id, profile_id)

        return node.id

    def delete(self):
        # node = db_api.node_get(self.id)
        # physical_id = node.physical_id

        # TODO(Qiming): invoke profile to delete this object
        # TODO(Qiming): check if actions are working on it and can be canceled

        db_api.delete_node(self.id)
        return True

    def join(self, cluster):
        return True

    def leave(self, cluster):
        return True

    def update(self, new_profile_id):
        new_profile = db_api.get_profile(new_profile_id)

        if self.profile_id == new_profile.id:
            return True

        new_type = new_profile.type_name

        profile_cls = environment.global_env().get_profile(new_type)

        profile_cls.update_object(self.id, new_profile)
        self.profile_id = new_profile
        self.updated_time = datetime.utcnow()
        return True
