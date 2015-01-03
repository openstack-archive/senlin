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
from senlin.profiles import base as profiles


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

    def __init__(self, context, name, profile_id, **kwargs):
        self.context = context
        self.id = kwargs.get('id', None)
        if name:
            self.name = name
        else:
            # TODO(Qiming): Use self.physical_resource_name() to
            #               generate a unique name
            self.name = 'node-name-tmp'

        self.physical_id = kwargs.get('physical_id', '')
        self.profile_id = profile_id
        self.cluster_id = kwargs.get('cluster_id', '')
        self.index = kwargs.get('index', -1)
        self.role = kwargs.get('role', '')
        self.created_time = kwargs.get('created_time', None)
        self.updated_time = kwargs.get('updated_time', None)
        self.deleted_time = kwargs.get('deleted_time', None)

        self.status = kwargs.get('status', self.INIT)
        self.status_reason = kwargs.get('status_reason', 'Initializing')
        self.data = kwargs.get('data', {})
        self.tags = kwargs.get('tags', {})

        self.rt = {
            'profile': profiles.load(context, self.profile_id),
        }

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
        return cls(context, record.name, record.profile_id, **kwargs)

    @classmethod
    def load(cls, context, node_id):
        '''
        Retrieve a node from database.
        '''
        record = db_api.node_get(context, node_id)

        if record is None:
            msg = _('No node with id "%s" exists') % node_id
            raise exception.NotFound(msg)

        return cls.from_db_record(context, record)

    @classmethod
    def load_all(cls, context, cluster_id):
        '''
        Retrieve all nodes of from database.
        '''
        records = db_api.node_get_all_by_cluster(context, cluster_id)

        for record in records:
            yield cls.from_db_record(context, record)

    def do_create(self):
        # TODO(Qiming): log events?
        self.created_time = datetime.datetime.utcnnow()
        res = profiles.create_object(self)
        if res:
            self.physical_id = res
            return True
        else:
            return False

    def do_delete(self):
        if not self.physical_id:
            return True

        # TODO(Qiming): check if actions are working on it and can be canceled
        # TODO(Qiming): log events
        res = profiles.delete_object(self)
        if res:
            db_api.delete_node(self.id)
            return True
        else:
            return False

    def do_update(self, new_profile_id):
        if not new_profile_id:
            raise exception.ProfileNotSpecified()

        if new_profile_id == self.profile_id:
            return True

        if not self.physical_id:
            return False

        # Check if profile types match
        old_profile = db_api.get_profile(context, self.profile_id)
        new_profile = db_api.get_profile(context, new_profile_id)
        if old_profile.type != new_profile.type:
            events.warning(_LW('Node cannot be updated to a different '
                               'profile type (%(oldt)s->%(newt)s)'),
                           {'oldt': old_profile.type,
                            'newt': new_profile.type})
            return False

        res = profiles.update_object(self, new_profile_id)
        if res:
            self.rt['profile'] = profiles.load(self.context, new_profile_id)
            self.profile_id = new_profile_id
            self.updated_time = datetime.datetime.utcnow()
            db_api.node_update(self.context, self.id,
                               {'profile_id': self.profile_id,
                                'updated_time': self.updated_time})

        return res

    def do_join(self, cluster_id):
        if self.cluster_id == cluster_id:
            return True

        db_api.node_migrate(self.context, self.id, self.cluster_id,
                            cluster_id)

        self.updated_time = datetime.datetime.utcnow()
        db_api.node_update(self.context, self.id,
                           {'updated_time': self.updated_time})
        return True

    def do_leave(self):
        if self.cluster_id is None:
            return True

        db_api.node_migrate(self.context, self.id, self.cluster_id, None)
        self.updated_time = datetime.datetime.utcnow()
        db_api.node_update(self.context, self.id,
                           {'updated_time': self.updated_time})

        return True
