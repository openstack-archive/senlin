=============
senlin-manage
=============

.. program:: senlin-manage

SYNOPSIS
~~~~~~~~

``senlin-manage <action> [options]``

DESCRIPTION
~~~~~~~~~~~

senlin-manage provides utilities for operators to manage Senlin specific
maintenance operations.


OPTIONS
~~~~~~~

To issue a senlin-manage command:

``senlin-manage <action> [options]``

Run with `-h` or `--help` to see a list of available commands:

``senlin-manage -h``

Commands are `db_version`, `db_sync`, `service`, `event_purge` . Below are
some detailed descriptions.


Senlin DB version
-----------------

``senlin-manage db_version``

Print out the db schema revision.

``senlin-manage db_sync``

Sync the database up to the most recent version.


Senlin Service Manage
---------------------

``senlin-manage service list``

Print out the senlin-engine service status.

``senlin-manage service clean``

Cleanup senlin-engine dead service.


Senlin Event Manage
-------------------

``senlin-manage event_purge -p [<project1;project2...>] -g {days,hours,minutes,seconds} age``

Purge the specified event records in senlin's database.

You can use command purge three days ago data.

::

   senlin-manage event_purge -p e127900ee5d94ff5aff30173aa607765 -g days 3


Senlin Action Manage
--------------------

``senlin-manage action_purge -p [<project1;project2...>] -g {days,hours,minutes,seconds} age``

Purge the specified action records in senlin's database.

You can use this command to purge actions that are older than 3 days.

::

   senlin-manage action_purge -p e127900ee5d94ff5aff30173aa607765 -g days 3


FILES
~~~~~

The /etc/senlin/senlin.conf file contains global options which can be
used to configure some aspects of `senlin-manage`, for example the DB
connection and logging options.


BUGS
~~~~

* Senlin issues are tracked in Launchpad so you can view or report bugs here
  `OpenStack Senlin Bugs <https://bugs.launchpad.net/senlin>`__
