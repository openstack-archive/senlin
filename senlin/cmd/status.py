# Copyright (c) 2018 NEC, Corp.
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

import sys

from oslo_config import cfg
from oslo_upgradecheck import common_checks
from oslo_upgradecheck import upgradecheck

from senlin.common.i18n import _
from senlin.db import api

from sqlalchemy import MetaData, Table, select, column


class Checks(upgradecheck.UpgradeCommands):

    """Upgrade checks for the senlin-status upgrade check command

    Upgrade checks should be added as separate methods in this class
    and added to _upgrade_checks tuple.
    """

    def _check_healthpolicy(self):
        """Check if version 1.0 health policies exists

        Stein introduces health policy version 1.1 which is incompatible with
        health policy version 1.0.  Users are required to delete version 1.0
        health policies before upgrade and recreate them in version 1.1 format
        after upgrading.
        """

        engine = api.get_engine()
        metadata = MetaData(bind=engine)
        policy = Table('policy', metadata, autoload=True)

        healthpolicy_select = (
            select([column('name')])
            .select_from(policy)
            .where(column('type') == 'senlin.policy.health-1.0')
        )
        healthpolicy_rows = engine.execute(healthpolicy_select).fetchall()

        if not healthpolicy_rows:
            return upgradecheck.Result(upgradecheck.Code.SUCCESS)

        healthpolicy_names = [row[0] for row in healthpolicy_rows]
        error_msg = _('The following version 1.0 health policies must be '
                      'deleted before upgrade: \'{}\'. After upgrading, the '
                      'health policies can be recreated in version 1.1 '
                      'format.').format(', '.join(healthpolicy_names))
        return upgradecheck.Result(upgradecheck.Code.FAILURE, error_msg)

    # The format of the check functions is to return an
    # oslo_upgradecheck.upgradecheck.Result
    # object with the appropriate
    # oslo_upgradecheck.upgradecheck.Code and details set.
    # If the check hits warnings or failures then those should be stored
    # in the returned Result's "details" attribute. The
    # summary will be rolled up at the end of the check() method.
    _upgrade_checks = (
        # In the future there should be some real checks added here
        (_('HealthPolicy'), _check_healthpolicy),
        (_('Policy File JSON to YAML Migration'),
         (common_checks.check_policy_json, {'conf': cfg.CONF})),
    )


def main():
    return upgradecheck.main(
        cfg.CONF, project='senlin', upgrade_command=Checks())


if __name__ == '__main__':
    sys.exit(main())
