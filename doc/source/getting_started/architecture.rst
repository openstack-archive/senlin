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

Senlin Architecture
===================

Senlin is a service to create and manage clusters of homogeneous resources on
an OpenStack cloud. Senlin provides an OpenStack-native ReST API.


--------------------
Detailed Description
--------------------

What is the purpose of the project and vision for it?

Senlin provides a clustering service for OpenStack that manages a collection
of nodes that are of the same type.

Describe the relevance of the project to other OpenStack projects and the
OpenStack mission to provide a ubiquitous cloud computing platform:

The Senlin service aggregates resources exposed by other components of
OpenStack into a cluster. Such a cluster can be associated with different
policies that can be checked/enforced at varying enforcement levels. Through
service APIs, a user can dynamically add nodes to and remove nodes from a
cluster, attach and detach policies, such as creation policy, deletion policy,
load-balancing policy, scaling policy, health checking policy etc. Through
integration with other OpenStack projects, users will be enabled to manage
deployments and orchestrations large scale resource pools much easier.

Currently no other clustering service exists for OpenStack. The developers
believe cloud developers have a strong desire to create and operate resource
clusters on OpenStack deployments. The Heat project provides a preliminary
support to resource groups but Heat developers have achieved a consensus that
such kind of a service should stand on its own feet.

---------------
Senlin Services
---------------

The developers are focusing on creating an OpenStack style project using
OpenStack design tenets, implemented in Python. We have started with a close
interaction with Heat project.

As the developers have only started development in December 2014, the 
architecture is evolving rapidly.

senlin
------

The senlin tool is a CLI which communicates with the senlin-api to manage
clusters, nodes, profiles, policies and events. End developers could also use
the Senlin REST API directly.


senlin-api
----------

The senlin-api component provides an OpenStack-native REST API that processes
API requests by sending them to the senlin-engine over RPC.


senlin-engine
-------------

The senlin engine's main responsibility is to orchestrate the clusters, nodes,
profiles and policies.
