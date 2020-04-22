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

Senlin is a service to create and manage :term:`Cluster` of multiple cloud
resources. Senlin provides an OpenStack-native REST API and a AWS
AutoScaling-compatible Query API is in plan.

.. toctree::
   :maxdepth: 1

   overview
   install/index
   configuration/index

2 Tutorial
~~~~~~~~~~

This tutorial walks you through the Senlin features step-by-step. For more
details, please check the :ref:`user-references` section.

.. toctree::
   :maxdepth: 1

   tutorial/basics
   tutorial/policies
   tutorial/receivers
   tutorial/autoscaling

.. _user-references:

3 User References
~~~~~~~~~~~~~~~~~

This section provides a detailed documentation for the concepts and built-in
policy types.

3.1 Basic Concepts
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

3.2 Built-in Policy Types
-------------------------

The senlin service is released with some built-in policy types that target
some common use cases. You can develop and deploy your own policy types by
following the instructions in the :ref:`developer-guide` section.

The following is a list of builtin policy types:

.. toctree::
   :maxdepth: 1

   user/policy_types/affinity
   user/policy_types/batch
   user/policy_types/deletion
   user/policy_types/health
   user/policy_types/load_balancing
   user/policy_types/scaling
   user/policy_types/region_placement
   user/policy_types/zone_placement

3.3 Built-in Profile Types
--------------------------

The senlin service is released with some built-in profile types that target
some common use cases. You can develop and deploy your own profile types by
following the instructions in the :ref:`developer-guide` section.

The following is a list of builtin profile types:

.. toctree::
   :maxdepth: 1

   user/profile_types/nova
   user/profile_types/stack
   user/profile_types/docker

4 Usage Scenarios
~~~~~~~~~~~~~~~~~

This section provides some guides for typical usage scenarios. More scenarios
are to be added.

4.1 Managing Node Affinity
--------------------------

Senlin provides an :doc:`Affinity Policy <user/policy_types/affinity>` for
managing node affinity. This section contains a detailed introduction on how
to use it.

.. toctree::
   :maxdepth: 1

   scenarios/affinity

4.2 Building AutoScaling Clusters
---------------------------------

.. toctree::
   :maxdepth: 1

   scenarios/autoscaling_overview
   scenarios/autoscaling_ceilometer
   scenarios/autoscaling_heat


.. _developer-guide:

5. Developer's Guide
~~~~~~~~~~~~~~~~~~~~

This section targets senlin developers.

5.1 Understanding the Design
----------------------------

.. toctree::
   :maxdepth: 1

   contributor/api_microversion
   contributor/authorization
   contributor/profile
   contributor/cluster
   contributor/node
   contributor/policy
   contributor/action
   contributor/receiver
   contributor/testing
   contributor/plugin_guide
   contributor/osprofiler

5.2 Built-in Policy Types
-------------------------

Senlin provides some built-in policy types which can be instantiated and then
attached to your clusters. These policy types are designed to be orthogonal so
that each of them can be used independently. They are also expected to work
in a collaborative way to meet the needs of complicated usage scenarios.

.. toctree::
   :maxdepth: 1

   contributor/policies/affinity_v1
   contributor/policies/deletion_v1
   contributor/policies/health_v1
   contributor/policies/load_balance_v1
   contributor/policies/region_v1
   contributor/policies/scaling_v1
   contributor/policies/zone_v1

5.3 Reviewing Patches
---------------------

There are many general guidelines across the community about code reviews, for
example:

- `Code review guidelines (wiki)`_
- `OpenStack developer's guide`_

Besides these guidelines, senlin has some additional amendments based on daily
review experiences that should be practiced.

.. toctree::
  :maxdepth: 1

  contributor/reviews

6 Administering Senlin
~~~~~~~~~~~~~~~~~~~~~~

.. toctree::
  :maxdepth: 1

  admin/index


7 References
~~~~~~~~~~~~

.. toctree::
  :maxdepth: 1

  reference/man/index
  reference/glossary
  reference/api


Indices and tables
------------------

* :ref:`genindex`
* :ref:`search`

.. _`Code review guidelines (wiki)`: https://wiki.openstack.org/wiki/CodeReviewGuidelines
.. _`OpenStack developer's guide`: https://docs.openstack.org/infra/manual/developers.html
