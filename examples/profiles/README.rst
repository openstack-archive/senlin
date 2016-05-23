How To Use the Sample Spec File
===============================

This directory contains sample spec files that can be used to create a
Senlin profile using `senlin profile-create` command, for example:

To create a os.nova.server profile::

  $ cd ./nova_server
  $ senlin profile-create -s cirros_basic.yaml my_server

To create a os.heat.stack profile::

  $ cd ./heat_stack/nova_server
  $ senlin profile-create -s heat_stack_nova_server.yaml my_stack

To get help on the command line options for creating profiles::

  $ senlin help profile-create

To show the profile created::

  $ senlin profile-show <profile_id>
