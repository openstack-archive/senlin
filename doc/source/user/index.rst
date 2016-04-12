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
