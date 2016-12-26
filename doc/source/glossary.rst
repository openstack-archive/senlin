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


========
Glossary
========

This section contains the glossary for the Senlin service.

.. glossary::
   :sorted:

   Action
     An action is an operation that can be performed on a :term:`Cluster` or a
     :term:`Node` etc. Different types of objects support different set of
     actions. An action is executed by a :term:`Worker` thread when the action
     becomes READY. Most Senlin APIs create actions in database for worker
     threads to execute asynchronously. An action, when executed, will check
     and enforce :term:`Policy` associated with the cluster. An action can be
     triggered via :term:`Receiver`.

   API server
     HTTP REST API service for Senlin.

   Cluster
     A cluster is a group of homogeneous objects (i.e. :term:`Node`). A
     cluster consists of 0 or more nodes and it can be associated with 0 or
     more :term:`Policy` objects. It is associated with a :term:`Profile Type`
     when created.

   Dependency
     The :term:`Action` objects are stored into database for execution. These
     actions may have dependencies among them.

   Dispatcher
     A dispatcher is a processor that takes a Senlin :term:`Action` as input
     and then converts it into a desired format for storage or further
     processing.

   Driver
     A driver is a Senlin internal module that enables Senlin :term:`Engine` to
     interact with other :term:`OpenStack` services. The interactions here are
     usually used to create, destroy, update the objects exposed by those
     services.

   Engine
     The daemon that actually perform the operations requested by users. It
     provides RPC interfaces to RPC clients.

   Environment
     Used to specify user provided :term:`Plugin` that implement a
     :term:`Profile Type` or a :term:`Policy Type`. User can provide plugins
     that override the default plugins by customizing an environment.

   Event
     An event is a record left in Senlin database when something matters to
     users happened. An event can be of different criticality levels.

   Index
     An integer property of a :term:`Node` when it is a member of a
     :term:`Cluster`.  Each node has an auto-generated index value that is
     unique in the cluster.

   Node
     A node is an object that belongs to at most one :term:`Cluster`. A node
     can become an 'orphaned node' when it is not a member of any clusters.
     All nodes in a cluster must be of the same :term:`Profile Type` of the
     owning cluster. In general, a node represents a physical object exposed
     by other OpenStack services.  A node has a unique :term:`Index` value
     scoped to the cluster that owns it.

   Permission
     A string dictating which user (role or group) has what permissions on a
     given object (i.e. :term:`Cluster`, :term:`Node`, :term:`Profile` and
     :term:`Policy` etc.)

   Plugin
     A plugin is an implementation of a :term:`Policy Type` or :term:`Profile
     Type` that can be dynamically loaded and registered to Senlin engine.
     Senlin engine comes with a set of builtin plugins. Users can add their own
     plugins by customizing the :term:`Environment` configuration.

   Policy
     A policy is a set of rules that can be checked and/or enforced when an
     :term:`Action` is performed on a :term:`Cluster`. A policy is an instance
     of a particular :term:`Policy Type`. Users can specify the enforcement
     level when creating a policy object. Such a policy object can be attached
     to and detached from a cluster.

   Policy Type
     A policy type is an abstraction of :term:`Policy` objects. The
     implementation of a policy type specifies when the policy should be
     checked and/or enforce, what profile types are supported, what operations
     are to be done before, during and after each :term:`Action`. All policy
     types are provided as Senlin plugins.

   Profile
     A profile is a mould used for creating objects (i.e. :term:`Node`). A
     profile is an instance of a :term:`Profile Type` with all required
     information specified. Each profile has a unique ID. As a guideline, a
     profile cannot be updated once created. To change a profile, you have to
     create a new instance.

   Profile Type
     A profile type is an abstraction of objects that are backed by some
     :term:`Driver`. The implementation of a profile type calls the driver(s)
     to create objects that are managed by Senlin. The implementation also
     serves a factory that can "produce" objects given a profile. All profile
     types are provided as Senlin plugins.

   Role
     A role is a string property that can be assigned to a :term:`Node`.
     Nodes in the same cluster may assume a role for certain reason such as
     application configuration. The default role for a node is empty.

   OpenStack
     Open source software for building private and public clouds.

   Receiver
     A receiver is an abstract resource created at the senlin engine that can
     be used to hook the engine to some external event/alarm sources. A
     receiver can be of different types. The most common type is a
     :term:`Webhook`.

   Webhook
     A webhook is an encoded URI (Uniform Resource Identifier) that for
     triggering some operations (e.g. Senlin actions) on some resources. Such
     a webhook URL is the only thing one needs to know to trigger an action on
     a cluster.

   Worker
     A worker is the thread created and managed by Senlin engine to execute
     an :term:`Action` that becomes ready.  When the current action completes
     (with a success or failure), a worker will check the database to find
     another action for execution.
