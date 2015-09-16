
HIGH PRIORITY
=============

DRIVER
------
  - Handle Heat stack operation exceptions [Qiming]

POLICY
------
  - Investigate the impact of node-create and node-delete on certain policies.
  - Implement a placement policy which supports cross-az/region node creation
    with some simple algorithms, e.g. ROUND_ROBIN, FIXED_PRIORITY. [Xinhui, Qiming]
  - Implement a deletion policy that supports cross-az/region node deleting.

TEST CASES
----------

  - Add test case the profile context can be saved and loaded correctly.

MIDDLE PRIORITY
===============

API
---
  - Revise the API for sorting, based on the following guideline:
    https://github.com/openstack/api-wg/blob/master/guidelines/pagination_filter_sort.rst
  - According to the guidelines from API WG, we need to support `page_reverse`
    as a pagination parameter. https://review.openstack.org/190743
  - Add support to replace a cluster node with another node
  - Make object creation requests return code 202, since most creation
    are done asynchronously in Senlin.
  - Make object creation requests return a location header set to the URI
    of the resource to be created. This is a requirement from API WG.
  - API resource names should not include underscores. A guideline from API
    WG.
  - Add API doc for CLUSTER_RESIZE operation.
  - Add API doc for webhook APIs operation.
  - Add support to have Senlin API run under Apache.

DB
--
  - Add test cases for policy_delete with 'force' set to True[Liuh/ZhaiHF]
  - The action data model is missing 'scheduled_start' and 'scheduled_stop'
    fields, we will need these fields for scheduled action execution.

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
  - Check if pre-context middleware needs logging and add special supports.

POLICY
------
  - Scaling policy allowng a cluster to scale to existing nodes
  - Health policy

DRIVER
------


LOW PRIORITY
============

API
---

  - Allow forced deletion of objects (cluster, node, policy, profile). The
    current problem is due to the limitations of the HTTP DELETE requests. We
    need to investigate whether a DELETE verb can carry query strings.

DRIVER
------
  - add Heat resource driver

TEST
----
  - Add test case to engine/parser

DOC
-----
  - Provide a sample conf file for customizing senlin options
