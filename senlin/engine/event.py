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


class Event(object):
    '''
    Class capturing a cluster operation or state change.
    '''

    def __init__(self, context, entity, action, status, reason,
                 level, timestamp, entity_type='CLUSTER')
        self.context = context
        self.entity = entity 
        self.action = action
        self.level = level
        self.status = status
        self.reason = reason
        self.timestamp = timestamp
        self.id = id

        # TODO: write to database

    @classmethod
    def add_event(cls):
        pass

    @classmethod
    def add_cluster_event(cls, context, entity, action, status, reason,
                          level, timestamp)
        pass

    @classmethod
    def add_member_event(cls, context, entity, action, status, reason,
                         level, timestamp, entity_type='MEMBER')
        pass

    @classmethod
    def add_policy_event(cls, context, entity, action, status, reason,
                         level, timestamp, entity_type='POLICY')
        pass

    @classmethod
    def add_profile_event(cls, context, entity, action, status, reason,
                          level, timestamp, entity_type='PROFILE')
        pass
