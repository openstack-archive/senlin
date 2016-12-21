..
  Licensed under the Apache License, Version 2.0 (the "License"); you may
  not use this file except in compliance with the License. You may obtain
  a copy of the License at

          http://www.apache.org/licenses/LICENSE-2.0

  Unless required by applicable law or agreed to in writing, software
  distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
  WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
  License for the specific language governing permissions and limitations
  under the License.

====================================
Welcome to the Senlin documentation!
====================================

1 Introduction
~~~~~~~~~~~~~~

Senlin is a service to create and manage :term:`cluster` of multiple cloud
resources. Senlin provides an OpenStack-native REST API and a AWS
AutoScaling-compatible Query API is in plan.

.. toctree::
   :maxdepth: 1

   overview

2 Install and Configuration
~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. toctree::
   :maxdepth: 1

   overview
   install
   configuration

3 Tutorial
~~~~~~~~~~

This tutorial walks you through the Senlin features step-by-step. For more
details, please check the :ref:`user-references` section.

.. toctree::
   :maxdepth: 1

   tutorial/basics
   tutorial/policies
   tutorial/receivers
   tutorial/autoscaling
   tutorial/heat

.. _user-references:

4 User References
~~~~~~~~~~~~~~~~~

This section provides a detailed documentation for the concepts and built-in
policy types.

4.1 Basic Concepts
------------------

.. toctree::
   :maxdepth: 1

   user/profile_types
   user/profiles
   user/clusters
   user/nodes
   user/membership
   user/policy_types
   user/policies
   user/bindings
   user/receivers
   user/actions
   user/events

4.2 Built-in Policy Types
-------------------------

The senlin service is released with some built-in policy types that target
some common use cases. You can develop and deploy your own policy types by
following the instructions in the :ref:`developer-guide` section.

The following is a list of builtin policy types:

.. toctree::
   :maxdepth: 1

   user/policy_types/affinity
   user/policy_types/deletion
   user/policy_types/load_balancing
   user/policy_types/scaling
   user/policy_types/region_placement
   user/policy_types/zone_placement

5 Usage Scenarios
~~~~~~~~~~~~~~~~~

This section provides some guides for typical usage scenarios. More scenarios
are to be added

5.1 Managing Node Affinity
--------------------------

Senlin provides an :doc:`Affinity Policy <user/policy_types/affinity>` for
managing node affinity. This section contains a detailed introduction on how
to use it.

.. toctree::
   :maxdepth: 1

   scenarios/affinity

5.2 Building AutoScaling Clusters
---------------------------------

The senlin service provides a rich set of facilities for building an
auto-scaling solution:

- *Operations*: The ``CLUSTER_SCALE_OUT``, ``CLUSTER_SCALE_IN`` operations are
  the simplest form of commands to scale a cluster. The ``CLUSTER_RESIZE``
  operation, on the other hand, provides more options for controlling the
  detailed cluster scaling behavior. These operations can be performed with
  and without policies attached to a cluster.

- *Policies*:
  The ``senlin.policy.scaling`` (:doc:`link <user/policy_types/scaling>`) policy
  can be applied to fine tune the cluster scaling operations.
  The ``senlin.policy.deletion`` (:doc:`link <user/policy_types/deletion>`)
  policy can be attached to a cluster to control how nodes are removed from a
  cluster.
  The ``senlin.policy.affinity`` (:doc:`link <user/policy_types/affinity>`)
  policy can be used to control how node affinity or anti-affinity can be
  enforced.
  The ``senlin.policy.region_placement``
  (:doc:`link <user/policy_types/region_placement>`) can be applied to scale a
  cluster across multiple regions.
  The ``senlin.policy.zone_placement``
  (:doc:`link <user/policy_types/zone_placement>`) can be enforced to achieve
  a cross-availability-zone node distribution.

- *Receivers*: The receiver (:doc:`link <user/receivers>`) concept provides a
  channel to which you can send signals or alarms from an external monitoring
  software or service so that scaling operations can be automated.

This section provides some guides on integrating senlin with other services
so that cluster scaling can be automated.

.. toctree::
   :maxdepth: 1

   scenarios/autoscaling_ceilometer
   scenarios/autoscaling_heat

.. _developer-guide:

6. Developer's Guide
~~~~~~~~~~~~~~~~~~~~

This section targets senlin contributors.

6.1 Understanding the Design
----------------------------

.. toctree::
   :maxdepth: 1

   developer/authorization
   developer/profile
   developer/cluster
   developer/node
   developer/policy
   developer/action
   developer/receiver
   developer/testing
   developer/plugin_guide
   developer/api_microversion
   developer/osprofiler

6.2 Built-in Policy Types
-------------------------

Senlin provides some built-in policy types which can be instantiated and then
attached to your clusters. These policy types are designed to be orthogonal so
that each of them can be used independently. They are also expected to work
in a collaborative way to meet the needs of complicated usage scenarios.

.. toctree::
   :maxdepth: 1

   developer/policies/affinity_v1
   developer/policies/deletion_v1
   developer/policies/load_balance_v1
   developer/policies/region_v1
   developer/policies/scaling_v1
   developer/policies/zone_v1

6.3 Reviewing Patches
~~~~~~~~~~~~~~~~~~~~~

There are many general guidelines across the community about code reviews, for
example:

- `Code review guidelines (wiki)`_
- `OpenStack developer's guide`_

Besides these guidelines, senlin has some additional amendments based on daily
review experiences that should be practiced.

.. toctree::
  :maxdepth: 1

  developer/reviews


7 References
~~~~~~~~~~~~

7.1 API Documentation
---------------------

Follow the link below for the Senlin API V1 specification:

-  `OpenStack API Complete Reference - Clustering`_

7.2 Man Pages
-------------

.. toctree::
   :maxdepth: 1

   man/index

7.3 Glossary
------------

.. toctree::
   :maxdepth: 1

   glossary

Indices and tables
------------------

* :ref:`genindex`
* :ref:`search`

.. _`Code review guidelines (wiki)`: https://wiki.openstack.org/wiki/CodeReviewGuidelines
.. _`OpenStack developer's guide`: http://docs.openstack.org/infra/manual/developers.html
.. _`OpenStack API Complete Reference - Clustering`: http://developer.openstack.org/api-ref/clustering/
