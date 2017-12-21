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
import inspect

from oslo_context import context as oslo_context
from oslo_log import log as logging
from oslo_utils import timeutils
from osprofiler import profiler
import six

from senlin.common import consts
from senlin.common import context
from senlin.common import exception as exc
from senlin.common.i18n import _
from senlin.common import schema
from senlin.common import utils
from senlin.drivers import base as driver_base
from senlin.engine import environment
from senlin.objects import credential as co
from senlin.objects import profile as po

LOG = logging.getLogger(__name__)


class Profile(object):
    """Base class for profiles."""

    VERSIONS = {}

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
    OPERATIONS = {}

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
        self.type_name = type_name
        self.version = version
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
        self.properties = schema.Spec(
            self.properties_schema,
            self.spec.get(self.PROPERTIES, {}),
            version)

        if not self.id:
            # new object needs a context dict
            self.context = self._init_context()
        else:
            self.context = kwargs.get('context')

        # initialize clients
        self._computeclient = None
        self._networkclient = None
        self._orchestrationclient = None
        self._workflowclient = None
        self._block_storageclient = None

    @classmethod
    def _from_object(cls, profile):
        '''Construct a profile from profile object.

        :param profile: a profile object that contains all required fields.
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
                raise exc.ResourceNotFound(type='profile', id=profile_id)

        return cls._from_object(profile)

    @classmethod
    def create(cls, ctx, name, spec, metadata=None):
        """Create a profile object and validate it.

        :param ctx: The requesting context.
        :param name: The name for the profile object.
        :param spec: A dict containing the detailed spec.
        :param metadata: An optional dictionary specifying key-value pairs to
                         be associated with the profile.
        :returns: An instance of Profile.
        """
        if metadata is None:
            metadata = {}

        try:
            profile = cls(name, spec, metadata=metadata, user=ctx.user_id,
                          project=ctx.project_id)
            profile.validate(True)
        except (exc.ResourceNotFound, exc.ESchema) as ex:
            error = _("Failed in creating profile %(name)s: %(error)s"
                      ) % {"name": name, "error": six.text_type(ex)}
            raise exc.InvalidSpec(message=error)

        profile.store(ctx)

        return profile

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
    @profiler.trace('Profile.create_object', hide_args=False)
    def create_object(cls, ctx, obj):
        profile = cls.load(ctx, profile_id=obj.profile_id)
        return profile.do_create(obj)

    @classmethod
    @profiler.trace('Profile.create_cluster_object', hide_args=False)
    def create_cluster_object(cls, ctx, obj):
        profile = cls.load(ctx, profile_id=obj.profile_id)
        try:
            ret = profile.do_cluster_create(obj)
        except NotImplementedError:
            return None
        return ret

    @classmethod
    @profiler.trace('Profile.delete_object', hide_args=False)
    def delete_object(cls, ctx, obj, **params):
        profile = cls.load(ctx, profile_id=obj.profile_id)
        return profile.do_delete(obj, **params)

    @classmethod
    @profiler.trace('Profile.delete_cluster_object', hide_args=False)
    def delete_cluster_object(cls, ctx, obj, **params):
        profile = cls.load(ctx, profile_id=obj.profile_id)
        try:
            ret = profile.do_cluster_delete(obj, **params)
        except NotImplementedError:
            return None
        return ret

    @classmethod
    @profiler.trace('Profile.update_object', hide_args=False)
    def update_object(cls, ctx, obj, new_profile_id=None, **params):
        profile = cls.load(ctx, profile_id=obj.profile_id)
        new_profile = None
        if new_profile_id:
            new_profile = cls.load(ctx, profile_id=new_profile_id)
        return profile.do_update(obj, new_profile, **params)

    @classmethod
    @profiler.trace('Profile.get_details', hide_args=False)
    def get_details(cls, ctx, obj):
        profile = cls.load(ctx, profile_id=obj.profile_id)
        return profile.do_get_details(obj)

    @classmethod
    @profiler.trace('Profile.adopt_node', hide_args=False)
    def adopt_node(cls, ctx, obj, type_name, overrides=None, snapshot=False):
        """Adopt a node.

        :param ctx: Request context.
        :param obj: A temporary node object.
        :param overrides: An optional parameter that specifies the set of
            properties to be overridden.
        :param snapshot: A boolean flag indicating whether a snapshot should
            be created before adopting the node.
        :returns: A dictionary containing the profile spec created from the
            specific node, or a dictionary containing error message.
        """
        parts = type_name.split("-")
        tmpspec = {"type": parts[0], "version": parts[1]}
        profile = cls("name", tmpspec)
        return profile.do_adopt(obj, overrides=overrides, snapshot=snapshot)

    @classmethod
    @profiler.trace('Profile.join_cluster', hide_args=False)
    def join_cluster(cls, ctx, obj, cluster_id):
        profile = cls.load(ctx, profile_id=obj.profile_id)
        return profile.do_join(obj, cluster_id)

    @classmethod
    @profiler.trace('Profile.leave_cluster', hide_args=False)
    def leave_cluster(cls, ctx, obj):
        profile = cls.load(ctx, profile_id=obj.profile_id)
        return profile.do_leave(obj)

    @classmethod
    @profiler.trace('Profile.check_object', hide_args=False)
    def check_object(cls, ctx, obj):
        profile = cls.load(ctx, profile_id=obj.profile_id)
        try:
            return profile.do_check(obj)
        except exc.InternalError as ex:
            LOG.error(ex)
            return False

    @classmethod
    @profiler.trace('Profile.recover_object', hide_args=False)
    def recover_object(cls, ctx, obj, **options):
        profile = cls.load(ctx, profile_id=obj.profile_id)
        return profile.do_recover(obj, **options)

    def validate(self, validate_props=False):
        """Validate the schema and the data provided."""
        # general validation
        self.spec_data.validate()
        self.properties.validate()

        ctx_dict = self.properties.get('context', {})
        if ctx_dict:
            argspec = inspect.getargspec(context.RequestContext.__init__)
            valid_keys = argspec.args
            bad_keys = [k for k in ctx_dict if k not in valid_keys]
            if bad_keys:
                msg = _("Some keys in 'context' are invalid: %s") % bad_keys
                raise exc.ESchema(message=msg)

        if validate_props:
            self.do_validate(obj=self)

    @classmethod
    def get_schema(cls):
        return dict((name, dict(schema))
                    for name, schema in cls.properties_schema.items())

    @classmethod
    def get_ops(cls):
        return dict((name, dict(schema))
                    for name, schema in cls.OPERATIONS.items())

    def _init_context(self):
        profile_context = {}
        if self.CONTEXT in self.properties:
            profile_context = self.properties[self.CONTEXT] or {}

        ctx_dict = context.get_service_credentials(**profile_context)

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
            raise exc.TrustNotFound(trustor=user)

        trust_id = cred.cred['openstack']['trust']

        # This is supposed to be trust-based authentication
        params = copy.deepcopy(self.context)
        params['trust_id'] = trust_id

        return params

    def compute(self, obj):
        '''Construct compute client based on object.

        :param obj: Object for which the client is created. It is expected to
                    be None when retrieving an existing client. When creating
                    a client, it contains the user and project to be used.
        '''

        if self._computeclient is not None:
            return self._computeclient
        params = self._build_conn_params(obj.user, obj.project)
        self._computeclient = driver_base.SenlinDriver().compute(params)
        return self._computeclient

    def network(self, obj):
        """Construct network client based on object.

        :param obj: Object for which the client is created. It is expected to
                    be None when retrieving an existing client. When creating
                    a client, it contains the user and project to be used.
        """
        if self._networkclient is not None:
            return self._networkclient
        params = self._build_conn_params(obj.user, obj.project)
        self._networkclient = driver_base.SenlinDriver().network(params)
        return self._networkclient

    def orchestration(self, obj):
        """Construct orchestration client based on object.

        :param obj: Object for which the client is created. It is expected to
                    be None when retrieving an existing client. When creating
                    a client, it contains the user and project to be used.
        """
        if self._orchestrationclient is not None:
            return self._orchestrationclient
        params = self._build_conn_params(obj.user, obj.project)
        oc = driver_base.SenlinDriver().orchestration(params)
        self._orchestrationclient = oc
        return oc

    def workflow(self, obj):
        if self._workflowclient is not None:
            return self._workflowclient
        params = self._build_conn_params(obj.user, obj.project)
        self._workflowclient = driver_base.SenlinDriver().workflow(params)
        return self._workflowclient

    def block_storage(self, obj):
        """Construct cinder client based on object.

        :param obj: Object for which the client is created. It is expected to
                    be None when retrieving an existing client. When creating
                    a client, it contains the user and project to be used.
        """
        if self._block_storageclient is not None:
            return self._block_storageclient
        params = self._build_conn_params(obj.user, obj.project)
        self._block_storageclient = driver_base.SenlinDriver().block_storage(
            params)
        return self._block_storageclient

    def do_create(self, obj):
        """For subclass to override."""
        raise NotImplementedError

    def do_cluster_create(self, obj):
        """For subclass to override."""
        raise NotImplementedError

    def do_delete(self, obj, **params):
        """For subclass to override."""
        raise NotImplementedError

    def do_cluster_delete(self, obj):
        """For subclass to override."""
        raise NotImplementedError

    def do_update(self, obj, new_profile, **params):
        """For subclass to override."""
        LOG.warning("Update operation not supported.")
        return True

    def do_check(self, obj):
        """For subclass to override."""
        LOG.warning("Check operation not supported.")
        return True

    def do_get_details(self, obj):
        """For subclass to override."""
        LOG.warning("Get_details operation not supported.")
        return {}

    def do_adopt(self, obj, overrides=None, snapshot=False):
        """For subclass to override."""
        LOG.warning("Adopt operation not supported.")
        return {}

    def do_join(self, obj, cluster_id):
        """For subclass to override to perform extra operations."""
        LOG.warning("Join operation not specialized.")
        return True

    def do_leave(self, obj):
        """For subclass to override to perform extra operations."""
        LOG.warning("Leave operation not specialized.")
        return True

    def do_recover(self, obj, **options):
        """Default recover operation.

        This is provided as a fallback if a specific profile type does not
        override this method.

        :param obj: The node object to operate on.
        :param options: Keyword arguments for the recover operation.
        """
        operation = options.pop('operation', None)

        # The operation is a list of action names with optional parameters
        if operation and not isinstance(operation, six.string_types):
            operation = operation[0]

        if operation and operation['name'] != consts.RECOVER_RECREATE:
            LOG.error("Recover operation not supported: %s", operation)
            return False

        extra_params = options.get('params', {})
        fence_compute = extra_params.get('fence_compute', False)
        try:
            self.do_delete(obj, force=fence_compute)
        except exc.EResourceDeletion as ex:
            raise exc.EResourceOperation(op='recovering', type='node',
                                         id=obj.id, message=six.text_type(ex))
        res = None
        try:
            res = self.do_create(obj)
        except exc.EResourceCreation as ex:
            raise exc.EResourceOperation(op='recovering', type='node',
                                         id=obj.id, message=six.text_type(ex))
        return res

    def do_validate(self, obj):
        """For subclass to override."""
        LOG.warning("Validate operation not supported.")
        return True

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
            'created_at': utils.isotime(self.created_at),
            'updated_at': utils.isotime(self.updated_at),
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
        LOG.error("The following properties are not updatable: %s.", msg)
        return False
