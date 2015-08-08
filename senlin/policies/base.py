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

from oslo_utils import timeutils

from senlin.common import exception
from senlin.common.i18n import _
from senlin.common import schema
from senlin.db import api as db_api
from senlin.engine import environment

# Default enforcement levels and level names.
#
#  - MUST: A policy of this enforcement level must be strictly checked. A
#          violation of such a policy will lead a cluster to ``CRITICAL``
#          status, which means that the cluster is in a problematic status
#          that cannot be recovered using Senlin APIs. A manual intervention
#          is needed. Such a cluster should not be treated as funtional any
#          more.
#
#  - SHOULD: A violation of a policy at this enforcement level will render a
#            cluster into an ``ERROR`` status. A manual intervention is needed
#            to recover the cluster. The cluster may and may not be providing
#            services in the ``ERROR`` status.
#
#  - WOULD: A policy of this enforcement level is usually about some
#           operations that would be done when the policy is enforced. A
#           violation of the policy will leave the cluster in a ``WARNING``
#           status, which means that the cluster is still operational, but
#           there are unsuccessful operations attempted.
#
#  - MIGHT: A policy of this enforcement level is usually associated with
#           certain operations that may or may not be done. A violation of
#           this policy will not cause any negative impact to the cluster.
#

POLICY_LEVELS = (
    MUST, SHOULD, WOULD, MIGHT,
) = (
    50, 40, 30, 20
)

_levelNames = {
    MUST: 'MUST',
    SHOULD: 'SHOULD',
    WOULD: 'WOULD',
    MIGHT: 'MIGHT',
    'MUST': MUST,
    'SHOULD': SHOULD,
    'WOULD': WOULD,
    'MIGHT': MIGHT,
}

CHECK_RESULTS = (
    CHECK_OK, CHECK_ERROR
) = (
    'OK', 'ERROR'
)


def getLevelName(level):
    '''Get a level name or number.

    Return a level name if given a numeric value; or return a value if given
    a string.  If level is not predefined, "Level %s" will be returned.
    '''
    return _levelNames.get(level, ("Level %s" % level))


class Policy(object):
    '''Base class for policies.'''
    PROFILE_TYPE = 'ANY'

    def __new__(cls, type_name, name, **kwargs):
        '''Create a new policy of the appropriate class.'''

        if cls != Policy:
            PolicyClass = cls
        else:
            PolicyClass = environment.global_env().get_policy(type_name)

        return super(Policy, cls).__new__(PolicyClass)

    def __init__(self, type_name, name, **kwargs):
        self.name = name
        self.type = type_name

        self.id = kwargs.get('id', None)
        self.user = kwargs.get('user')
        self.project = kwargs.get('project')
        self.domain = kwargs.get('domain')
        self.level = kwargs.get('level', 0)
        self.cooldown = kwargs.get('cooldown', None)
        self.spec = kwargs.get('spec', {})
        self.data = kwargs.get('data', {})
        self.created_time = kwargs.get('created_time', None)
        self.updated_time = kwargs.get('updated_time', None)
        self.deleted_time = kwargs.get('deleted_time', None)

        self.spec_data = schema.Spec(self.spec_schema, self.spec)

    @classmethod
    def _from_db_record(cls, record):
        '''Construct a policy object from a database record.'''

        kwargs = {
            'id': record.id,
            'user': record.user,
            'project': record.project,
            'domain': record.domain,
            'spec': record.spec,
            'level': record.level,
            'cooldown': record.cooldown,
            'created_time': record.created_time,
            'updated_time': record.updated_time,
            'deleted_time': record.deleted_time,
            'data': record.data,
        }

        return cls(record.type, record.name, **kwargs)

    @classmethod
    def load(cls, context, policy_id=None, policy=None):
        '''Retrieve and reconstruct a policy object from DB.'''
        if policy is None:
            policy = db_api.policy_get(context, policy_id)
            if policy is None:
                raise exception.PolicyNotFound(policy=policy_id)

        return cls._from_db_record(policy)

    @classmethod
    def load_all(cls, context, limit=None, sort_keys=None, marker=None,
                 sort_dir=None, filters=None, show_deleted=False):
        '''Retrieve all policies from database.'''

        records = db_api.policy_get_all(context, limit=limit, marker=marker,
                                        sort_keys=sort_keys,
                                        sort_dir=sort_dir,
                                        filters=filters,
                                        show_deleted=show_deleted)

        for record in records:
            yield cls._from_db_record(record)

    @classmethod
    def delete(cls, context, policy_id):
        db_api.policy_delete(context, policy_id)

    def store(self, context):
        '''Store the policy object into database table.'''
        timestamp = timeutils.utcnow()

        values = {
            'name': self.name,
            'type': self.type,
            'user': self.user,
            'project': self.project,
            'domain': self.domain,
            'spec': self.spec,
            'level': self.level,
            'cooldown': self.cooldown,
            'data': self.data,
        }

        if self.id is not None:
            self.updated_time = timestamp
            values['updated_time'] = timestamp
            db_api.policy_update(context, self.id, values)
        else:
            self.created_time = timestamp
            values['created_time'] = timestamp
            policy = db_api.policy_create(context, values)
            self.id = policy.id

        return self.id

    def validate(self):
        '''Validate the schema and the data provided.'''
        self.spec_data.validate()

    @classmethod
    def get_schema(cls):
        return dict((name, dict(schema))
                    for name, schema in cls.spec_schema.items())

    def _build_policy_data(self, data):
        clsname = self.__class__.__name__
        version = self.VERSION
        result = {
            clsname: {
                'version': version,
                'data': data,
            }
        }
        return result

    def _extract_policy_data(self, policy_data):
        clsname = self.__class__.__name__
        if clsname not in policy_data:
            return None
        data = policy_data.get(clsname)
        if 'version' not in data or data['version'] != self.VERSION:
            return None

        return data.get('data', None)

    def attach(self, cluster):
        '''Method to be invoked before policy is attached to a cluster.

        :param cluster: the cluster to which the policy is being attached to.
        :returns: (True, message) if the operation is successful, or (False,
                 error) otherwise.
        '''
        if self.PROFILE_TYPE == ['ANY']:
            return True, None

        profile = cluster.rt['profile']
        if profile.type not in self.PROFILE_TYPE:
            error = _('Policy not applicable on profile type:'
                      '%s') % profile.type
            return False, error

        return True, None

    def detach(self, cluster):
        '''Method to be invoked before policy is detached from a cluster.'''
        return True, None

    def pre_op(self, cluster_id, action):
        '''A method that will be invoked before an action execution.'''
        return

    def post_op(self, cluster_id, action):
        '''A method that will be invoked after an action execution.'''
        return

    def to_dict(self):
        def _fmt_time(value):
            return value and value.isoformat()

        pb_dict = {
            'id': self.id,
            'name': self.name,
            'type': self.type,
            'user': self.user,
            'project': self.project,
            'domain': self.domain,
            'spec': self.spec,
            'level': self.level,
            'cooldown': self.cooldown,
            'created_time': _fmt_time(self.created_time),
            'updated_time': _fmt_time(self.updated_time),
            'deleted_time': _fmt_time(self.deleted_time),
            'data': self.data,
        }
        return pb_dict

    @classmethod
    def from_dict(cls, **kwargs):
        type_name = kwargs.pop('type')
        name = kwargs.pop('name')
        return cls(type_name, name, **kwargs)
