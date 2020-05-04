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
from unittest import mock

from oslo_config import cfg

from senlin.cmd import health_manager
from senlin.common import config
from senlin.common import consts
from senlin.common import messaging
from senlin.common import profiler
from senlin.health_manager import service
from senlin.tests.unit.common import base

CONF = cfg.CONF


class TestHealthManager(base.SenlinTestCase):
    def setUp(self):
        super(TestHealthManager, self).setUp()

    @mock.patch('oslo_log.log.setup')
    @mock.patch('oslo_log.log.set_defaults')
    @mock.patch('oslo_service.service.launch')
    @mock.patch.object(config, 'parse_args')
    @mock.patch.object(messaging, 'setup')
    @mock.patch.object(profiler, 'setup')
    @mock.patch.object(service, 'HealthManagerService')
    def test_main(self, mock_service, mock_profiler_setup,
                  mock_messaging_setup, mock_parse_args, mock_launch,
                  mock_log_set_defaults, mock_log_setup):
        health_manager.main()

        mock_parse_args.assert_called_once()
        mock_log_setup.assert_called_once()
        mock_log_set_defaults.assert_called_once()
        mock_messaging_setup.assert_called_once()
        mock_profiler_setup.assert_called_once()

        mock_service.assert_called_once_with(
            mock.ANY, consts.HEALTH_MANAGER_TOPIC
        )

        mock_launch.assert_called_once_with(
            mock.ANY, mock.ANY, workers=1, restart_method='mutate'
        )
