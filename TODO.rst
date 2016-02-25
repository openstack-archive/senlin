Senlin TODO Item List
=====================
This document records all workitems the team want to finish in a short-term
(usually a development cycle which lasts 6 month). All jobs listed here are NOT
in working progress which means developers can pick up any workitem they are
interested in if they do have enough time to work on it. Developer should file
a BluePrint in the launchpad to give a detailed description about their plan after
deciding to work on a specific item. A patch should be proposed as well to remove
related workitem from the TODO list after the BP gets approval.


HIGH PRIORITY
=============

API
---
  - Find and fill gaps with API-WG besides the one we already identified.

POLICY
------

  - Investigate the impact of node-create and node-delete on certain policies.


MIDDLE PRIORITY
===============

API
---
  - Support advanced filters as suggested by the API WG:
    `Filtering Guidelines`_
  - Support to ``os-request-id`` when serving api requests.

PROFILE
-------

  - Add support to template_url for heat stack profile. If template and template_url
    are both specified, use template. Need to refer to heat api test for testing heat
    profile.


POLICY
------
  - Provide support for watching all objects we created on behalf of users, like
    loadbalancer which is created when attaching lb policy.
  - Leverage other monitoring service for object health status monitoring.


DB
--
  - Add db purge (senlin-manage) for deleting events and actions because they
    accumulate very fast.


LOW PRIORITY
============

ENGINE
------
  - Allow actions to be paused and resumed. This is important for some background
    actions such as health checking.
  - Add support to replace a cluster node with another node.
  - Provide support to oslo.notification and allow nodes to receive and react
    to those notifications accordingly: `Autoscaling Notifications`_

POLICY
------
  - Scaling policy: allow a cluster to scale to existing nodes.
  - Batching policy: create batchs for node creation/deletion/update.

Receiver
--------
  - Zaqar queue based receiver.


DOC
-----
  - Provide a sample conf file for customizing senlin options.


.. _`Filtering Guidelines`: http://specs.openstack.org/openstack/api-wg/guidelines/pagination_filter_sort.html#filtering
.. _`Autoscaling Notifications`: https://ask.openstack.org/en/question/46495/heat-autoscaling-adaptation-actions-on-existing-servers/
