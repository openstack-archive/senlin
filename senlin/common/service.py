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

import senlin.conf
from senlin import version

CONF = senlin.conf.CONF
LOG = logging.getLogger(__name__)


class Service(service.Service):
    def __init__(self, name, host, topic, threads=None):
        threads = threads or 1000
        super(Service, self).__init__(threads)
        self.name = name
        self.host = host
        self.topic = topic

    def start(self):
        LOG.info('Starting %(name)s service (version: %(version)s)',
                 {
                     'name': self.name,
                     'version': version.version_info.version_string()
                 })
        super(Service, self).start()

    def stop(self, graceful=True):
        LOG.info('Stopping %(name)s service', {'name': self.name})
        super(Service, self).stop(graceful)


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
