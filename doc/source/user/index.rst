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

.. _ref-index:

===============
User References
===============

Project Scope and Vision
~~~~~~~~~~~~~~~~~~~~~~~~

* Senlin provides a clustering solution for :term:`OpenStack` cloud. A user
  can create clusters of :term:`node` and associate :term:`policy` to such
  a cluster.
* The software interacts with other components of OpenStack so that clusters
  of resources exposed by those components can be created and operated.
* The software complements Heat project each other so Senlin can create and
  manage clusters of Heat stacks while Heat can invoke Senlin APIs to
  orchestrate collections of homogeneous resources.
* Senlin provides policies as plugins that can be used to specify how clusters
  operate. Example policies include creation policy, placement policy,
  deletion policy, load-balancing policy, scaling policy etc.
* Senlin can interact with all other OpenStack components via :term:`profile`
  plugins. Each profile type implementation enable Senlin to create resources
  provided by a corresponding OpenStack service.


Working with Senlin
~~~~~~~~~~~~~~~~~~~

.. toctree::
   :maxdepth: 1

   profile_types
   profiles
   clusters
   nodes
   membership
   policy_types
   policies
   bindings
   receivers
   actions
   events

Built-in Policy Types
~~~~~~~~~~~~~~~~~~~~~

The senlin service is released with some builtin policy types that target some
most common use cases. You can develop and deploy your own policy types by
following the instructions in the
:doc:`developer guide <../../developer/index>`.

The following is a list of builtin policy types that are shipped with the
service package.

.. toctree::
   :maxdepth: 1

   policy_types/affinity
   policy_types/deletion
   policy_types/load_balancing
   policy_types/scaling
   policy_types/region_placement
   policy_types/zone_placement


Usage Scenarios
~~~~~~~~~~~~~~~

This section provides some guides for typical usage scenarios.

.. toctree::
   :maxdepth: 1

   scenarios/affinity
   scenarios/autoscaling
