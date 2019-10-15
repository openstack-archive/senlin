================
senlin-conductor
================

.. program:: senlin-conductor

SYNOPSIS
~~~~~~~~

``senlin-conductor [options]``

DESCRIPTION
~~~~~~~~~~~

senlin-conductor provides an internal RPC interface for the senlin-api to
invoke.

INVENTORY
~~~~~~~~~

The senlin-conductor provides an internal RPC interface.

OPTIONS
~~~~~~~
.. cmdoption:: --config-file

  Path to a config file to use. Multiple config files can be specified, with
  values in later files taking precedence.


.. cmdoption:: --config-dir

  Path to a config directory to pull .conf files from. This file set is
  sorted, so as to provide a predictable parse order if individual options are
  over-ridden. The set is parsed after the file(s), if any, specified via
  --config-file, hence over-ridden options in the directory take precedence.

FILES
~~~~~

* /etc/senlin/senlin.conf

BUGS
~~~~

* Senlin issues are tracked in Launchpad so you can view or report bugs here
  `OpenStack Senlin Bugs <https://bugs.launchpad.net/senlin>`__
