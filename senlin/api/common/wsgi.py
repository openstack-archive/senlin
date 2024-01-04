# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

"""
Utility methods for working with WSGI servers
"""

import abc
import errno
import os
import signal
import sys
import time

import eventlet
from eventlet.green import socket
from eventlet.green import ssl
import eventlet.wsgi
import functools
from oslo_config import cfg
import oslo_i18n
from oslo_log import log as logging
from oslo_utils import importutils
from paste import deploy
from routes import middleware
import webob
from webob import dec as webob_dec
from webob import exc

from senlin.api.common import serializers
from senlin.api.common import version_request
from senlin.api.common import versioned_method
from senlin.common import exception
from senlin.common.i18n import _
from senlin.rpc import client as rpc_client


LOG = logging.getLogger(__name__)
URL_LENGTH_LIMIT = 50000
DEFAULT_API_VERSION = '1.0'
API_VERSION_KEY = 'OpenStack-API-Version'
VER_METHOD_ATTR = 'versioned_methods'


def get_bind_addr(conf, default_port=None):
    return conf.bind_host, conf.bind_port or default_port


def get_socket(conf, default_port):
    """Bind socket to bind ip:port in conf

    :param conf: a cfg.ConfigOpts object
    :param default_port: port to bind to if none is specified in conf

    :returns : a socket object as returned from socket.listen or
               ssl.wrap_socket if conf specifies cert_file
    """

    bind_addr = get_bind_addr(conf, default_port)

    # TODO(jaypipes): eventlet's greened socket module does not actually
    # support IPv6 in getaddrinfo(). We need to get around this in the
    # future or monitor upstream for a fix
    address_family = [addr[0] for addr in socket.getaddrinfo(bind_addr[0],
                      bind_addr[1], socket.AF_UNSPEC, socket.SOCK_STREAM)
                      if addr[0] in (socket.AF_INET, socket.AF_INET6)][0]

    cert_file = conf.cert_file
    key_file = conf.key_file
    use_ssl = cert_file or key_file
    if use_ssl and (not cert_file or not key_file):
        raise RuntimeError(_("When running server in SSL mode, you must "
                             "specify both a cert_file and key_file "
                             "option value in your configuration file"))

    sock = None
    retry_until = time.time() + 30
    while not sock and time.time() < retry_until:
        try:
            sock = eventlet.listen(bind_addr, backlog=conf.backlog,
                                   family=address_family)
        except socket.error as err:
            if err.args[0] != errno.EADDRINUSE:
                raise
            eventlet.sleep(0.1)

    if not sock:
        raise RuntimeError(_("Could not bind to %(bind_addr)s after trying"
                             " 30 seconds") % {'bind_addr': bind_addr})
    return sock


class Server(object):
    """Server class to manage multiple WSGI sockets and applications."""

    def __init__(self, name, conf, threads=1000):
        os.umask(0o27)  # ensure files are created with the correct privileges
        self._logger = logging.getLogger("eventlet.wsgi.server")
        self.name = name
        self.threads = threads
        self.children = set()
        self.stale_children = set()
        self.running = True
        self.pgid = os.getpid()
        self.conf = conf
        try:
            os.setpgid(self.pgid, self.pgid)
        except OSError:
            self.pgid = 0

    def kill_children(self, *args):
        """Kill the entire process group."""

        LOG.error('SIGTERM received')
        signal.signal(signal.SIGTERM, signal.SIG_IGN)
        signal.signal(signal.SIGINT, signal.SIG_IGN)
        self.running = False
        os.killpg(0, signal.SIGTERM)

    def hup(self, *args):
        """Reload configuration files with zero down time."""

        LOG.error('SIGHUP received')
        signal.signal(signal.SIGHUP, signal.SIG_IGN)
        raise exception.SIGHUPInterrupt

    def start(self, application, default_port):
        """Run a WSGI server with the given application.

        :param application: The application to run in the WSGI server
        :param default_port: Port to bind to if none is specified in conf
        """

        eventlet.wsgi.MAX_HEADER_LINE = self.conf.max_header_line
        self.application = application
        self.default_port = default_port
        self.configure_socket()
        self.start_wsgi()

    def start_wsgi(self):
        if self.conf.workers == 0:
            # Useful for profiling, test, debug etc.
            self.pool = eventlet.GreenPool(size=self.threads)
            self.pool.spawn_n(self._single_run, self.application, self.sock)
            return

        LOG.info("Starting %d workers", self.conf.workers)
        signal.signal(signal.SIGTERM, self.kill_children)
        signal.signal(signal.SIGINT, self.kill_children)
        signal.signal(signal.SIGHUP, self.hup)
        while len(self.children) < self.conf.workers:
            self.run_child()

    def wait_on_children(self):
        """Wait on children exit."""

        while self.running:
            try:
                pid, status = os.wait()
                if os.WIFEXITED(status) or os.WIFSIGNALED(status):
                    self._remove_children(pid)
                    self._verify_and_respawn_children(pid, status)
            except OSError as err:
                if err.errno not in (errno.EINTR, errno.ECHILD):
                    raise
            except KeyboardInterrupt:
                LOG.info('Caught keyboard interrupt. Exiting.')
                os.killpg(0, signal.SIGTERM)
                break
            except exception.SIGHUPInterrupt:
                self.reload()
                continue

        eventlet.greenio.shutdown_safe(self.sock)
        self.sock.close()
        LOG.debug('Exited')

    def configure_socket(self, old_conf=None, has_changed=None):
        """Ensure a socket exists and is appropriately configured.

        This function is called on start up, and can also be
        called in the event of a configuration reload.

        When called for the first time a new socket is created.
        If reloading and either bind_host or bind_port have been
        changed, the existing socket must be closed and a new
        socket opened (laws of physics).

        In all other cases (bind_host/bind_port have not been changed)
        the existing socket is reused.

        :param old_conf: Cached old configuration settings (if any)
        :param has_changed: callable to determine if a parameter has changed
        """

        new_sock = (old_conf is None or (
                    has_changed('bind_host') or
                    has_changed('bind_port')))
        # check https
        use_ssl = not (not self.conf.cert_file or not self.conf.key_file)
        # Were we using https before?
        old_use_ssl = (old_conf is not None and not (
                       not old_conf.get('key_file') or
                       not old_conf.get('cert_file')))
        # Do we now need to perform an SSL wrap on the socket?
        wrap_sock = use_ssl is True and (old_use_ssl is False or new_sock)
        # Do we now need to perform an SSL unwrap on the socket?
        unwrap_sock = use_ssl is False and old_use_ssl is True

        if new_sock:
            self._sock = None
            if old_conf is not None:
                self.sock.close()

            _sock = get_socket(self.conf, self.default_port)
            _sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            # sockets can hang around forever without keepalive
            _sock.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)
            self._sock = _sock

        if wrap_sock:
            self.sock = ssl.wrap_socket(self._sock,
                                        certfile=self.conf.cert_file,
                                        keyfile=self.conf.key_file)

        if unwrap_sock:
            self.sock = self._sock

        if new_sock and not use_ssl:
            self.sock = self._sock

        # Pick up newly deployed certs
        if old_conf is not None and use_ssl is True and old_use_ssl is True:
            if has_changed('cert_file'):
                self.sock.certfile = self.conf.cert_file
            if has_changed('key_file'):
                self.sock.keyfile = self.conf.key_file

        if new_sock or (old_conf is not None and has_changed('tcp_keepidle')):
            # This option isn't available in the OS X version of eventlet
            if hasattr(socket, 'TCP_KEEPIDLE'):
                self.sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_KEEPIDLE,
                                     self.conf.tcp_keepidle)

        if old_conf is not None and has_changed('backlog'):
            self.sock.listen(self.conf.backlog)

    def _remove_children(self, pid):

        if pid in self.children:
            self.children.remove(pid)
            LOG.info('Removed dead child %s', pid)
        elif pid in self.stale_children:
            self.stale_children.remove(pid)
            LOG.info('Removed stale child %s', pid)
        else:
            LOG.warning('Unrecognized child %s', pid)

    def _verify_and_respawn_children(self, pid, status):
        if len(self.stale_children) == 0:
            LOG.debug('No stale children')

        if os.WIFEXITED(status) and os.WEXITSTATUS(status) != 0:
            LOG.error('Not respawning child %d, cannot '
                      'recover from termination', pid)
            if not self.children and not self.stale_children:
                LOG.info('All workers have terminated. Exiting')
                self.running = False
        else:
            if len(self.children) < self.conf.workers:
                self.run_child()

    def stash_conf_values(self):
        """Make a copy of some of the current global CONF's settings.

        Allow determining if any of these values have changed
        when the config is reloaded.
        """
        conf = {}
        conf['bind_host'] = self.conf.bind_host
        conf['bind_port'] = self.conf.bind_port
        conf['backlog'] = self.conf.backlog
        conf['key_file'] = self.conf.key_file
        conf['cert_file'] = self.conf.cert_file
        return conf

    def reload(self):
        """Reload and re-apply configuration settings.

        Existing child processes are sent a SIGHUP signal and will exit after
        completing existing requests. New child processes, which will have the
        updated configuration, are spawned. This allows preventing
        interruption to the service.
        """
        def _has_changed(old, new, param):
            old = old.get(param)
            new = getattr(new, param)
            return (new != old)

        old_conf = self.stash_conf_values()
        has_changed = functools.partial(_has_changed, old_conf, self.conf)
        cfg.CONF.reload_config_files()
        os.killpg(self.pgid, signal.SIGHUP)
        self.stale_children = self.children
        self.children = set()

        # Ensure any logging config changes are picked up
        logging.setup(cfg.CONF, self.name)

        self.configure_socket(old_conf, has_changed)
        self.start_wsgi()

    def wait(self):
        """Wait until all servers have completed running."""
        try:
            if self.children:
                self.wait_on_children()
            else:
                self.pool.waitall()
        except KeyboardInterrupt:
            pass

    def run_child(self):
        def child_hup(*args):
            """Shut down child processes, existing requests are handled."""
            signal.signal(signal.SIGHUP, signal.SIG_IGN)
            eventlet.wsgi.is_accepting = False
            self.sock.close()

        pid = os.fork()
        if pid == 0:
            signal.signal(signal.SIGHUP, child_hup)
            signal.signal(signal.SIGTERM, signal.SIG_DFL)
            # ignore the interrupt signal to avoid a race whereby
            # a child worker receives the signal before the parent
            # and is respawned unnecessarily as a result
            signal.signal(signal.SIGINT, signal.SIG_IGN)
            # The child has no need to stash the unwrapped
            # socket, and the reference prevents a clean
            # exit on sighup
            self._sock = None
            self.run_server()
            LOG.info('Child %d exiting normally', os.getpid())
            # self.pool.waitall() is now called in wsgi's server so
            # it's safe to exit here
            sys.exit(0)
        else:
            LOG.info('Started child %s', pid)
            self.children.add(pid)

    def run_server(self):
        """Run a WSGI server."""

        eventlet.wsgi.HttpProtocol.default_request_version = "HTTP/1.0"
        eventlet.hubs.use_hub('poll')
        eventlet.patcher.monkey_patch(all=False, socket=True)
        self.pool = eventlet.GreenPool(size=self.threads)
        socket_timeout = cfg.CONF.senlin_api.client_socket_timeout or None

        try:
            eventlet.wsgi.server(
                self.sock, self.application,
                custom_pool=self.pool,
                url_length_limit=URL_LENGTH_LIMIT,
                log=self._logger,
                debug=cfg.CONF.debug,
                keepalive=cfg.CONF.senlin_api.wsgi_keep_alive,
                socket_timeout=socket_timeout)
        except socket.error as err:
            if err.errno != errno.EINVAL:
                raise

        self.pool.waitall()

    def _single_run(self, application, sock):
        """Start a WSGI server in a new green thread."""

        LOG.info("Starting single process server")
        eventlet.wsgi.server(sock, application, custom_pool=self.pool,
                             url_length_limit=URL_LENGTH_LIMIT,
                             log=self._logger, debug=cfg.CONF.debug)


class Middleware(object):
    """Base WSGI middleware wrapper.

    These classes require an application to be initialized that will be called
    next.  By default the middleware will simply call its wrapped app, or you
    can override __call__ to customize its behavior.
    """

    def __init__(self, application):
        self.application = application

    def process_request(self, request):
        """Called on each request.

        If this returns None, the next application down the stack will be
        executed. If it returns a response then that response will be returned
        and execution will stop here.

        :param request: A request object to be processed.
        :returns: None.
        """

        return None

    def process_response(self, response):
        """Customize the response."""
        return response

    @webob_dec.wsgify
    def __call__(self, request):
        response = self.process_request(request)
        if response:
            return response
        response = request.get_response(self.application)
        return self.process_response(response)


class Debug(Middleware):
    """Helper class that can be inserted into any WSGI application chain."""

    @webob_dec.wsgify
    def __call__(self, req):
        print(("*" * 40) + " REQUEST ENVIRON")
        for key, value in req.environ.items():
            print(key, "=", value)
        print('')
        resp = req.get_response(self.application)

        print(("*" * 40) + " RESPONSE HEADERS")
        for (key, value) in resp.headers.items():
            print(key, "=", value)
        print('')

        resp.app_iter = self.print_generator(resp.app_iter)

        return resp

    @staticmethod
    def print_generator(app_iter):
        # Iterator that prints the contents of a wrapper string iterator
        # when iterated.
        print(("*" * 40) + " BODY")
        for part in app_iter:
            sys.stdout.write(part)
            sys.stdout.flush()
            yield part
        print('')


def debug_filter(app, conf, **local_conf):
    return Debug(app)


class Router(object):
    """WSGI middleware that maps incoming requests to WSGI apps."""

    def __init__(self, mapper):
        """Create a router for the given routes.Mapper."""

        self.map = mapper
        self._router = middleware.RoutesMiddleware(self._dispatch, self.map)

    @webob_dec.wsgify
    def __call__(self, req):
        """Route the incoming request to a controller based on self.map."""

        return self._router

    @staticmethod
    @webob_dec.wsgify
    def _dispatch(req):
        """Private dispatch method.

        Called by self._router() after matching the incoming request to
        a route and putting the information into req.environ.
        :returns: Either returns 404 or the routed WSGI app's response.
        """

        match = req.environ['wsgiorg.routing_args'][1]
        if not match:
            return exc.HTTPNotFound()
        app = match['controller']
        return app


class Request(webob.Request):
    """Add some OpenStack API-specific logics to the base webob.Request."""

    def best_match_content_type(self):
        """Determine the requested response content-type."""
        supported = ('application/json',)
        bm = self.accept.best_match(supported)
        return bm or 'application/json'

    def get_content_type(self, allowed_content_types):
        """Determine content type of the request body."""
        if "Content-Type" not in self.headers:
            raise exception.InvalidContentType(content_type=None)

        content_type = self.content_type

        if content_type not in allowed_content_types:
            raise exception.InvalidContentType(content_type=content_type)
        else:
            return content_type

    def best_match_language(self):
        """Determine best available locale from the Accept-Language header.

        :returns: the best language match or None if the 'Accept-Language'
                  header was not available in the request.
        """
        if not self.accept_language:
            return None
        all_languages = oslo_i18n.get_available_languages('senlin')
        return self.accept_language.best_match(all_languages)


class Resource(object):
    """WSGI app that handles (de)serialization and controller dispatch.

    Read routing information supplied by RoutesMiddleware and call
    the requested action method upon its deserializer, controller,
    and serializer. Those three objects may implement any of the basic
    controller action methods (create, update, show, index, delete)
    along with any that may be specified in the api router. A 'default'
    method may also be implemented to be used in place of any
    non-implemented actions. Deserializer methods must accept a request
    argument and return a dictionary. Controller methods must accept a
    request argument. Additionally, they must also accept keyword
    arguments that represent the keys returned by the Deserializer. They
    may raise a webob.exc exception or return a dict, which will be
    serialized by requested content type.
    """

    def __init__(self, controller):
        """Initializer.

        :param controller: object that implement methods created by routes lib
        """
        self.controller = controller
        self.deserializer = serializers.JSONRequestDeserializer()
        self.serializer = serializers.JSONResponseSerializer()

    @webob_dec.wsgify(RequestClass=Request)
    def __call__(self, request):
        """WSGI method that controls (de)serialization and method dispatch."""
        action_args = self.get_action_args(request.environ)
        action = action_args.pop('action', None)
        status_code = action_args.pop('success', None)

        try:
            deserialized_request = self.dispatch(self.deserializer,
                                                 action, request)
            action_args.update(deserialized_request)

            LOG.debug('Calling %(controller)s : %(action)s',
                      {'controller': self.controller, 'action': action})

            action_result = self.dispatch(self.controller, action,
                                          request, **action_args)
        except TypeError as err:
            LOG.error('Exception handling resource: %s', err)
            msg = _('The server could not comply with the request since '
                    'it is either malformed or otherwise incorrect.')
            err = exc.HTTPBadRequest(msg)
            http_exc = translate_exception(err, request.best_match_language())
            # NOTE(luisg): We disguise HTTP exceptions, otherwise they will be
            # treated by wsgi as responses ready to be sent back and they
            # won't make it into the pipeline app that serializes errors
            raise exception.HTTPExceptionDisguise(http_exc)
        except exc.HTTPException as err:
            if not isinstance(err, exc.HTTPError):
                # Some HTTPException are actually not errors, they are
                # responses ready to be sent back to the users, so we don't
                # create error log, but disguise and translate them to meet
                # openstacksdk's need.
                http_exc = translate_exception(err,
                                               request.best_match_language())
                raise http_exc
            if isinstance(err, exc.HTTPServerError):
                LOG.error(
                    "Returning %(code)s to user: %(explanation)s",
                    {'code': err.code, 'explanation': err.explanation})
            http_exc = translate_exception(err, request.best_match_language())
            raise exception.HTTPExceptionDisguise(http_exc)
        except exception.SenlinException as err:
            raise translate_exception(err, request.best_match_language())
        except Exception as err:
            log_exception(err)
            raise translate_exception(err, request.best_match_language())

        try:
            response = webob.Response(request=request)
            # Customize status code if default (200) should be overridden
            if status_code is not None:
                response.status_code = int(status_code)
            # Customize 'location' header if provided
            if action_result and isinstance(action_result, dict):
                location = action_result.pop('location', None)
                if location:
                    response.location = '/v1%s' % location
                if not action_result:
                    action_result = None

            # Attach openstack-api-version header
            if hasattr(response, 'headers'):
                for hdr, val in response.headers.items():
                    # Note(lvdongbing): Ensure header is a python 2 or 3
                    # native string (thus not unicode in python 2 but stay
                    # a string in python 3). Because mod-wsgi checks that
                    # response header values are what's described as
                    # "native strings". This means whatever `str` is in
                    # either python 2 or 3, but never `unicode`.
                    response.headers[hdr] = str(val)
                ver = request.version_request
                if not ver.is_null():
                    ver_res = ' '.join(['clustering', str(ver)])
                    response.headers[API_VERSION_KEY] = ver_res
                    response.headers['Vary'] = API_VERSION_KEY

            self.dispatch(self.serializer, action, response, action_result)
            return response

        # return unserializable result (typically an exception)
        except Exception:
            return action_result

    def dispatch(self, obj, action, *args, **kwargs):
        """Find action-specific method on self and call it."""
        try:
            method = getattr(obj, action)
        except AttributeError:
            method = getattr(obj, 'default')

        try:
            return method(*args, **kwargs)
        except exception.MethodVersionNotFound:
            raise

    def get_action_args(self, request_environment):
        """Parse dictionary created by routes library."""
        try:
            args = request_environment['wsgiorg.routing_args'][1].copy()
        except Exception:
            return {}

        try:
            del args['controller']
        except KeyError:
            pass

        try:
            del args['format']
        except KeyError:
            pass

        return args


class ControllerMetaclass(type):

    def __new__(mcs, name, bases, cls_dict):
        versioned_methods = None
        for base in bases:
            if base.__name__ == "Controller":
                if VER_METHOD_ATTR in base.__dict__:
                    versioned_methods = getattr(base, VER_METHOD_ATTR)
                    delattr(base, VER_METHOD_ATTR)
        if versioned_methods:
            cls_dict[VER_METHOD_ATTR] = versioned_methods

        return super(ControllerMetaclass, mcs).__new__(mcs, name, bases,
                                                       cls_dict)


class Controller(object, metaclass=ControllerMetaclass):
    """Generic WSGI controller for resources."""

    def __init__(self, options):
        self.options = options
        self.rpc_client = rpc_client.get_engine_client()

    def __getattribute__(self, key):

        def version_select(*args, **kwargs):
            """Look for the method and invoke the versioned one.

            This method looks for the method that matches the name provided
            and version constraints then calls it with the supplied arguments.

            :returns: The result of the method called.
            :raises: MethodVersionNotFound if there is no method matching the
                     name and the version constraints.
            """

            # The first argument is always the request object. The version
            # request is attached to the request object.
            req = kwargs['req'] if len(args) == 0 else args[0]
            ver = req.version_request
            func_list = self.versioned_methods[key]
            for func in func_list:
                if ver.matches(func.min_version, func.max_version):
                    # update version_select wrapper so other decorator
                    # attributes are still respected
                    functools.update_wrapper(version_select, func.func)
                    return func.func(self, *args, **kwargs)

            # no version match
            raise exception.MethodVersionNotFound(version=ver)

        try:
            version_meth_dict = object.__getattribute__(self, VER_METHOD_ATTR)
        except AttributeError:
            # no versioning on this class
            return object.__getattribute__(self, key)

        if version_meth_dict:
            if key in object.__getattribute__(self, VER_METHOD_ATTR):
                return version_select

        return object.__getattribute__(self, key)

    # This decorator must appear first (the outermost decorator) on an API
    # method for it to work correctly
    @classmethod
    def api_version(cls, min_ver, max_ver=None):
        """Decorator for versioning api methods.

        Add the decorator to any method that takes a request object as the
        first parameter and belongs to a class which inherits from
        wsgi.Controller.
        :param min_ver: String representing the minimum version.
        :param max_ver: Optional string representing the maximum version.
        """

        def decorator(f):
            obj_min_ver = version_request.APIVersionRequest(min_ver)
            obj_max_ver = version_request.APIVersionRequest(max_ver)

            func_name = f.__name__
            new_func = versioned_method.VersionedMethod(
                func_name, obj_min_ver, obj_max_ver, f)

            func_dict = getattr(cls, VER_METHOD_ATTR, {})
            if not func_dict:
                setattr(cls, VER_METHOD_ATTR, func_dict)

            func_list = func_dict.get(func_name, [])
            if not func_list:
                func_dict[func_name] = func_list
            func_list.append(new_func)

            # Ensure the list is sorted by minimum version (reversed) so when
            # we walk through the list later in order we find the method with
            # the latest version which supports the version requested
            func_list.sort(key=lambda f: f.min_version, reverse=True)

            return f

        return decorator

    def default(self, req, **args):
        raise exc.HTTPNotFound()


def log_exception(err):
    LOG.error("Unexpected error occurred serving API: %s", err)


def translate_exception(ex, locale):
    """Translate all translatable elements of the given exception."""
    if isinstance(ex, exception.SenlinException):
        ex.message = oslo_i18n.translate(ex.message, locale)
    else:
        ex.message = oslo_i18n.translate(str(ex), locale)

    if isinstance(ex, exc.HTTPError):
        ex.explanation = oslo_i18n.translate(ex.explanation, locale)
        ex.detail = oslo_i18n.translate(getattr(ex, 'detail', ''), locale)
    return ex


class BasePasteFactory(object, metaclass=abc.ABCMeta):
    """A base class for paste app and filter factories.

    Sub-classes must override the KEY class attribute and provide
    a __call__ method.
    """

    KEY = None

    def __init__(self, conf):
        self.conf = conf

    @abc.abstractmethod
    def __call__(self, global_conf, **local_conf):
        return

    def _import_factory(self, local_conf):
        """Import an app/filter class.

        Lookup the KEY from the PasteDeploy local conf and import the
        class named there. This class can then be used as an app or
        filter factory.
        """
        class_name = local_conf[self.KEY].replace(':', '.').strip()
        return importutils.import_class(class_name)


class AppFactory(BasePasteFactory):
    """A Generic paste.deploy app factory.

    The WSGI app constructor must accept a ConfigOpts object and a local
    config dict as its arguments.
    """

    KEY = 'senlin.app_factory'

    def __call__(self, global_conf, **local_conf):

        factory = self._import_factory(local_conf)
        return factory(self.conf, **local_conf)


class FilterFactory(AppFactory):
    """A Generic paste.deploy filter factory.

    This requires senlin.filter_factory to be set to a callable which returns
    a WSGI filter when invoked. The WSGI filter constructor must accept a
    WSGI app, a ConfigOpts object and a local config dict as its arguments.
    """

    KEY = 'senlin.filter_factory'

    def __call__(self, global_conf, **local_conf):

        factory = self._import_factory(local_conf)

        def filter(app):
            return factory(app, self.conf, **local_conf)

        return filter


def setup_paste_factories(conf):
    """Set up the generic paste app and filter factories.

    The app factories are constructed at runtime to allow us to pass a
    ConfigOpts object to the WSGI classes.

    :param conf: a ConfigOpts object
    """
    global app_factory, filter_factory

    app_factory = AppFactory(conf)
    filter_factory = FilterFactory(conf)


def teardown_paste_factories():
    """Reverse the effect of setup_paste_factories()."""
    global app_factory, filter_factory

    del app_factory
    del filter_factory


def paste_deploy_app(paste_config_file, app_name, conf):
    """Load a WSGI app from a PasteDeploy configuration.

    Use deploy.loadapp() to load the app from the PasteDeploy configuration,
    ensuring that the supplied ConfigOpts object is passed to the app and
    filter constructors.

    :param paste_config_file: a PasteDeploy config file
    :param app_name: the name of the app/pipeline to load from the file
    :param conf: a ConfigOpts object to supply to the app and its filters
    :returns: the WSGI app
    """
    setup_paste_factories(conf)
    try:
        return deploy.loadapp("config:%s" % paste_config_file, name=app_name)
    finally:
        teardown_paste_factories()


def _get_deployment_config_file():
    """Retrieve item from deployment_config_file.

    The retrieved item is formatted as an absolute pathname.
    """
    config_path = cfg.CONF.find_file(cfg.CONF.senlin_api.api_paste_config)
    if config_path is None:
        return None

    return os.path.abspath(config_path)


def load_paste_app(app_name=None):
    """Build and return a WSGI app from a paste config file.

    We assume the last config file specified in the supplied ConfigOpts
    object is the paste config file.

    :param app_name: name of the application to load

    :raises RuntimeError when config file cannot be located or application
            cannot be loaded from config file
    """
    if app_name is None:
        app_name = cfg.CONF.prog

    conf_file = _get_deployment_config_file()
    if conf_file is None:
        raise RuntimeError(_("Unable to locate config file"))

    try:
        app = paste_deploy_app(conf_file, app_name, cfg.CONF)

        # Log the options used when starting if we're in debug mode...
        if cfg.CONF.debug:
            cfg.CONF.log_opt_values(logging.getLogger(app_name),
                                    logging.DEBUG)

        return app
    except (LookupError, ImportError) as e:
        raise RuntimeError(_("Unable to load %(app_name)s from "
                             "configuration file %(conf_file)s."
                             "\nGot: %(e)r") % {'app_name': app_name,
                                                'conf_file': conf_file,
                                                'e': e})
