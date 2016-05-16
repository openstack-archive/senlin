#!/bin/bash
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

# This script is executed inside pre_test_hook function in devstack gate.

export localconf=$BASE/new/devstack/local.conf
export SENLIN_CONF=/etc/senlin/senlin.conf
export SENLIN_BACKEND=${SENLIN_BACKEND:-'openstack_test'}

_LOG_CFG='default_log_levels ='
_LOG_CFG+='amqp=WARN,amqplib=WARN,sqlalchemy=WARN,oslo_messaging=WARN'
_LOG_CFG+=',iso8601=WARN,requests.packages.urllib3.connectionpool=WARN'
_LOG_CFG+=',urllib3.connectionpool=WARN'
_LOG_CFG+=',requests.packages.urllib3.util.retry=WARN,urllib3.util.retry=WARN'
_LOG_CFG+=',keystonemiddleware=WARN'
_LOG_CFG+=',routes.middleware=WARN'
_LOG_CFG+=',stevedore=WARN'
_LOG_CFG+=',oslo_messaging._drivers.amqp=WARN'
_LOG_CFG+=',oslo_messaging._drivers.amqpdriver=WARN'

echo -e '[[post-config|$SENLIN_CONF]]\n[DEFAULT]\n' >> $localconf
echo -e 'num_engine_workers=2\n' >> $localconf
echo -e "cloud_backend=$SENLIN_BACKEND\n" >> $localconf
echo -e $_LOG_CFG >> $localconf
