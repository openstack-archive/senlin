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

.. _guide-install:

============
Installation
============

There are in general two ways to install Senlin service: you can install it
via devstack, or you install it manually, following the steps outlined in this
document.


Install via Devstack
~~~~~~~~~~~~~~~~~~~~

This is the recommended way to install the Senlin service. Please refer to
following detailed instructions.

1. Download DevStack::

    $ git clone https://git.openstack.org/openstack-dev/devstack
    $ cd devstack

2. Add this repo as an external repository into your ``local.conf`` file::

    [[local|localrc]]
    enable_plugin senlin https://git.openstack.org/openstack/senlin

3. Run ``stack.sh``::

    $ stack.sh

Note that Senlin client is also installed when following the instructions.


Manual Installation
~~~~~~~~~~~~~~~~~~~

Install Senlin Server
---------------------

1. Get Senlin source code from OpenStack git repository.

::

  $ cd /opt/stack
  $ git clone http://git.openstack.org/openstack/senlin.git

2. Install Senlin with required packages.

::

  $ cd /opt/stack/senlin
  $ sudo pip install -e .

3. Register Senlin clustering service with keystone.

   This can be done using the :command:`setup-service` script under the
   :file:`tools` folder.

::

  $ source ~/devstack/openrc admin
  $ cd /opt/stack/senlin/tools
  $ ./setup-service <HOST IP> <SERVICE_PASSWORD>

4. Generate configuration file for the Senlin service.

::

  $ cd /opt/stack/senlin
  $ tools/gen-config
  $ sudo mkdir /etc/senlin
  $ sudo cp etc/senlin/api-paste.ini /etc/senlin
  $ sudo cp etc/senlin/policy.json /etc/senlin
  $ sudo cp etc/senlin/senlin.conf.sample /etc/senlin/senlin.conf

Edit file :file:`/etc/senlin/senlin.conf` according to your system settings.
The most common options to be customized include:

::

  [database]
  connection = mysql://senlin:<MYSQL_SENLIN_PW>@127.0.0.1/senlin?charset=utf8

  [keystone_authtoken]
  auth_uri = http://<HOST>:5000/v3
  auth_version = 3
  cafile = /opt/stack/data/ca-bundle.pem
  identity_uri = http://<HOST>:35357
  admin_user = senlin
  admin_password = <SENLIN PASSWORD>
  admin_tenant_name = service

  [authentication]
  auth_url = http://<HOST>:5000/v3
  service_username = senlin
  service_password = <SENLIN PASSWORD>
  service_project_name = service

  [oslo_messaging_rabbit]
  rabbit_userid = <RABBIT USER ID>
  rabbit_hosts = <HOST>
  rabbit_password = <RABBIT PASSWORD>

5. Create Senlin Database.

 Create Senlin database using the :command:`senlin-db-recreate` script under
 the :file:`tools` subdirectory. Before calling the script, you need edit it
 to customize the password you will use for the ``senlin`` user. You need to
 update this script with the <DB PASSWORD> entered in step4.

::

  $ cd /opt/stack/senlin/tools
  $ ./senlin-db-recreate

6. Start senlin engine and api service.

 You may need two consoles for the services i.e., one for each service.

::

  $ senlin-engine --config-file /etc/senlin/senlin.conf
  $ senlin-api --config-file /etc/senlin/senlin.conf

Install Senlin Client
---------------------

1. Get Senlin client code from OpenStack git repository.

::

  $ cd /opt/stack
  $ git clone http://git.openstack.org/openstack/python-senlinclient.git

2. Install senlin client.

::

  $ cd python-senlinclient
  $ sudo python setup.py install

Verify Your Installation
------------------------

To check whether Senlin server and Senlin client have been installed
successfully, run command ``openstack cluster build info`` in a console.
The installation is successful if the command output looks similar to the
following.

::

  $ openstack cluster build info
  +----------+---------------------+
  | Property | Value               |
  +----------+---------------------+
  | api      | {                   |
  |          |   "revision": "1.0" |
  |          | }                   |
  | engine   | {                   |
  |          |   "revision": "1.0" |
  |          | }                   |
  +----------+---------------------+

You are ready to begin your journey (aka. adventure) with Senlin, now.
