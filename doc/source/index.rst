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
   install
   configuration

2 Tutorial
~~~~~~~~~~

This tutorial walks you through the Senlin features step-by-step. For more
details, please check the :ref:`user-references` section.

.. toctree::
   :maxdepth: 1

   tutorial/basics
   tutorial/policies
   tutorial/receivers

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
   user/policy_types/deletion
   user/policy_types/load_balancing
   user/policy_types/scaling
   user/policy_types/region_placement
   user/policy_types/zone_placement

4 Usage Scenarios
~~~~~~~~~~~~~~~~~

This section provides some guides for typical usage scenarios. More scenarios
are to be added

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

   developer/api_microversion
   developer/authorization
   developer/profile
   developer/cluster
   developer/node
   developer/policy
   developer/action
   developer/receiver
   developer/testing
   developer/plugin_guide
   developer/osprofiler

5.2 Built-in Policy Types
-------------------------

Senlin provides some built-in policy types which can be instantiated and then
attached to your clusters. These policy types are designed to be orthogonal so
that each of them can be used independently. They are also expected to work
in a collaborative way to meet the needs of complicated usage scenarios.

.. toctree::
   :maxdepth: 1

   developer/policies/affinity_v1
   developer/policies/deletion_v1
   developer/policies/health_v1
   developer/policies/load_balance_v1
   developer/policies/region_v1
   developer/policies/scaling_v1
   developer/policies/zone_v1

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

  developer/reviews

6 References
~~~~~~~~~~~~

6.1 API Documentation
---------------------

Follow the link below for the Senlin API V1 specification:

-  `OpenStack API Complete Reference - Clustering`_

6.2 Man Pages
-------------

.. toctree::
   :maxdepth: 1

   man/index

6.3 Glossary
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
