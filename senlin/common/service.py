# All Rights Reserved.
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
from oslo_log import log as logging
from oslo_service import service

from oslo_service import sslutils
from oslo_service import wsgi
from oslo_utils import netutils
from oslo_utils import uuidutils

from senlin.common import context as senlin_context
import senlin.conf
from senlin.objects import service as service_obj
from senlin import version

CONF = senlin.conf.CONF
LOG = logging.getLogger(__name__)


class Service(service.Service):
    def __init__(self, name, host, topic, threads=None):
        self.tg = None
        super(Service, self).__init__(threads or 1000)
        self.name = name
        self.host = host
        self.topic = topic

        self.server = None
        self.service_id = None
        self.cleanup_timer = None
        self.cleanup_count = 0
        self.service_report_timer = None

        # Start the service cleanup process. This is only going to be
        # running on the main process.
        if self.tg:
            self.cleanup_timer = self.tg.add_timer(
                CONF.periodic_interval, self.service_manage_cleanup
            )

    def start(self):
        super(Service, self).start()
        self.service_id = uuidutils.generate_uuid()
        LOG.info(
            'Starting %(name)s service (version: %(version)s '
            'id: %(service_id)s)',
            {
                'name': self.name,
                'version': version.version_info.version_string(),
                'service_id': self.service_id,
            }
        )
        ctx = senlin_context.get_admin_context()
        service_obj.Service.create(
            ctx, self.service_id, self.host, self.name, self.topic
        )
        self.service_report_timer = self.tg.add_timer(
            CONF.periodic_interval, self.service_manage_report
        )

    def stop(self, graceful=True):
        LOG.info(
            'Stopping %(name)s service (id: %(service_id)s)',
            {
                'name': self.name,
                'service_id': self.service_id or 'main',
            }
        )
        if self.service_report_timer:
            self.service_report_timer.stop()
            self.service_report_timer = None
        if self.cleanup_timer:
            self.cleanup_timer.stop()
            self.cleanup_timer = None
        if self.service_id:
            service_obj.Service.delete(self.service_id)
        super(Service, self).stop(graceful)

    def service_manage_cleanup(self):
        self.cleanup_count += 1
        try:
            ctx = senlin_context.get_admin_context()
            services = service_obj.Service.get_all_expired(
                ctx, self.name
            )
            for svc in services:
                LOG.info(
                    'Breaking locks for dead service %(name)s '
                    '(id: %(service_id)s)',
                    {
                        'name': self.name,
                        'service_id': svc['id'],
                    }
                )
                service_obj.Service.gc_by_engine(svc['id'])
                LOG.info(
                    'Done breaking locks for service %(name)s '
                    '(id: %(service_id)s)',
                    {
                        'name': self.name,
                        'service_id': svc['id'],
                    }
                )
                service_obj.Service.delete(svc['id'])
        except Exception as ex:
            LOG.error(
                'Error while cleaning up service %(name)s: %(ex)s',
                {
                    'name': self.name,
                    'ex': ex,
                }
            )

        # The clean-up process runs during service startup and will over
        # multiple attempts check to see if any services have reach the
        # deadline and if so remove them. This is only done on startup, or
        # after a service recovers from a crash.
        if self.cleanup_count >= 5:
            self.cleanup_timer.stop()
            self.cleanup_timer = None
            LOG.info('Finished cleaning up dead services.')
        else:
            LOG.info('Service clean-up attempt count: %s', self.cleanup_count)

    def service_manage_report(self):
        try:
            ctx = senlin_context.get_admin_context()
            service_obj.Service.update(ctx, self.service_id)
        except Exception as ex:
            LOG.error(
                'Error while updating service %(name)s: %(ex)s',
                {
                    'name': self.name,
                    'ex': ex,
                }
            )


class WSGIService(service.Service):
    def __init__(self, app, name, listen, max_url_len=None):
        super(WSGIService, self).__init__(CONF.senlin_api.threads)
        self.app = app
        self.name = name

        self.listen = listen

        self.servers = []

        for address in self.listen:
            host, port = netutils.parse_host_port(address)
            server = wsgi.Server(
                CONF, name, app,
                host=host,
                port=port,
                pool_size=CONF.senlin_api.threads,
                use_ssl=sslutils.is_enabled(CONF),
                max_url_len=max_url_len
            )

            self.servers.append(server)

    def start(self):
        for server in self.servers:
            server.start()
        super(WSGIService, self).start()

    def stop(self, graceful=True):
        for server in self.servers:
            server.stop()
        super(WSGIService, self).stop(graceful)

    def wait(self):
        for server in self.servers:
            server.wait()
        super(WSGIService, self).wait()
