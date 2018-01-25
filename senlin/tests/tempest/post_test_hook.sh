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

set -ex

export DEST=${DEST:-/opt/stack/new}
export DEVSTACK_DIR=$DEST/devstack
export SENLIN_DIR=$DEST/senlin

source $DEVSTACK_DIR/openrc admin admin

cd $DEST/tempest
echo "Running tempest " $SENLIN_TEST_TYPE "tests"
sudo tox -evenv-tempest -- tempest run --regex $DEVSTACK_GATE_TEMPEST_REGEX
