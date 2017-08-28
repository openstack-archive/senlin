
Files in this directory are tools for developers or for helping users install
the senlin software.

--------
Contents
--------

``config-generator.conf``

  This is a configuration for the oslo-config-generator tool to create an
  initial `senlin.conf.sample` file. When installing senlin manually, the
  generated file can be copied to `/etc/senlin/senlin.conf` with customized
  settings.


``gen-config``

  This is a wrapper of the oslo-config-generator tool that generates a config
  file for senlin. The correct way to use it is::

   cd /opt/stack/senlin
   tools/gen-config

  Another way to generate sample configuration file is::

   cd /opt/stack/senlin
   tox -e genconfig


``gen-pot-files``

  This is a script for extracting strings from source code into a POT file,
  which serves the basis to generate translations for different languages.


``senlin-db-recreate``

  This script drops the `senlin` database in mysql when database is corrupted.

  **Warning**
  Be sure to change the 'MYSQL_ROOT_PW' and 'MYSQL_SENLIN_PW' before running
  this script.


``setup-service``

  This is a script for setting up the ``senlin`` service. You will need to
  provide the host IP address and the service password for the ``senlin``
  user to be created. For example::

    cd /opt/stack/senlin/tools
    ./setup-service 192.168.52.5 TopSecrete

  **NOTE**
  You need to have some environment variables properly set so that you are
  the ``admin`` user for setting up the ``senlin`` service. For example::

    cd $HOME
    . devstack/openrc admin
