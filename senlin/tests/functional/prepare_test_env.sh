#!/bin/bash -xe

# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

# This script is executed inside post_test_hook function in devstack gate.

export DEST=${DEST:-/opt/stack/new}
export SENLIN_CONF=/etc/senlin/senlin.conf

source $DEST/devstack/inc/ini-config

# Send SIGHUP to service
function sighup_proc()
{
    NAME=$1
    ID=`ps -ef | grep "$NAME" | grep -v "$0" | grep -v "grep" | awk '{print $2}'`
    for id in $ID
    do
        kill -1 $id
        echo "sighup $id"
    done
}

# Switch cloud_backend to openstack_test
iniset $SENLIN_CONF DEFAULT cloud_backend openstack_test
sighup_proc senlin-engine
sleep 10
