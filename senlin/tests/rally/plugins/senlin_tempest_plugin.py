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

from rally.plugins.openstack import scenario
from rally.plugins.openstack.scenarios.tempest import tempest
from rally.plugins.openstack.scenarios.tempest import utils
from rally.task import validation


class SenlinTempestScenario(tempest.TempestScenario):
    """Plugin for Senlin tempest scenarios test."""

    @validation.required_openstack(admin=True)
    @scenario.configure(context={"tempest": {}})
    @utils.tempest_log_wrapper
    def single_test(self, test_name, log_file, tempest_conf=None):
        """Launch a single Tempest test by its name.

        :param test_name: name of Senlin tempest test case for launching
        :param log_file: name of file for junitxml results
        :param tempest_conf: User specified tempest.conf location
        """
        self.context["verifier"].run(test_name, log_file=log_file,
                                     tempest_conf=tempest_conf)
