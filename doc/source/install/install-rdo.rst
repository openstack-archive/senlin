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

.. _install-rdo:

===============
Install via RDO
===============

This section describes how to install and configure the Senlin service
for Red Hat Enterprise Linux 7 and CentOS 7.

This install file support from ``pike`` version.

Prerequisites
-------------

Before you install and configure Senlin, you must create a
database, service credentials, and API endpoints. Senlin also
requires additional information in the Identity service.

1. To create the database, complete these steps:

* Use the database access client to connect to the database
  server as the ``root`` user:

::

        $ mysql -u root -p

* Create the ``senlin`` database:

::

        CREATE DATABASE senlin DEFAULT CHARACTER SET utf8;

* Grant proper access to the ``senlin`` database:

::

        GRANT ALL ON senlin.* TO 'senlin'@'localhost' \
          IDENTIFIED BY 'SENLIN_DBPASS';
        GRANT ALL ON senlin.* TO 'senlin'@'%' \
          IDENTIFIED BY 'SENLIN_DBPASS';

Replace ``Senlin_DBPASS`` with a suitable password.

* Exit the database access client.

2. Source the ``admin`` credentials to gain access to
   admin-only CLI commands:

::

      $ . admin-openrc

3. To create the service credentials, complete these steps:

* Create the ``senlin`` user:

::

        $openstack user create --project service --password-prompt senlin
        User Password:
        Repeat User Password:
        +-----------+----------------------------------+
        | Field     | Value                            |
        +-----------+----------------------------------+
        | domain_id | e0353a670a9e496da891347c589539e9 |
        | enabled   | True                             |
        | id        | ca2e175b851943349be29a328cc5e360 |
        | name      | senlin                           |
        +-----------+----------------------------------+

* Add the ``admin`` role to the ``senlin`` user:

::

        $ openstack role add --project service --user senlin admin

     .. note::

        This command provides no output.

* Create the ``senlin`` service entities:

::

        $ openstack service create --name senlin \
          --description "Senlin Clustering Service V1" clustering
        +-------------+----------------------------------+
        | Field       | Value                            |
        +-------------+----------------------------------+
        | description | Senlin Clustering Service V1     |
        | enabled     | True                             |
        | id          | 727841c6f5df4773baa4e8a5ae7d72eb |
        | name        | senlin                           |
        | type        | clustering                       |
        +-------------+----------------------------------+

4. Create the senlin service API endpoints:

::

      $ openstack endpoint create senlin --region RegionOne \
        public http://controller:8777
      +--------------+----------------------------------+
      | Field        | Value                            |
      +--------------+----------------------------------+
      | enabled      | True                             |
      | id           | 90485e3442544509849e3c79bf93c15d |
      | interface    | public                           |
      | region       | RegionOne                        |
      | region_id    | RegionOne                        |
      | service_id   | 9130295921b04601a81f95c417b9f113 |
      | service_name | senlin                           |
      | service_type | clustering                       |
      | url          | http://controller:8777           |
      +--------------+----------------------------------+

      $ openstack endpoint create senlin --region RegionOne \
        admin http://controller:8777
      +--------------+----------------------------------+
      | Field        | Value                            |
      +--------------+----------------------------------+
      | enabled      | True                             |
      | id           | d4a9f5a902574479a73e520dd3f93dfb |
      | interface    | admin                            |
      | region       | RegionOne                        |
      | region_id    | RegionOne                        |
      | service_id   | 9130295921b04601a81f95c417b9f113 |
      | service_name | senlin                           |
      | service_type | clustering                       |
      | url          | http://controller:8777           |
      +--------------+----------------------------------+

      $ openstack endpoint create senlin --region RegionOne \
        internal http://controller:8777
      +--------------+----------------------------------+
      | Field        | Value                            |
      +--------------+----------------------------------+
      | enabled      | True                             |
      | id           | d119b192857e4760a196ba2b88d20bc6 |
      | interface    | internal                         |
      | region       | RegionOne                        |
      | region_id    | RegionOne                        |
      | service_id   | 9130295921b04601a81f95c417b9f113 |
      | service_name | senlin                           |
      | service_type | clustering                       |
      | url          | http://controller:8777           |
      +--------------+----------------------------------+

Install and configure components
--------------------------------

.. note::

   Default configuration files vary by distribution. You might need
   to add these sections and options rather than modifying existing
   sections and options. Also, an ellipsis (``...``) in the configuration
   snippets indicates potential default configuration options that you
   should retain.

1. Install the packages:

::

      # yum install openstack-senlin-api.noarch \
        openstack-senlin-common.noarch \
        openstack-senlin-conductor.noarch \
        openstack-senlin-engine.noarch \
        openstack-senlin-health-manager.noarch \
        python3-senlinclient.noarch

2. Edit file :file:`/etc/senlin/senlin.conf` according to your system settings. The most common options to be customized include:

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


3. Populate the Senlin database:

::

      # senlin-manage db_sync

   .. note::

      Ignore any deprecation messages in this output.

Finalize installation
---------------------

* Start the Senlin services and configure them to start
  when the system boots:

::

     # systemctl enable openstack-senlin-api.service \
        openstack-senlin-conductor.service \
        openstack-senlin-engine.service \
        openstack-senlin-health-manager.service
     # systemctl start openstack-senlin-api.service \
        openstack-senlin-conductor.service \
        openstack-senlin-engine.service \
        openstack-senlin-health-manager.service
