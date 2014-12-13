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


class Action(object):
    '''
    An action can be performed on a cluster or a member of a cluster.
    '''

    def __init__(self, context):
        self.context = context
        # the context should contain a request ID
        self.request_id = context['request_id']

    def execute(self):
        return NotImplemented

    def cancel(self):
        return NotImplemented


class ClusterAction(Action):
    '''
    An action performed on a cluster.
    '''

    def __init__(self, context, cluster_id):
        super(ClusterAction, self).__init__(context)


    def execute(self):
        pass

    def cancel(self):
        pass


class MemberAction(Action):
    '''
    An action performed on a cluster member.
    '''
    def __init__(self, context, member_id):
        super(MemberAction, self).__init__(context)

        # get cluster of this member
        # get policies associated with the cluster

    def execute(self):
        pass

    def cancel(self):
        pass
