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

import copy

from oslo_context import context as oslo_context
from oslo_log import log as logging
from oslo_utils import timeutils
import six

from senlin.common import context
from senlin.common import exception
from senlin.common.i18n import _
from senlin.common.i18n import _LE
from senlin.common import schema
from senlin.common import utils
from senlin.engine import environment
from senlin.objects import credential as co
from senlin.objects import profile as po

LOG = logging.getLogger(__name__)


class Profile(object):
    '''Base class for profiles.'''

    KEYS = (
        TYPE, VERSION, PROPERTIES,
    ) = (
        'type', 'version', 'properties',
    )

    spec_schema = {
        TYPE: schema.String(
            _('Name of the profile type.'),
            required=True,
        ),
        VERSION: schema.String(
            _('Version number of the profile type.'),
            required=True,
        ),
        PROPERTIES: schema.Map(
            _('Properties for the profile.'),
            required=True,
        )
    }

    properties_schema = {}

    def __new__(cls, name, spec, **kwargs):
        """Create a new profile of the appropriate class.

        :param name: The name for the profile.
        :param spec: A dictionary containing the spec for the profile.
        :param kwargs: Keyword arguments for profile creation.
        :returns: An instance of a specific sub-class of Profile.
        """
        type_name, version = schema.get_spec_version(spec)
        type_str = "-".join([type_name, version])

        if cls != Profile:
            ProfileClass = cls
        else:
            ProfileClass = environment.global_env().get_profile(type_str)

        return super(Profile, cls).__new__(ProfileClass)

    def __init__(self, name, spec, **kwargs):
        """Initialize a profile instance.

        :param name: A string that specifies the name for the profile.
        :param spec: A dictionary containing the detailed profile spec.
        :param kwargs: Keyword arguments for initializing the profile.
        :returns: An instance of a specific sub-class of Profile.
        """

        type_name, version = schema.get_spec_version(spec)
        type_str = "-".join([type_name, version])

        self.name = name
        self.spec = spec

        self.id = kwargs.get('id', None)
        self.type = kwargs.get('type', type_str)

        self.user = kwargs.get('user')
        self.project = kwargs.get('project')
        self.domain = kwargs.get('domain')

        self.metadata = kwargs.get('metadata', {})

        self.created_at = kwargs.get('created_at', None)
        self.updated_at = kwargs.get('updated_at', None)

        self.spec_data = schema.Spec(self.spec_schema, self.spec)
        self.properties = schema.Spec(self.properties_schema,
                                      self.spec.get(self.PROPERTIES, {}))

        if not self.id:
            # new object needs a context dict
            self.context = self._init_context()
        else:
            self.context = kwargs.get('context')

    @classmethod
    def from_object(cls, profile):
        '''Construct a profile from profile object.

        :param profile: a Profle object that contains all required fields.
        '''
        kwargs = {
            'id': profile.id,
            'type': profile.type,
            'context': profile.context,
            'user': profile.user,
            'project': profile.project,
            'domain': profile.domain,
            'metadata': profile.metadata,
            'created_at': profile.created_at,
            'updated_at': profile.updated_at,
        }

        return cls(profile.name, profile.spec, **kwargs)

    @classmethod
    def load(cls, ctx, profile=None, profile_id=None, project_safe=True):
        '''Retrieve a profile object from database.'''
        if profile is None:
            profile = po.Profile.get(ctx, profile_id,
                                     project_safe=project_safe)
            if profile is None:
                raise exception.ProfileNotFound(profile=profile_id)

        return cls.from_object(profile)

    @classmethod
    def load_all(cls, ctx, limit=None, marker=None, sort=None, filters=None,
                 project_safe=True):
        """Retrieve all profiles from database."""

        records = po.Profile.get_all(ctx, limit=limit, marker=marker,
                                     sort=sort, filters=filters,
                                     project_safe=project_safe)

        for record in records:
            yield cls.from_object(record)

    @classmethod
    def delete(cls, ctx, profile_id):
        po.Profile.delete(ctx, profile_id)

    def store(self, ctx):
        '''Store the profile into database and return its ID.'''
        timestamp = timeutils.utcnow(True)

        values = {
            'name': self.name,
            'type': self.type,
            'context': self.context,
            'spec': self.spec,
            'user': self.user,
            'project': self.project,
            'domain': self.domain,
            'meta_data': self.metadata,
        }

        if self.id:
            self.updated_at = timestamp
            values['updated_at'] = timestamp
            po.Profile.update(ctx, self.id, values)
        else:
            self.created_at = timestamp
            values['created_at'] = timestamp
            profile = po.Profile.create(ctx, values)
            self.id = profile.id

        return self.id

    @classmethod
    def create_object(cls, ctx, obj):
        profile = cls.load(ctx, profile_id=obj.profile_id)
        return profile.do_create(obj)

    @classmethod
    def check_object(cls, ctx, obj):
        profile = cls.load(ctx, profile_id=obj.profile_id)
        return profile.do_check(obj)

    @classmethod
    def delete_object(cls, ctx, obj):
        profile = cls.load(ctx, profile_id=obj.profile_id)
        return profile.do_delete(obj)

    @classmethod
    def update_object(cls, ctx, obj, new_profile_id=None, **params):
        profile = cls.load(ctx, profile_id=obj.profile_id)
        new_profile = None
        if new_profile_id:
            new_profile = cls.load(ctx, profile_id=new_profile_id)
        return profile.do_update(obj, new_profile, **params)

    @classmethod
    def recover_object(cls, ctx, obj, **options):
        profile = cls.load(ctx, profile_id=obj.profile_id)
        return profile.do_recover(obj, **options)

    @classmethod
    def get_details(cls, ctx, obj):
        profile = cls.load(ctx, profile_id=obj.profile_id)
        return profile.do_get_details(obj)

    @classmethod
    def join_cluster(cls, ctx, obj, cluster_id):
        profile = cls.load(ctx, profile_id=obj.profile_id)
        return profile.do_join(obj, cluster_id)

    @classmethod
    def leave_cluster(cls, ctx, obj):
        profile = cls.load(ctx, profile_id=obj.profile_id)
        return profile.do_leave(obj)

    def validate(self):
        '''Validate the schema and the data provided.'''
        # general validation
        self.spec_data.validate()
        self.properties.validate()

        # TODO(Anyone): need to check the contents in self.CONTEXT

    @classmethod
    def get_schema(cls):
        return dict((name, dict(schema))
                    for name, schema in cls.properties_schema.items())

    def _init_context(self):
        profile_context = {}
        if self.CONTEXT in self.properties:
            profile_context = self.properties[self.CONTEXT] or {}

        ctx_dict = context.get_service_context(**profile_context)

        ctx_dict.pop('project_name', None)
        ctx_dict.pop('project_domain_name', None)

        return ctx_dict

    def _build_conn_params(self, user, project):
        """Build connection params for specific user and project.

        :param user: The ID of the user for which a trust will be used.
        :param project: The ID of the project for which a trust will be used.
        :returns: A dict containing the required parameters for connection
                  creation.
        """
        cred = co.Credential.get(oslo_context.get_current(), user, project)
        if cred is None:
            raise exception.TrustNotFound(trustor=user)

        trust_id = cred.cred['openstack']['trust']

        # This is supposed to be trust-based authentication
        params = copy.deepcopy(self.context)
        params['trust_id'] = trust_id

        return params

    def do_create(self, obj):
        '''For subclass to override.'''

        return NotImplemented

    def do_delete(self, obj):
        '''For subclass to override.'''

        return NotImplemented

    def do_update(self, obj, new_profile, **params):
        '''For subclass to override.'''

        return NotImplemented

    def do_check(self, obj):
        '''For subclass to override.'''
        return NotImplemented

    def do_get_details(self, obj):
        '''For subclass to override.'''
        return NotImplemented

    def do_join(self, obj, cluster_id):
        '''For subclass to override to perform extra operations.'''
        return True

    def do_leave(self, obj):
        '''For subclass to override to perform extra operations.'''
        return True

    def do_rebuild(self, obj):
        '''For subclass to override.'''
        return NotImplemented

    def do_recover(self, obj, **options):
        '''For subclass to override.'''

        operation = options.get('operation', None)
        if operation and operation != 'RECREATE':
            return NotImplemented

        # NOTE: do_delete always returns a boolean
        res = self.do_delete(obj)

        if res:
            try:
                res = self.do_create(obj)
            except Exception as ex:
                LOG.exception(_('Failed at recovering obj: %s '),
                              six.text_type(ex))
                return False

        return res

    def to_dict(self):
        pb_dict = {
            'id': self.id,
            'name': self.name,
            'type': self.type,
            'user': self.user,
            'project': self.project,
            'domain': self.domain,
            'spec': self.spec,
            'metadata': self.metadata,
            'created_at': utils.format_time(self.created_at),
            'updated_at': utils.format_time(self.updated_at),
        }
        return pb_dict

    def validate_for_update(self, new_profile):
        non_updatables = []
        for (k, v) in new_profile.properties.items():
            if self.properties.get(k, None) != v:
                if not self.properties_schema[k].updatable:
                    non_updatables.append(k)

        if not non_updatables:
            return True

        msg = ", ".join(non_updatables)
        LOG.error(_LE("The following properties are not updatable: %s."
                      ) % msg)
        return False
