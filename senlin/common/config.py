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

"""
Routines for configuring Senlin
"""
from oslo_log import log
from oslo_middleware import cors
from oslo_policy import opts
from oslo_utils import importutils

import senlin.conf
from senlin import version

profiler = importutils.try_import('osprofiler.opts')

CONF = senlin.conf.CONF


def parse_args(argv, name, default_config_files=None):
    log.register_options(CONF)

    if profiler:
        profiler.set_defaults(CONF)

    set_config_defaults()

    CONF(
        argv[1:],
        project='senlin',
        prog=name,
        version=version.version_info.version_string(),
        default_config_files=default_config_files,
    )


def set_config_defaults():
    """Update default configuration options for oslo.middleware."""
    cors.set_defaults(
        allow_headers=['X-Auth-Token',
                       'X-Identity-Status',
                       'X-Roles',
                       'X-Service-Catalog',
                       'X-User-Id',
                       'X-Tenant-Id',
                       'X-OpenStack-Request-ID'],
        expose_headers=['X-Auth-Token',
                        'X-Subject-Token',
                        'X-Service-Token',
                        'X-OpenStack-Request-ID'],
        allow_methods=['GET',
                       'PUT',
                       'POST',
                       'DELETE',
                       'PATCH'])

    # TODO(gmann): Remove setting the default value of config policy_file
    # once oslo_policy change the default value to 'policy.yaml'.
    # https://github.com/openstack/oslo.policy/blob/a626ad12fe5a3abd49d70e3e5b95589d279ab578/oslo_policy/opts.py#L49
    opts.set_defaults(CONF, 'policy.yaml')
