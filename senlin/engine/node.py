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

import uuid
import datetime

from senlin.db import api as db_api


class Node(object):
    '''
    A node is an object that can belong to at most one single cluster.

    All operations are performed without further checking because the
    checkings are supposed to be de done before/after/during an action is
    excuted.
    '''

    statuses = (
        ACTIVE, ERROR, DELETED, UPDATING,
    ) = (
        'ACTIVE', 'ERROR', 'DELETED', 'UPDATING',
    )

    def __init__(self, name, profile_id, cluster_id=None, **kwargs):
        if name:
            self.name = name
        else:
            # TODO
            # Using self.physical_resource_name() to generate a unique name
            self.name = 'node-name-tmp'
        self.physical_id = None
        self.cluster_id = cluster_id
        self.profile_id = profile_id
        if cluster_id is None:
            self.index = -1
        else:
            self.index = db_api.get_next_index(cluster_id)
        self.role = ''

        self.created_time = None
        self.updated_time = None
        self.deleted_time = None

        self.status = self.ACTIVE
        self.status_reason = 'Initialized'
        self.data = {}
        self.tags = {}
        # TODO: store this to database

    def create(self, name, profile_id, cluster_id=None, **kwargs):
        # TODO: invoke profile to create new object and get the physical id
        # TODO: log events?
        self.created_time = datetime.datetime.utcnnow()
        return node.id

    def delete(self):
        node = db_api.get_node(self.id)
        # TODO: invoke profile to delete this object
        # TODO: check if actions are working on it and can be canceled

        db_api.delete_node(self.id)
        return True

    def update(self, new_profile_id):
        old_profile = db_api.get_profile(self.profile_id)
        new_profile = db_api.get_profile(new_profile_id)

        # TODO: check if profile type matches
        new_profile_type = new_profile.type_name

        profile_cls = profile_registry.get_class(type_name)

        profile_cls.update_object(self.id, new_profile)
        self.profile_id = new_profile
        self.updated_time = datetime.utcnow()
        return True
