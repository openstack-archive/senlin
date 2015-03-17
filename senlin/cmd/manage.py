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

'''
CLI interface for senlin management.
'''

import sys

from oslo_config import cfg
from oslo_log import log as logging

from senlin.common.i18n import _
from senlin.db import api
from senlin.db import utils
from senlin import version

CONF = cfg.CONF


def do_db_version():
    '''Print database's current migration level.'''
    print(api.db_version(api.get_engine()))


def do_db_sync():
    '''Place a database under migration control and upgrade.

    DB is created first if necessary.
    '''
    api.db_sync(api.get_engine(), CONF.command.version)


def purge_deleted():
    """Remove database records that have been previously soft deleted."""

    utils.purge_deleted(CONF.command.age, CONF.command.granularity)


def add_command_parsers(subparsers):
    parser = subparsers.add_parser('db_version')
    parser.set_defaults(func=do_db_version)

    parser = subparsers.add_parser('db_sync')
    parser.set_defaults(func=do_db_sync)
    parser.add_argument('version', nargs='?')
    parser.add_argument('current_version', nargs='?')

    parser = subparsers.add_parser('purge_deleted')
    parser.set_defaults(func=purge_deleted)
    parser.add_argument('age', nargs='?', default='90',
                        help=_('How long to preserve deleted data.'))
    parser.add_argument(
        '-g', '--granularity', default='days',
        choices=['days', 'hours', 'minutes', 'seconds'],
        help=_('Granularity to use for age argument, defaults to days.'))

command_opt = cfg.SubCommandOpt('command',
                                title='Commands',
                                help='Show available commands.',
                                handler=add_command_parsers)


def main():
    logging.register_options(CONF)
    logging.setup(CONF, 'senlin-manage')
    CONF.register_cli_opt(command_opt)

    try:
        default_config_files = cfg.find_config_files('senlin', 'senlin-engine')
        CONF(sys.argv[1:], project='senlin', prog='senlin-manage',
             version=version.version_info.version_string(),
             default_config_files=default_config_files)
    except RuntimeError as e:
        sys.exit("ERROR: %s" % e)

    try:
        CONF.command.func()
    except Exception as e:
        sys.exit("ERROR: %s" % e)
