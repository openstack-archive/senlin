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
from datatime import datetime

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
        self.name = name
        self.uuid = str(uuid.uuid4())
        self.physical_id = None
        self.cluster_id = cluster_id
        self.index = db_api.next_index(cluster_id) if cluster_id or -1
        self.profile_id = profile_id
        self.role = None
        self.status = self.ACTIVE
        self.status_reason = 'Initialized'
        self.created_time = None
        self.updated_time = None

        # TODO: store this to database

    def create(self, name, profile_id, cluster_id=None, **kwargs):
        # TODO: invoke profile to create new object and get the physical id
        # TODO: log events?
        self.created_time = datetime.utcnnow()
        return node.uuid

    def delete(self):
        node = db_api.get_node(self.uuid)
        # TODO: invoke profile to delete this object
        # TODO: check if actions are working on it and can be canceled

        db_api.delete_node(self.uuid)
        return True

    def update(self, new_profile_id):
        old_profile = db_api.get_profile(self.profile_id)
        new_profile = db_api.get_profile(new_profile_id)

        # TODO: check if profile type matches
        new_profile_type = new_profile.type_name

        profile_cls = profile_registry.get_class(type_name)

        profile_cls.update_object(self.uuid, new_profile)
        self.profile_id = new_profile
        self.updated_time = datetime.utcnow()
        return True
