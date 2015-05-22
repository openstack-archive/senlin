
HIGH PRIORITY
=============

ENGINE
------
  - cleanse scheduler module [Yanyan Hu]

DRIVER
------
  - Handle Heat stack operation exception handling [Qiming]

POLICY
------
  - healthy policy[Liuh]
  - Formalize policy enforcement levels [Qiming]
  - Enable placement policy and deletion policy to handle CLUSTER_RESIZE
    action.

TEST CASES
----------
  - Add test case the profile context can be saved and loaded correctly.

MIDDLE PRIORITY
===============

API
---
  - Revise the API for sorting, based on the following guideline:
    https://github.com/openstack/api-wg/blob/master/guidelines/pagination_filter_sort.rst
  - Add support to replace a cluster node with another node
  - Make object creation requests return code 202, since most creation
    are done asynchronously in Senlin.
  - Make object creation requests return a location header set to the URI
    of the resource to be created. This is a requirement from API WG.
  - API resource names should not include underscores. A guideline from API
    WG.
  - Add API doc for CLUSTER_RESIZE operation.
  - Add API doc for webhook APIs operation.

DB
--
  - Add test cases for policy_delete with 'force' set to True[Liuh/ZhaiHF]

ENGINE
------
  - Revise spec parser so that 'type' and 'version' are parts of the spec file
    This could be a client-only fix, or a client/server fix.

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

OSLO
----
  - Add support to oslo_versionedobjects
  - Check if pre-context middleware needs logging and add special supports.

POLICY
------
  - Scaling policy allowng a cluster to scale to existing nodes

DRIVER
------
  - Add another abstract layer which hides interface differentiation between
    multiple drivers of the same type and provides unified interface for
    profile, e.g. alarm interfaces for scaling policy which can be mapped to
    both Ceilometer or Monasca driver; loadblancer interfaces for lb policy
    which can be mapped to both Neutron LBaaS or AWS LBaaS driver.

LOW PRIORITY
============

DRIVER
------
  - add Heat resource driver
  - add exception translation in driver

TEST
----
  - Add test case to engine/parser
  - Add test case to engine/registry
  - Add test case to engine/environment

DOC
-----
  - Provide a sample conf file for customizing senlin options
