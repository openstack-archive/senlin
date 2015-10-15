
HIGH PRIORITY
=============

POLICY
------
  - Investigate the impact of node-create and node-delete on certain policies.
  - Implement a placement policy which supports cross-az/region node creation
    with a simple algorithm. [Xinhui, Qiming]
  - Implement a deletion policy that supports cross-az/region node deleting.


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
  - Add support to replace a cluster node with another node
  - Make object creation requests return code 202, since most creation
    are done asynchronously in Senlin.
  - Make object creation requests return a location header set to the URI
    of the resource to be created. This is a requirement from API WG.
  - API resource names should not include underscores. A guideline from API
    WG.
  - Add support to have Senlin API run under Apache.

DB
--
  - The action data model is missing 'scheduled_start' and 'scheduled_stop'
    fields, we may need these fields for scheduled action execution.

ENGINE
------
  - Add configuration option to enforce name uniqueness. There are reasonable
    requirements for cluster/node names to be unique within a project. This
    should be supported, maybe with the help from a name generator?

  - Design and implement dynamical plugin loading mechanism that allows 
    loading plugins from any paths

  - Provide support to oslo.notification and allow nodes to receive and react
    to those notifications accordingly.
    [https://ask.openstack.org/en/question/46495/heat-autoscaling-adaptation-actions-on-existing-servers/]

  - Allow actions to be paused and resumed.
    This is important for some background actions such as health checking

  - Add support to template_url for heat stack profile
    Note: if template and template_url are both specified, use template
    Need to refer to heat api test for testing heat profile

  - Revise start_action() in scheduler module so that it can handle cases when
    action_id specified is None. When ``action_id`` parameter is None, it
    means that the scheduler will pick a suitable READY action for execution.

  - Add event logs wherever needed. Before that, we need a design on the
    criteria for events to be emitted. [Partially done]

OSLO
----
  - Add support to oslo_versionedobjects

POLICY
------
  - Scaling policy allowng a cluster to scale to existing nodes
  - Health policy


LOW PRIORITY
============

API
---

  - Allow forced deletion of objects (cluster, node, policy, profile). The
    current problem is due to the limitations of the HTTP DELETE requests. We
    need to investigate whether a DELETE verb can carry query strings.

TEST
----
  - Add test case to engine/parser

DOC
-----
  - Provide a sample conf file for customizing senlin options
  - Provide documentation for all policies
