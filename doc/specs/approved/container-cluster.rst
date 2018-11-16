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

=================
Container Cluster
=================

The mission of the Senlin project is to provide a generic clustering service
for an OpenStack cloud. Currently Senlin provides Nova instance type and
Heat stack type clustering service, it's natural to think about container
cluster.

Problem Description
===================

As for container service, Magnum is a project which provides an API for users
to build the container orchestration engine such as Docker Swarm, Kubernetes
and Apache Mesos. By using these engines users can build their container cloud,
and manage the cloud. But these container clouds created by these tools are not
managed by Magnum after they are created. That means those containers are not
OpenStack-managed resources, thus other projects which want to use container
resources can't invoke Magnum to acquire them. Furthermore, the dependency on
those engines will cause version management problems and makes it difficult
to test the container engine because the engines are not implemented in Python
language. For the cloud operators who want to use OpenStack to manage
containers, they may want OpenStack's own container service instead of learning
how to use docker swarm etc.

Use Cases
=========

For users who want to use container services, they may want to use container
cluster instead of a single container. In an OpenStack cloud, user may want
to deploy containers cluster on baremetal machines or on all or some of the
specific virtual machines in the cloud. This container cluster is desired
to be a scalable, HA, multi-tenant support and high-security cloud and can
be easily controlled by invoking OpenStack standard REST API.

Proposed Changes
================

1. Docker library
   Senlin would like to support Docker type container resource. As Docker
   provides API to developers, it is very easy to create/delete a container
   resource by invoking Docker API directly.
   Docker driver will be added for container management.
2. Container Profile
   It is necessary to add a new type of profile for container to start with.
   In the container profile the required properties like network, volume etc.
   will be contained to created a container.
3. Scheduling
   To decide to start containers in which virtual/baremetal machines, a
   scheduler is needed. There are some existing container schedulers like
   docker swarm which are widely used in production, but by thinking about
   Senlin's feature, it is reasonable to invent a scheduler which can support
   container auto-scaling better. For example, starting containers
   preferentially in specified nodes whose cpu utilization is lower than a
   certain value.
   This is an intelligent but complicated solution for container scheduling,
   to meet the limited needs, Senlin placement policy can be used to work as
   a scheduler to take place of complicated scheduler implementation.
   For the simplest case, add 'host_node' and 'host_cluster' properties into
   container profile, which can be used to determine the placement of
   containers. Since Senlin supports scaling, some rules should be obeyed
   to cooperate host_node and host_cluster usage.

   * Only container type profile can contain 'host_node' and 'host_cluster'
     properties.
   * Container type profile must contain both 'host_node' and 'host_cluster'
     properties, but either not both of them can be None.
   * Host_node must belong to host_cluster.
   * If host_node is None and host_cluster is not None, container will be
     started on some node of the cluster randomly.(This may be changed in
     future, to support the case of low CPU, memory usage priority.)
4. Network
   To allocate an IP address to every container, a network for container is
   desired before creating a container. Kuryr brings container networking to
   neutron which can make container networking management similar to Nova
   server. Senlin will introduce Kuryr for container networking management.
5. Storage
   For the virtual machines in which containers will be started, it is
   necessary to attach a volume in advance. The containers started in the
   virtual machines will share the volume. Currently Flocker and Rexray are
   the options.
6. Policies
   The policies for container service are different from virtual machines.
   For example, in placement policy the specified nodes of azs or regions
   should be provided.
7. Test
   Add test cases for container service on both client and server sides.

Alternatives
------------

Any other ideas of managing containers by Senlin.

Data model impact
-----------------

None

REST API impact
---------------

None

Security impact
---------------

Not clear.

Other end user impact
---------------------

User can use Senlin commands to create/update/delete a container cluster.
Managing containers will become much easier.

Performance Impact
------------------

None

Developer Impact
----------------

None

Implementation
==============

Assignee(s)
-----------

xuhaiwei
anyone interested

Work Items
----------

Depends on the design plan

Dependencies
============

Depends on Docker.

Testing
=======

Undecided

Documentation Impact
====================

Documentation about container cluster will be added.

References
==========

None

History
=======

Approved: Newton
Implemented: Newton
