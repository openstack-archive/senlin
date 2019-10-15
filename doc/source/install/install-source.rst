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

.. _install-source:

============================
Install from Git Source Code
============================

Install Senlin Server
---------------------

1. Get Senlin source code from OpenStack git repository.

::

  $ cd /opt/stack
  $ git clone https://git.openstack.org/openstack/senlin.git

2. Install Senlin with required packages.

::

  $ cd /opt/stack/senlin
  $ sudo pip install -e .

3. Register Senlin clustering service with keystone.

   This can be done using the :command:`setup-service` script under the
   :file:`tools` folder.

   **NOTE:** Suppose you have devstack installed under the
   :file:`/opt/devstack` folder

::

  $ . /opt/devstack/openrc admin admin
  $ cd /opt/stack/senlin/tools
  $ ./setup-service <HOST IP> <SERVICE_PASSWORD>

4. Generate configuration file for the Senlin service.

::

  $ cd /opt/stack/senlin
  $ tools/gen-config
  $ sudo mkdir /etc/senlin
  $ sudo cp etc/senlin/api-paste.ini /etc/senlin
  $ sudo cp etc/senlin/senlin.conf.sample /etc/senlin/senlin.conf

Edit file :file:`/etc/senlin/senlin.conf` according to your system settings.
The most common options to be customized include:

::

  [database]
  connection = mysql+pymysql://senlin:<MYSQL_SENLIN_PW>@127.0.0.1/senlin?charset=utf8

  [keystone_authtoken]
  service_token_roles_required = True
  auth_type = password
  user_domain_name = Default
  project_domain_name = Default
  project_name = service
  username = senlin
  password = <SENLIN_PASSWORD>
  www_authenticate_uri = http://<HOST>/identity/v3
  auth_url = http://<HOST>/identity

  [authentication]
  auth_url = http://<HOST>:5000/v3
  service_username = senlin
  service_password = <SENLIN PASSWORD>
  service_project_name = service

  [oslo_messaging_rabbit]
  rabbit_userid = <RABBIT USER ID>
  rabbit_hosts = <HOST>
  rabbit_password = <RABBIT PASSWORD>

  [oslo_messaging_notifications]
  driver = messaging

For more comprehensive helps on configuration options, please refer to
:doc:`Configuration Options </configuration/index>` documentation.

In case you want to modify access policies of Senlin, please generate sample
policy file, copy it to `/etc/senlin/policy.yaml` and then update it.

::

  $ cd /opt/stack/senlin
  $ tools/gen-policy
  $ sudo cp etc/senlin/policy.yaml.sample /etc/senlin/policy.yaml

5. Create Senlin Database.

Create Senlin database using the :command:`senlin-db-recreate` script under
the :file:`tools` subdirectory. Before calling the script, you need edit it
to customize the password you will use for the ``senlin`` user. You need to
update this script with the <DB PASSWORD> entered in step4.

::

  $ cd /opt/stack/senlin/tools
  $ ./senlin-db-recreate

6. Start the senlin api, conductor, engine and health-manager services.

You may need multiple consoles for the services i.e., one for each service.

::

  $ senlin-conductor --config-file /etc/senlin/senlin.conf
  $ senlin-engine --config-file /etc/senlin/senlin.conf
  $ senlin-health-manager --config-file /etc/senlin/senlin.conf
  $ senlin-api --config-file /etc/senlin/senlin.conf

Install Senlin Client
---------------------

1. Get Senlin client code from OpenStack git repository.

::

  $ cd /opt/stack
  $ git clone https://git.openstack.org/openstack/python-senlinclient.git

2. Install senlin client.

::

  $ cd python-senlinclient
  $ sudo python setup.py install

