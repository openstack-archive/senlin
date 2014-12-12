#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

import collections
import functools
import json
import os

import eventlet
from oslo.config import cfg
from oslo import messaging
from oslo.serialization import jsonutils
from oslo.utils import timeutils
from osprofiler import profiler
import requests
import six
import warnings
import webob

from senlin.common import context
from senlin.common import exception
from senlin.common.i18n import _
from senlin.common.i18n import _LE
from senlin.common.i18n import _LI
from senlin.common.i18n import _LW
from senlin.common import identifier
from senlin.common import messaging as rpc_messaging
# Just for test, need be repalced with real db api implementation
from senlin.db import api_sim as db_api
from senlin.openstack.common import log as logging
from senlin.openstack.common import service
from senlin.openstack.common import threadgroup
from senlin.openstack.common import uuidutils
from senlin.rpc import api as rpc_api

LOG = logging.getLogger(__name__)


def request_context(func):
    @functools.wraps(func)
    def wrapped(self, ctx, *args, **kwargs):
        if ctx is not None and not isinstance(ctx, context.RequestContext):
            ctx = context.RequestContext.from_dict(ctx.to_dict())
        try:
            return func(self, ctx, *args, **kwargs)
        except exception.HeatException:
            raise messaging.rpc.dispatcher.ExpectedException()
    return wrapped


class ThreadGroupManager(object):

    def __init__(self):
        super(ThreadGroupManager, self).__init__()
        self.groups = {}
        self.events = collections.defaultdict(list)

        # Create dummy service task, because when there is nothing queued
        # on self.tg the process exits
        self.add_timer(cfg.CONF.periodic_interval, self._service_task)

    def _service_task(self):
        """
        This is a dummy task which gets queued on the service.Service
        threadgroup.  Without this service.Service sees nothing running
        i.e has nothing to wait() on, so the process exits..
        This could also be used to trigger periodic non-cluster-specific
        housekeeping tasks
        """
        pass

    def _serialize_profile_info(self):
        prof = profiler.get()
        trace_info = None
        if prof:
            trace_info = {
                "hmac_key": prof.hmac_key,
                "base_id": prof.get_base_id(),
                "parent_id": prof.get_id()
            }
        return trace_info

    def _start_with_trace(self, trace, func, *args, **kwargs):
        if trace:
            profiler.init(**trace)
        return func(*args, **kwargs)

    def start(self, cluster_id, func, *args, **kwargs):
        """
        Run the given method in a sub-thread.
        """
        if cluster_id not in self.groups:
            self.groups[cluster_id] = threadgroup.ThreadGroup()
        return self.groups[cluster_id].add_thread(self._start_with_trace,
                                                self._serialize_profile_info(),
                                                func, *args, **kwargs)

    def start_with_lock(self, cnxt, cluster, engine_id, func, *args, **kwargs):
        """
        Try to acquire a cluster lock and, if successful, run the given
        method in a sub-thread.  Release the lock when the thread
        finishes.

        :param cnxt: RPC context
        :param cluster: Cluster to be operated on
        :type cluster: heat.engine.parser.Stack
        :param engine_id: The UUID of the engine/worker acquiring the lock
        :param func: Callable to be invoked in sub-thread
        :type func: function or instancemethod
        :param args: Args to be passed to func
        :param kwargs: Keyword-args to be passed to func.
        """
        lock = cluster_lock.ClusterLock(cnxt, cluster, engine_id)
        with lock.thread_lock(cluster.id):
            th = self.start_with_acquired_lock(cluster, lock,
                                               func, *args, **kwargs)
            return th

    def start_with_acquired_lock(self, cluster, lock, func, *args, **kwargs):
        """
        Run the given method in a sub-thread and release the provided lock
        when the thread finishes.

        :param cluster: Cluster to be operated on
        :type cluster: heat.engine.parser.Stack
        :param lock: The acquired cluster lock
        :type lock: heat.engine.cluster_lock.ClusterLock
        :param func: Callable to be invoked in sub-thread
        :type func: function or instancemethod
        :param args: Args to be passed to func
        :param kwargs: Keyword-args to be passed to func

        """
        def release(gt, *args):
            """
            Callback function that will be passed to GreenThread.link().
            """
            lock.release(*args)

        th = self.start(cluster.id, func, *args, **kwargs)
        th.link(release, cluster.id)
        return th

    def add_timer(self, cluster_id, func, *args, **kwargs):
        """
        Define a periodic task, to be run in a separate thread, in the cluster
        threadgroups.  Periodicity is cfg.CONF.periodic_interval
        """
        if cluster_id not in self.groups:
            self.groups[cluster_id] = threadgroup.ThreadGroup()
        self.groups[cluster_id].add_timer(cfg.CONF.periodic_interval,
                                        func, *args, **kwargs)

    def add_event(self, cluster_id, event):
        self.events[cluster_id].append(event)

    def remove_event(self, gt, cluster_id, event):
        for e in self.events.pop(cluster_id, []):
            if e is not event:
                self.add_event(cluster_id, e)

    def stop_timers(self, cluster_id):
        if cluster_id in self.groups:
            self.groups[cluster_id].stop_timers()

    def stop(self, cluster_id, graceful=False):
        '''Stop any active threads on a cluster.'''
        if cluster_id in self.groups:
            self.events.pop(cluster_id, None)
            threadgroup = self.groups.pop(cluster_id)
            threads = threadgroup.threads[:]

            threadgroup.stop(graceful)
            threadgroup.wait()

            # Wait for link()ed functions (i.e. lock release)
            links_done = dict((th, False) for th in threads)

            def mark_done(gt, th):
                links_done[th] = True

            for th in threads:
                th.link(mark_done, th)
            while not all(links_done.values()):
                eventlet.sleep()

    def send(self, cluster_id, message):
        for event in self.events.pop(cluster_id, []):
            event.send(message)


@profiler.trace_cls("rpc")
class EngineService(service.Service):
    """
    Manages the running instances from creation to destruction.
    All the methods in here are called from the RPC backend.  This is
    all done dynamically so if a call is made via RPC that does not
    have a corresponding method here, an exception will be thrown when
    it attempts to call into this class.  Arguments to these methods
    are also dynamically added and will be named as keyword arguments
    by the RPC caller.
    """

    RPC_API_VERSION = '1.2'

    def __init__(self, host, topic, manager=None):
        super(EngineService, self).__init__()
        resources.initialise()
        self.host = host
        self.topic = topic

        # The following are initialized here, but assigned in start() which
        # happens after the fork when spawning multiple worker processes
        self.engine_id = None
        self.thread_group_mgr = None
        self.target = None

        if cfg.CONF.instance_user:
            warnings.warn('The "instance_user" option in heat.conf is '
                          'deprecated and will be removed in the Juno '
                          'release.', DeprecationWarning)

        if cfg.CONF.trusts_delegated_roles:
            warnings.warn('The default value of "trusts_delegated_roles" '
                          'option in heat.conf is changed to [] in Kilo '
                          'and heat will delegate all roles of trustor. '
                          'Please keep the same if you do not want to '
                          'delegate subset roles when upgrading.',
                          Warning)

    def start(self):
        self.engine_id = cluster_lock.ClusterLock.generate_engine_id()
        self.thread_group_mgr = ThreadGroupManager()
        LOG.debug("Starting engine worker with engine_id %s" % self.engine_id)
        target = messaging.Target(
            version=self.RPC_API_VERSION, server=self.host,
            topic=self.topic)
        self.target = target
        server = rpc_messaging.get_rpc_server(target, self)
        server.start()

        super(EngineService, self).start()

    def stop(self):
        # Stop rpc connection at first for preventing new requests
        LOG.info(_LI("Attempting to stop engine service..."))
        try:
            self.conn.close()
        except Exception:
            pass

        # Wait for all active threads to be finished
        for cluster_id in self.thread_group_mgr.groups.keys():
            # Ignore dummy service task
            if cluster_id == cfg.CONF.periodic_interval:
                continue
            LOG.info(_LI("Waiting cluster %s processing to be finished"),
                     cluster_id)
            # Stop threads gracefully
            self.thread_group_mgr.stop(cluster_id, True)
            LOG.info(_LI("cluster %s processing was finished"), cluster_id)

        # Terminate the engine process
        LOG.info(_LI("All threads were gone, terminating engine"))
        super(EngineService, self).stop()

    @request_context
    def identify_cluster(self, cnxt, cluster_name):
        """
        The identify_cluster method returns the full cluster identifier for a
        single, live cluster given the cluster name.

        :param cnxt: RPC context.
        :param cluster_name: Name or UUID of the cluster to look up.
        """
        # Just for test
        if uuidutils.is_uuid_like(cluster_name):
            c = db_api.cluster_get(cnxt, cluster_name, show_deleted=True)
            # may be the name is in uuid format, so if get by id returns None,
            # we should get the info by name again
            if not c:
                c = db_api.cluster_get_by_name(cnxt, cluster_name)
        else:
            c = db_api.cluster_get_by_name(cnxt, cluster_name)
        if c:
            return dict(c['id'])
        else:
            raise exception.ClusterNotFound(cluster_name=cluster_name)

    def _get_cluster(self, cnxt, cluster_identity, show_deleted=False):
        identity = identifier.HeatIdentifier(**cluster_identity)

        s = db_api.cluster_get(cnxt, identity.cluster_id,
                             show_deleted=show_deleted,
                             eager_load=True)

        if s is None:
            raise exception.ClusterNotFound(cluster_name=identity.cluster_name)

        if cnxt.tenant_id not in (identity.tenant, s.cluster_user_project_id):
            # The DB API should not allow this, but sanity-check anyway..
            raise exception.InvalidTenant(target=identity.tenant,
                                          actual=cnxt.tenant_id)

        if identity.path or s.name != identity.cluster_name:
            raise exception.ClusterNotFound(cluster_name=identity.cluster_name)

        return s

    @request_context
    def show_cluster(self, cnxt, cluster_identity):
        """
        Return detailed information about one or all clusters.

        :param cnxt: RPC context.
        :param cluster_identity: Name of the cluster you want to show, or None
            to show all
        """
        if cluster_identity is not None:
            db_cluster = self._get_cluster(cnxt, cluster_identity, show_deleted=True)
            clusters = [parser.Cluster.load(cnxt, cluster=db_cluster)]
        else:
            clusters = parser.Cluster.load_all(cnxt)

        return [api.format_cluster(cluster) for cluster in clusters]

    @request_context
    def list_clusters(self, cnxt, limit=None, marker=None, sort_keys=None,
                    sort_dir=None, filters=None, tenant_safe=True,
                    show_deleted=False, show_nested=False):
        """
        The list_clusters method returns attributes of all clusters.  It supports
        pagination (``limit`` and ``marker``), sorting (``sort_keys`` and
        ``sort_dir``) and filtering (``filters``) of the results.

        :param cnxt: RPC context
        :param limit: the number of clusters to list (integer or string)
        :param marker: the ID of the last item in the previous page
        :param sort_keys: an array of fields used to sort the list
        :param sort_dir: the direction of the sort ('asc' or 'desc')
        :param filters: a dict with attribute:value to filter the list
        :param tenant_safe: if true, scope the request by the current tenant
        :param show_deleted: if true, show soft-deleted clusters
        :param show_nested: if true, show nested clusters
        :returns: a list of formatted clusters
        """
        clusters = parser.Cluster.load_all(cnxt, limit, marker, sort_keys,
                                       sort_dir, filters, tenant_safe,
                                       show_deleted, resolve_data=False,
                                       show_nested=show_nested)
        return [api.format_cluster(cluster) for cluster in clusters]

    def _validate_deferred_auth_context(self, cnxt, cluster):
        if cfg.CONF.deferred_auth_method != 'password':
            return

        if not cluster.requires_deferred_auth():
            return

        if cnxt.username is None:
            raise exception.MissingCredentialError(required='X-Auth-User')
        if cnxt.password is None:
            raise exception.MissingCredentialError(required='X-Auth-Key')

    def _validate_new_cluster(self, cnxt, cluster_name, parsed_template):
        try:
            parsed_template.validate()
        except Exception as ex:
            raise exception.ClusterValidationFailed(message=six.text_type(ex))

        if db_api.cluster_get_by_name(cnxt, cluster_name):
            raise exception.ClusterExists(cluster_name=cluster_name)

        tenant_limit = cfg.CONF.max_clusters_per_tenant
        if db_api.cluster_count_all(cnxt) >= tenant_limit:
            message = _("You have reached the maximum clusters per tenant, %d."
                        " Please delete some clusters.") % tenant_limit
            raise exception.RequestLimitExceeded(message=message)

        num_resources = len(parsed_template[parsed_template.RESOURCES])
        if num_resources > cfg.CONF.max_resources_per_cluster:
            message = exception.ClusterResourceLimitExceeded.msg_fmt
            raise exception.RequestLimitExceeded(message=message)

    def _parse_template_and_validate_cluster(self, cnxt, cluster_name, template,
                                           params, files, args, owner_id=None,
                                           nested_depth=0, user_creds_id=None,
                                           cluster_user_project_id=None):
        tmpl = templatem.Template(template, files=files)
        self._validate_new_cluster(cnxt, cluster_name, tmpl)

        # If it is cluster-adopt, use parameters from adopt_cluster_data
        common_params = api.extract_args(args)

        if rpc_api.PARAM_ADOPT_CLUSTER_DATA in common_params:
            params[rpc_api.CLUSTER_PARAMETERS] = common_params[
                rpc_api.PARAM_ADOPT_CLUSTER_DATA]['environment'][
                    rpc_api.CLUSTER_PARAMETERS]

        env = environment.Environment(params)
        cluster = parser.Cluster(cnxt, cluster_name, tmpl, env,
                             owner_id=owner_id,
                             nested_depth=nested_depth,
                             user_creds_id=user_creds_id,
                             cluster_user_project_id=cluster_user_project_id,
                             **common_params)

        self._validate_deferred_auth_context(cnxt, cluster)
        cluster.validate()
        return cluster

    @request_context
    def create_cluster(self, cnxt, cluster_name, template, params, files, args,
                     owner_id=None, nested_depth=0, user_creds_id=None,
                     cluster_user_project_id=None):
        """
        The create_cluster method creates a new cluster using the template
        provided.
        Note that at this stage the template has already been fetched from the
        heat-api process if using a template-url.

        :param cnxt: RPC context.
        :param cluster_name: Name of the cluster you want to create.
        :param template: Template of cluster you want to create.
        :param params: cluster Input Params
        :param files: Files referenced from the template
        :param args: Request parameters/args passed from API
        :param owner_id: parent cluster ID for nested clusters, only expected when
                         called from another heat-engine (not a user option)
        :param nested_depth: the nested depth for nested clusters, only expected
                         when called from another heat-engine
        :param user_creds_id: the parent user_creds record for nested clusters
        :param cluster_user_project_id: the parent cluster_user_project_id for
                         nested clusters
        """
        LOG.info(_LI('Creating cluster %s'), cluster_name)

        def _cluster_create(cluster):

            if not cluster.cluster_user_project_id:
                cluster.create_cluster_user_project_id()

            # Create/Adopt a cluster, and create the periodic task if successful
            if cluster.adopt_cluster_data:
                if not cfg.CONF.enable_cluster_adopt:
                    raise exception.NotSupported(feature='Cluster Adopt')

                cluster.adopt()
            else:
                cluster.create()

            if (cluster.action in (cluster.CREATE, cluster.ADOPT)
                    and cluster.status == cluster.COMPLETE):
            else:
                LOG.info(_LI("Cluster create failed, status %s"), cluster.status)

        cluster = self._parse_template_and_validate_cluster(cnxt,
                                                        cluster_name,
                                                        template,
                                                        params,
                                                        files,
                                                        args,
                                                        owner_id,
                                                        nested_depth,
                                                        user_creds_id,
                                                        cluster_user_project_id)

        cluster.store()

        self.thread_group_mgr.start_with_lock(cnxt, cluster, self.engine_id,
                                              _cluster_create, cluster)

        return dict(cluster.identifier())

    @request_context
    def update_cluster(self, cnxt, cluster_identity, template, params,
                     files, args):
        """
        The update_cluster method updates an existing cluster based on the
        provided template and parameters.
        Note that at this stage the template has already been fetched from the
        heat-api process if using a template-url.

        :param cnxt: RPC context.
        :param cluster_identity: Name of the cluster you want to create.
        :param template: Template of cluster you want to create.
        :param params: cluster Input Params
        :param files: Files referenced from the template
        :param args: Request parameters/args passed from API
        """
        # Get the database representation of the existing cluster
        db_cluster = self._get_cluster(cnxt, cluster_identity)
        LOG.info(_LI('Updating cluster %s'), db_cluster.name)

        current_cluster = parser.Cluster.load(cnxt, cluster=db_cluster)

        if current_cluster.action == current_cluster.SUSPEND:
            msg = _('Updating a cluster when it is suspended')
            raise exception.NotSupported(feature=msg)

        if current_cluster.action == current_cluster.DELETE:
            msg = _('Updating a cluster when it is deleting')
            raise exception.NotSupported(feature=msg)

        # Now parse the template and any parameters for the updated
        # cluster definition.
        tmpl = templatem.Template(template, files=files)
        if len(tmpl[tmpl.RESOURCES]) > cfg.CONF.max_resources_per_cluster:
            raise exception.RequestLimitExceeded(
                message=exception.ClusterResourceLimitExceeded.msg_fmt)
        cluster_name = current_cluster.name
        common_params = api.extract_args(args)
        common_params.setdefault(rpc_api.PARAM_TIMEOUT,
                                 current_cluster.timeout_mins)
        common_params.setdefault(rpc_api.PARAM_DISABLE_ROLLBACK,
                                 current_cluster.disable_rollback)
        env = environment.Environment(params)
        if args.get(rpc_api.PARAM_EXISTING, None):
            env.patch_previous_parameters(
                current_cluster.env,
                args.get(rpc_api.PARAM_CLEAR_PARAMETERS, []))
        updated_cluster = parser.Cluster(cnxt, cluster_name, tmpl,
                                     env, **common_params)
        updated_cluster.parameters.set_cluster_id(current_cluster.identifier())

        self._validate_deferred_auth_context(cnxt, updated_cluster)
        updated_cluster.validate()

        event = eventlet.event.Event()
        th = self.thread_group_mgr.start_with_lock(cnxt, current_cluster,
                                                   self.engine_id,
                                                   current_cluster.update,
                                                   updated_cluster,
                                                   event=event)
        th.link(self.thread_group_mgr.remove_event, current_cluster.id, event)
        self.thread_group_mgr.add_event(current_cluster.id, event)
        return dict(current_cluster.identifier())

    @request_context
    def validate_template(self, cnxt, template, params=None):
        """
        The validate_template method uses the cluster parser to check
        the validity of a template.

        :param cnxt: RPC context.
        :param template: Template of cluster you want to create.
        :param params: cluster Input Params
        """
        LOG.info(_LI('validate_template'))
        if template is None:
            msg = _("No Template provided.")
            return webob.exc.HTTPBadRequest(explanation=msg)

        tmpl = templatem.Template(template)

        # validate overall template
        try:
            tmpl.validate()
        except Exception as ex:
            return {'Error': six.text_type(ex)}

        # validate resource classes
        tmpl_resources = tmpl[tmpl.RESOURCES]

        env = environment.Environment(params)

        for res in tmpl_resources.values():
            ResourceClass = env.get_class(res['Type'])
            if ResourceClass == resources.template_resource.TemplateResource:
                # we can't validate a TemplateResource unless we instantiate
                # it as we need to download the template and convert the
                # parameters into properties_schema.
                continue

            props = properties.Properties(ResourceClass.properties_schema,
                                          res.get('Properties', {}),
                                          context=cnxt)
            deletion_policy = res.get('DeletionPolicy', 'Delete')
            try:
                ResourceClass.validate_deletion_policy(deletion_policy)
                props.validate(with_value=False)
            except Exception as ex:
                return {'Error': six.text_type(ex)}

        # validate parameters
        tmpl_params = tmpl.parameters(None, user_params=env.params)
        tmpl_params.validate(validate_value=False, context=cnxt)
        is_real_param = lambda p: p.name not in tmpl_params.PSEUDO_PARAMETERS
        params = tmpl_params.map(api.format_validate_parameter, is_real_param)
        param_groups = parameter_groups.ParameterGroups(tmpl)

        result = {
            'Description': tmpl.get('Description', ''),
            'Parameters': params,
        }

        if param_groups.parameter_groups:
            result['ParameterGroups'] = param_groups.parameter_groups

        return result

    @request_context
    def authenticated_to_backend(self, cnxt):
        """
        Verify that the credentials in the RPC context are valid for the
        current cloud backend.
        """
        return clients.Clients(cnxt).authenticated()

    @request_context
    def delete_cluster(self, cnxt, cluster_identity):
        """
        The delete_cluster method deletes a given cluster.

        :param cnxt: RPC context.
        :param cluster_identity: Name of the cluster you want to delete.
        """

        st = self._get_cluster(cnxt, cluster_identity)
        LOG.info(_LI('Deleting cluster %s'), st.name)
        cluster = parser.Cluster.load(cnxt, cluster=st)

        lock = cluster_lock.ClusterLock(cnxt, cluster, self.engine_id)
        with lock.try_thread_lock(cluster.id) as acquire_result:

            # Successfully acquired lock
            if acquire_result is None:
                self.thread_group_mgr.stop_timers(cluster.id)
                self.thread_group_mgr.start_with_acquired_lock(cluster, lock,
                                                               cluster.delete)
                return

        # Current engine has the lock
        if acquire_result == self.engine_id:
            # give threads which are almost complete an opportunity to
            # finish naturally before force stopping them
            eventlet.sleep(0.2)
            self.thread_group_mgr.stop(cluster.id)

        # Another active engine has the lock
        # Doesn't suppot yet!
        # TODO: add multi-engine support

        # There may be additional resources that we don't know about
        # if an update was in-progress when the cluster was stopped, so
        # reload the cluster from the database.
        st = self._get_cluster(cnxt, cluster_identity)
        cluster = parser.Cluster.load(cnxt, cluster=st)

        self.thread_group_mgr.start_with_lock(cnxt, cluster, self.engine_id,
                                              cluster.delete)
        return None

    @request_context
    def cluster_suspend(self, cnxt, cluster_identity):
        '''
        Handle request to perform suspend action on a cluster
        '''
        def _cluster_suspend(cluster):
            LOG.debug("suspending cluster %s" % cluster.name)
            cluster.suspend()

        s = self._get_cluster(cnxt, cluster_identity)

        cluster = parser.Cluster.load(cnxt, cluster=s)
        self.thread_group_mgr.start_with_lock(cnxt, cluster, self.engine_id,
                                              _cluster_suspend, cluster)

    @request_context
    def cluster_resume(self, cnxt, cluster_identity):
        '''
        Handle request to perform a resume action on a cluster
        '''
        def _cluster_resume(cluster):
            LOG.debug("resuming cluster %s" % cluster.name)
            cluster.resume()

        s = self._get_cluster(cnxt, cluster_identity)

        cluster = parser.Cluster.load(cnxt, cluster=s)
        self.thread_group_mgr.start_with_lock(cnxt, cluster, self.engine_id,
                                              _cluster_resume, cluster)
