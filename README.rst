========================
Team and repository tags
========================

.. image:: https://governance.openstack.org/tc/badges/senlin.svg
    :target: https://governance.openstack.org/tc/reference/tags/index.html

.. Change things from this point on

Senlin
======

--------
Overview
--------

Senlin is a clustering service for OpenStack clouds. It creates and operates
clusters of homogeneous objects exposed by other OpenStack services. The goal
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
under the ``doc/source/user/`` subdirectory. User guide online link:
https://docs.openstack.org/senlin/latest/#user-references

--------------
For Developers
--------------

There are many ways to help improve the software, for example, filing a bug,
submitting or reviewing a patch, writing or reviewing some documents. There
are documents under the ``doc/source/contributor`` subdirectory. Developer
guide online link: https://docs.openstack.org/senlin/latest/#developer-s-guide

---------
Resources
---------

Launchpad Projects
------------------
- Server: https://launchpad.net/senlin
- Client: https://launchpad.net/python-senlinclient
- Dashboard: https://launchpad.net/senlin-dashboard
- Tempest Plugin: https://launchpad.net/senlin-tempest-plugin

Code Repository
---------------
- Server: https://opendev.org/openstack/senlin
- Client: https://opendev.org/openstack/python-senlinclient
- Dashboard: https://opendev.org/openstack/senlin-dashboard
- Tempest Plugin: https://opendev.org/openstack/senlin-tempest-plugin

Blueprints
----------
- Blueprints: https://blueprints.launchpad.net/senlin

Bug Tracking
------------
- Server Bugs: https://bugs.launchpad.net/senlin
- Client Bugs: https://bugs.launchpad.net/python-senlinclient
- Dashboard Bugs: https://bugs.launchpad.net/senlin-dashboard
- Tempest Plugin Bugs: https://bugs.launchpad.net/senlin-tempest-plugin

Weekly Meetings
---------------
- Schedule: every Tuesday at 1300 UTC, on #openstack-meeting channel
- Agenda: https://wiki.openstack.org/wiki/Meetings/SenlinAgenda
- Archive: http://eavesdrop.openstack.org/meetings/senlin/2015/

IRC
---
IRC Channel: #senlin on `OFTC`_.

Mailinglist
-----------
Project use http://lists.openstack.org/cgi-bin/mailman/listinfo/openstack-discuss
as the mailinglist. Please use tag ``[Senlin]`` in the subject for new
threads.


.. _OFTC: https://oftc.net/

Release notes
------------------
- Release notes: https://docs.openstack.org/releasenotes/senlin/
