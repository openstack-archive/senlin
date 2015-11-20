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
  - Make object creation/updating requests return code 202, since most of them
    are done asynchronously in Senlin.
  - Make object creation requests return both action_id and a location header set
    to the URI of the resource to be created. This is a requirement from API WG.
  - Find and fill gaps with API-WG besides the one we already identified.

POLICY
------
  - Implement a deletion policy that supports cross-az/region node deleting.
  - Investigate the impact of node-create and node-delete on certain policies.

Health Management
-----------------
  - Provide an option for user to define the threshold of cluster health status
    classification.
  - Support do_check/do_recover in profiles.
  - Support cluster/node health status refresh and expose API interface: By
    default, 'cached' health status of Senlin objects will be provided to user.
    Object health status will only be refreshed when user requests initiatively.

TEST
----
  - Complete unit test of senlinclient

DOC
-----
  - Provide document(or docstring) for policy data passing for developers.
  - Provide documentation for existing policies.


MIDDLE PRIORITY
===============

API
---
  - Revise the API for sorting, based on the following guideline:
    https://github.com/openstack/api-wg/blob/master/guidelines/pagination_filter_sort.rst
  - According to the guidelines from API WG, we need to support `page_reverse`
    as a pagination parameter. https://review.openstack.org/190743
  - According to the proposal (https://review.openstack.org/#/c/234994/),
    actions are to follow a guideline. We may need to revise our actions API
    and those related to asynchronous operations.


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
  - Add db purge (senlin-manage) for deleting old db entries, especially for events
    and actions because they accumulate very fast.


LOW PRIORITY
============

API
---
  - Allow forced deletion of objects (cluster, node, policy, profile). The
    current problem is due to the limitations of the HTTP DELETE requests. We
    need to investigate whether a DELETE verb can carry query strings.

ENGINE
------
  - Allow actions to be paused and resumed. This is important for some background
    actions such as health checking.
  - Add support to replace a cluster node with another node.
  - Provide support to oslo.notification and allow nodes to receive and react
    to those notifications accordingly.
    [https://ask.openstack.org/en/question/46495/heat-autoscaling-adaptation-actions-on-existing-servers/]

POLICY
------
  - Scaling policy: allow a cluster to scale to existing nodes.
  - Batching policy: create batchs for node creation/deletion/update.

Trigger
-------
  - Zaqar queue based triggers.

EVENT
-----
  - Complete event log generation.

DOC
-----
  - Provide a sample conf file for customizing senlin options.
  - Give a sample end-to-end story to demonstrate how to use Senlin for autoscaling
    scenario.
