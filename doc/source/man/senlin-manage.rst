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
maitenance operations.


OPTIONS
~~~~~~~

To issue a senlin-manage command:

``senlin-manage <action> [options]``

Run with `-h` or `--help` to see a list of available commands:

``senlin-manage -h``

Commands are `db_version`, `db_sync` . Below are some detailed descriptions.


Senlin DB version
-----------------

``senlin-manage db_version``

    Print out the db schema revision.

``senlin-manage db_sync``

    Sync the database up to the most recent version.


FILES
~~~~~

The /etc/senlin/senlin.conf file contains global options which can be
used to configure some aspects of `senlin-manage`, for example the DB
connection and logging options.


BUGS
~~~~

* Senlin issues are tracked in Launchpad so you can view or report bugs here
  `OpenStack Senlin Bugs <https://bugs.launchpad.net/senlin>`__
