..
  Licensed under the Apache License, Version 2.0 (the "License"); you may
  not use this file except in compliance with the License. You may obtain
  a copy of the License at

          http://www.apache.org/licenses/LICENSE-2.0

  Unless required by applicable law or agreed to in writing, software
  distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
  WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
  License for the specific language governing permissions and limitations
  under the License.

.. _install-devstack:

====================
Install via Devstack
====================

This is the recommended way to install the Senlin service. Please refer to
following detailed instructions.

1. Download DevStack::

    $ git clone https://git.openstack.org/openstack-dev/devstack
    $ cd devstack

2. Add following repo as external repositories into your ``local.conf`` file::

    [[local|localrc]]
    #Enable senlin
    enable_plugin senlin https://git.openstack.org/openstack/senlin
    #Enable senlin-dashboard
    enable_plugin senlin-dashboard https://git.openstack.org/openstack/senlin-dashboard

Optionally, you can add a line ``SENLIN_USE_MOD_WSGI=True`` to the same ``local.conf``
file if you prefer running the Senlin API service under Apache.

3. Run ``./stack.sh``::

    $ ./stack.sh

Note that Senlin client is also installed when following the instructions.


