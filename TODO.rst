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

  - Add support to put a cluster to maintenance mode

ENGINE
------
  - Complete support to list of health recovery actions.

  - Add command "node adopt --profile-type <type> --properties network.id=\
    <NET_ID> --resource <NOVA_ID>" to adopt existing server node.
    * The new command should check if the provided properties are sufficient.
    * There exists a need to snapshot a server before adoption.


MIDDLE PRIORITY
===============

API
---
  - Support advanced filters as suggested by the API WG:
    `Filtering Guidelines`_

ENGINE
------
  - Add a new property "fast_scaling" to Cluster
    * A standby (user invisible) cluster is created containing the extra nodes
      that amount to max_size - desired_capacity
  - Perform cluster scaling based on role filters
  - Perform cluster checking based on role filters
  - Perform cluster recovery based on role filters

PROFILE
-------
  - Add support to snapshot/restore operations for nova server profile. The
    possible use case is rapid scale.
  - Add support to nova server so that "block_device_mapping_v2" can reference
    an existing pool of cinder volumes.
  - Add support to nova server so that "network" can reference an existing
    pool of neutron ports or fixed IPs.

POLICY
------
  - Provide support for watching all objects we created on behalf of users, like
    loadbalancer which is created when attaching lb policy.
  - Leverage other monitoring service for object health status monitoring.
  - Health policy extension for recovery action selection based on inputs

CLIENT
------
  - Provide role-based filtering when doing 'cluster-run'

LOW PRIORITY
============

ENGINE
------
  - Allow actions to be paused and resumed. This is important for some background
    actions such as health checking.
  - Provide support to oslo.notification and allow nodes to receive and react
    to those notifications accordingly: `Autoscaling Notifications`_

PROFILE
-------
  - Support disk property update for os.nova.server profile

DOC
---
  - Provide a sample conf file for customizing senlin options.

TEST
----
  - Add more Rally profile and scenario support for Senlin.

OTHERS
------
  - Integration with Glare for profile/policy specs storage. At least we may
    want to enable users to retrieve/reference heat templates from glare when
    creating profiles.


.. _`Filtering Guidelines`: https://specs.openstack.org/openstack/api-wg/guidelines/pagination_filter_sort.html#filtering
.. _`Autoscaling Notifications`: https://ask.openstack.org/en/question/46495/heat-autoscaling-adaptation-actions-on-existing-servers/
