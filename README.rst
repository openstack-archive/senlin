Senlin
======

--------
Overview
--------

Senlin is a clustering service for OpenStack clouds. It creates and operates
clusters of homogenous objects exposed by other OpenStack services. The goal
is to make the orchestration of collections of similar objects easier.

Senlin provides RESTful APIs to users so that they can associate various
policies to a cluster.  Sample policies include placement policy, load
balancing policy, health policy, scaling policy, update policy and so on.

Senlin is designed to be capable of managing different types of objects. An
object's lifecycle is managed using profile type implementations, which are
themselves plugins.

---------
For Users
---------

If you want to install Senlin for a try out, please refer to the documents
under the ``doc/source/getting_started/`` subdirectory.

--------------
For Developers
--------------

There are many ways to help improve the software, for example, filing a bug,
submitting or reviewing a patch, writing or reviewing some documents. There
are documents under the ``doc/source/developer/`` subdirectory.

---------
Resources
---------

Launchpad Projects
------------------
- Server: https://launchpad.net/senlin
- Client: https://launchpad.net/python-senlinclient

Code Repository
---------------
- Server: https://git.openstack.org/cgit/openstack/senlin
- Client: https://git.openstack.org/cgit/openstack/python-senlinclient

Blueprints
----------
- Blueprints: https://blueprints.launchpad.net/senlin

Bug Tracking
------------
- Bugs: https://bugs.launchpad.net/senlin

Weekly Meetings
---------------
- Schedule: every Tuesday at 1300 UTC, on #openstack-meeting channel
- Agenda: http://wiki.openstack.org/wiki/Meetings/SenlinAgenda
- Archive: http://eavesdrop.openstack.org/meetings/senlin/2015/

IRC
---
IRC Channel: #senlin on `Freenode`_.

Mailinglist
-----------
Project use http://lists.openstack.org/cgi-bin/mailman/listinfo/openstack-dev
as the mailinglist. Please use tag ``[Senlin]`` in the subject for new
threads.


.. _Freenode: http://freenode.net/
