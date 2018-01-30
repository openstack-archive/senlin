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

from oslo_config import cfg

from senlin.drivers import base
from senlin.drivers import sdk


class HeatClient(base.DriverBase):
    '''Heat V1 driver.'''

    def __init__(self, params):
        super(HeatClient, self).__init__(params)
        self.conn = sdk.create_connection(params)

    @sdk.translate_exception
    def stack_create(self, **params):
        return self.conn.orchestration.create_stack(**params)

    @sdk.translate_exception
    def stack_get(self, stack_id):
        return self.conn.orchestration.get_stack(stack_id)

    @sdk.translate_exception
    def stack_find(self, name_or_id):
        return self.conn.orchestration.find_stack(name_or_id)

    @sdk.translate_exception
    def stack_list(self):
        return self.conn.orchestration.stacks()

    @sdk.translate_exception
    def stack_update(self, stack_id, **params):
        return self.conn.orchestration.update_stack(stack_id, **params)

    @sdk.translate_exception
    def stack_delete(self, stack_id, ignore_missing=True):
        return self.conn.orchestration.delete_stack(stack_id,
                                                    ignore_missing)

    @sdk.translate_exception
    def stack_check(self, stack_id):
        return self.conn.orchestration.check_stack(stack_id)

    @sdk.translate_exception
    def stack_get_environment(self, stack_id):
        return self.conn.orchestration.get_stack_environment(stack_id)

    @sdk.translate_exception
    def stack_get_files(self, stack_id):
        return self.conn.orchestration.get_stack_files(stack_id)

    @sdk.translate_exception
    def stack_get_template(self, stack_id):
        return self.conn.orchestration.get_stack_template(stack_id)

    @sdk.translate_exception
    def wait_for_stack(self, stack_id, status, failures=None, interval=2,
                       timeout=None):
        if failures is None:
            failures = []

        if timeout is None:
            timeout = cfg.CONF.default_action_timeout

        stack_obj = self.conn.orchestration.find_stack(stack_id, False)
        if stack_obj:
            self.conn.orchestration.wait_for_status(
                stack_obj, status, failures, interval, timeout)

    @sdk.translate_exception
    def wait_for_stack_delete(self, stack_id, timeout=None):
        '''Wait for stack deleting complete'''
        if timeout is None:
            timeout = cfg.CONF.default_action_timeout

        server_obj = self.conn.orchestration.find_stack(stack_id, True)
        if server_obj:
            self.conn.orchestration.wait_for_delete(server_obj, wait=timeout)

        return
