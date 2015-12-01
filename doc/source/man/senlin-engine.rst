=============
senlin-engine
=============

.. program:: senlin-engine

SYNOPSIS
~~~~~~~~

``senlin-engine [options]``

DESCRIPTION
~~~~~~~~~~~

senlin-engine is the server that perform operations on objects such as
clusters, nodes, policies and profiles.  It provides an internal RPC
interface for the senlin-api to invoke.

INVENTORY
~~~~~~~~~

The senlin-engine provides services to the callers so that requests on
various objects can be met by background operations. Senlin models most
operations as asynchronous actions, so most operations are not to be assumed
as completed when the calls return.

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
