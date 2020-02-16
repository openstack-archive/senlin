#!/usr/bin/env python
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

"""
Senlin API Server.
"""
import sys

from oslo_log import log as logging
from oslo_reports import guru_meditation_report as gmr
from oslo_service import systemd

from senlin.api.common import wsgi
from senlin.common import config
from senlin.common import messaging
from senlin.common import profiler
import senlin.conf
from senlin import objects
from senlin import version

CONF = senlin.conf.CONF
LOG = logging.getLogger('senlin.api')


def main():
    config.parse_args(sys.argv, 'senlin-api')
    logging.setup(CONF, 'senlin-api')
    gmr.TextGuruMeditation.setup_autorun(version)
    objects.register_all()
    messaging.setup()

    app = wsgi.load_paste_app()

    host = CONF.senlin_api.bind_host
    port = CONF.senlin_api.bind_port
    LOG.info('Starting Senlin API on %(host)s:%(port)s',
             {'host': host, 'port': port})
    profiler.setup('senlin-api', host)
    server = wsgi.Server('senlin-api', CONF.senlin_api)
    server.start(app, default_port=port)
    systemd.notify_once()
    server.wait()
