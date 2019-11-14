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
Senlin Health-Manager.
"""
from oslo_config import cfg
from oslo_log import log as logging
from oslo_reports import guru_meditation_report as gmr
from oslo_service import service

from senlin.common import consts
from senlin.common import messaging
from senlin.common import profiler
from senlin import objects
from senlin import version


def main():
    logging.register_options(cfg.CONF)
    cfg.CONF(project='senlin', prog='senlin-health-manager')
    logging.setup(cfg.CONF, 'senlin-health-manager')
    logging.set_defaults()
    gmr.TextGuruMeditation.setup_autorun(version)
    objects.register_all()
    messaging.setup()

    from senlin.health_manager import service as health_manager

    profiler.setup('senlin-health-manager', cfg.CONF.host)
    srv = health_manager.HealthManagerService(cfg.CONF.host,
                                              consts.HEALTH_MANAGER_TOPIC)
    launcher = service.launch(cfg.CONF, srv,
                              workers=cfg.CONF.health_manager.workers,
                              restart_method='mutate')
    launcher.wait()
