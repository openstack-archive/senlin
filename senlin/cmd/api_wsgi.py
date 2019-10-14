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

"""WSGI script for senlin-api.

Use this file for deploying senlin-api under Apache2(mode-wsgi).
"""
import sys

from oslo_config import cfg
from oslo_log import log as logging

from senlin.api.common import wsgi
from senlin.common import config
from senlin.common import messaging
from senlin.common import profiler
from senlin import objects


def init_app():
    config.parse_args(sys.argv, 'senlin-api')
    logging.setup(cfg.CONF, 'senlin-api')
    objects.register_all()
    messaging.setup()

    profiler.setup('senlin-api', cfg.CONF.host)
    return wsgi.load_paste_app()
