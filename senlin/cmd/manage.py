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
CLI interface for senlin management.
"""

import sys

from oslo_config import cfg
from oslo_log import log as logging
from oslo_utils import timeutils

from senlin.common import context
from senlin.common.i18n import _
from senlin.db import api
from senlin.objects import service as service_obj
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


def do_event_purge():
    '''Purge the specified event records in senlin's database.'''
    if CONF.command.age < 0:
        print(_("age must be a positive integer."))
        return
    api.event_purge(api.get_engine(),
                    CONF.command.project_id,
                    CONF.command.granularity,
                    CONF.command.age)


class ServiceManageCommand(object):
    def __init__(self):
        self.ctx = context.get_admin_context()

    def _format_service(self, service):
        if service is None:
            return

        status = 'up'
        CONF.import_opt('periodic_interval', 'senlin.common.config')
        max_interval = 2 * CONF.periodic_interval
        if timeutils.is_older_than(service.updated_at, max_interval):
            status = 'down'

        result = {
            'service_id': service.id,
            'binary': service.binary,
            'host': service.host,
            'topic': service.topic,
            'created_at': service.created_at,
            'updated_at': service.updated_at,
            'status': status
        }
        return result

    def service_list(self):
        services = [self._format_service(service)
                    for service in service_obj.Service.get_all(self.ctx)]

        print_format = "%-36s %-24s %-16s %-16s %-10s %-24s %-24s"
        print(print_format % (_('Service ID'),
                              _('Host'),
                              _('Binary'),
                              _('Topic'),
                              _('Status'),
                              _('Created At'),
                              _('Updated At')))

        for svc in services:
            print(print_format % (svc['service_id'],
                                  svc['host'],
                                  svc['binary'],
                                  svc['topic'],
                                  svc['status'],
                                  svc['created_at'],
                                  svc['updated_at']))

    def service_clean(self):
        for service in service_obj.Service.get_all(self.ctx):
            svc = self._format_service(service)
            if svc['status'] == 'down':
                print(_('Dead service %s is removed.') % svc['service_id'])
                service_obj.Service.delete(svc['service_id'])

    @staticmethod
    def add_service_parsers(subparsers):
        service_parser = subparsers.add_parser('service')
        service_parser.set_defaults(command_object=ServiceManageCommand)
        service_subparsers = service_parser.add_subparsers(dest='action')
        list_parser = service_subparsers.add_parser('list')
        list_parser.set_defaults(func=ServiceManageCommand().service_list)
        remove_parser = service_subparsers.add_parser('clean')
        remove_parser.set_defaults(func=ServiceManageCommand().service_clean)


def add_command_parsers(subparsers):
    parser = subparsers.add_parser('db_version')
    parser.set_defaults(func=do_db_version)

    parser = subparsers.add_parser('db_sync')
    parser.set_defaults(func=do_db_sync)
    ServiceManageCommand.add_service_parsers(subparsers)
    parser.add_argument('version', nargs='?')
    parser.add_argument('current_version', nargs='?')

    parser = subparsers.add_parser('event_purge')
    parser.set_defaults(func=do_event_purge)
    parser.add_argument('-p',
                        '--project-id',
                        nargs='?',
                        metavar='<project1;project2...>',
                        help=_("Purge event records with specified project. "
                               "This can be specified multiple times, or once "
                               "with parameters separated by semicolon."),
                        action='append')
    parser.add_argument('-g',
                        '--granularity',
                        default='days',
                        choices=['days', 'hours', 'minutes', 'seconds'],
                        help=_("Purge event records which were created in the "
                               "specified time period. The time is specified "
                               "by age and granularity, whose value must be "
                               "one of 'days', 'hours', 'minutes' or "
                               "'seconds' (default)."))
    parser.add_argument('age',
                        type=int,
                        default=30,
                        help=_("Purge event records which were created in the "
                               "specified time period. The time is specified "
                               "by age and granularity. For example, "
                               "granularity=hours and age=2 means purging "
                               "events created two hours ago. Defaults to "
                               "30."))


command_opt = cfg.SubCommandOpt('command',
                                title='Commands',
                                help=_('Show available commands.'),
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
