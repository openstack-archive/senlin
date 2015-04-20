senlin
======

Senlin is a clustering service for OpenStack cloud. It creates and operates
clusters of homogenous objects exposed by other OpenStack services. The
goal is to make orchestration of collections of similar objects easier.

Senlin provides ReSTful APIs to users so that they can associate various
policies to a cluster.  Sample policies include placement policy, load
balancing policy, failover policy, scaling policy, ... and so on.

IRC Channel: #senlin

--------------------
Install via Devstack
--------------------

This is the recommended way to install Senlin service. Please refer to
`devstack/README.rst` for detailed instructions.

Note that Senlin client is also installed when following the instructions
it the above mentioned document.

-------------------
Manual Installation
-------------------


Install Senlin Server
---------------------

1. Get Senlin source code from OpenStack git repository

::

  $ cd /opt/stack
  $ git clone http://git.openstack.org/stackforge/senlin.git

2. Install Senlin with required packages

::

  $ cd /opt/stack/senlin
  $ sudo pip install -e .

3. Register Senlin clustering service with keystone.

   This can be done using the `setup-service` script under `tools` folder.

::

  $ cd /opt/stack/senlin/tools
  $ ./setup-service <HOST IP>

4. Generate configuration file for the Senlin service

::

  $ cd /opt/stack/senlin
  $ tools/gen-config
  $ sudo mkdir /etc/senlin
  $ cp etc/senlin/api-paste.ini /etc/senlin
  $ cp etc/senlin/policy.json /etc/senlin
  $ cp etc/senlin/senlin.conf.sample

Edit file `/etc/senlin/senlin.conf` according to your system settings. The
most common options to be customized include::

  [database]
  connection = mysql://senlin:<DB PASSWORD>.0.0.1/senlin?charset=utf8

  [keystone_authtoken]
  auth_uri = http://<HOST>:5000/v3
  auth_version = 3
  cafile = /opt/stack/data/ca-bundle.pem
  identity_uri = http://<HOST>:35357
  admin_user = senlin
  admin_password = <SENLIN PASSWORD>
  admin_tenant_name = service

  [oslo_messaging_rabbit]
  rabbit_host = <HOST>
  rabbit_password = <RABBIT PASSWORD>

5. Create Senlin Database

 Create Senlin database using the `senlin-db-recreate` script under the `tools`
 subdirectory. Before calling the script, you need edit it to customize the
 password you will use for the `senlin` user.

::

  $ cd /opt/stack/senlin/tools
  $ ./senlin-db-recreate

6. Start senlin engine and api service.

 You may need two consoles for the services each.

::

  $ senlin-engine --config-file /etc/senlin/senlin.conf
  $ senlin-api --config-file /etc/senlin/senlin.conf

---------------------
Install Senlin Client
---------------------

1. Get Senlin client code from OpenStack git repository.

::

  $ cd /opt/stack
  $ git clone http://git.openstack.org/stackforge/python-senlinclient.git

2. Install senlin client.

::

  $ cd python-senlinclient
  $ python setup.py install

You are ready to begin your journey (aka. adventure) with Senlin, now.
