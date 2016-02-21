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

.. _guide-overview:

========
Overview
========

Senlin is a **clustering service** for OpenStack clouds. It creates and
operates clusters of homogeneous objects exposed by other OpenStack services.
The goal is to make orchestration of collections of similar objects easier.

A :term:`Cluster` can be associated with different :term:`Policy` objects
that can be checked/enforced at varying enforcement levels. Through service
APIs, a user can dynamically add :term:`Node` to and remove node from a
cluster, attach and detach policies, such as *creation policy*, *deletion
policy*, *load-balancing policy*, *scaling policy*, *health policy* etc.
Through integration with other OpenStack projects, users will be enabled to
manage deployments and orchestrations large-scale resource pools much easier.

Currently no other clustering service exists for OpenStack. The developers
believe cloud operators have a strong desire to create and operate resource
pools on OpenStack deployments. The *Heat* project provides a preliminary
support to resource groups but Heat team has achieved a consensus that
such kind of a service should stand on its own feet.

Senlin is designed to be capable of managing different types of objects. An
object's lifecycle is managed using :term:`Profile Type` implementations,
which are plugins that can be dynamically loaded by the service engine.

Components
~~~~~~~~~~

The developers are focusing on creating an OpenStack style project using
OpenStack design tenets, implemented in Python. We have started with a close
interaction with Heat project.

senlinclient
------------

The :program:`senlinclient` package provides a plugin for the openstackclient
tool so you have a command line interface to communicate with
the :program:`senlin-api` to manage clusters, nodes, profiles, policies,
actions and events. End developers could also use the Senlin REST API directly.

senlin-dashboard
----------------
The :program:`senlin-dashboard` is a Horizon plugin that provides a UI for
senlin.

senlin-api
----------

The :program:`senlin-api` component provides an OpenStack-native REST API that
processes API requests by sending them to the :program:`senlin-engine` over RPC.

senlin-engine
-------------

The :program:`senlin-engine`'s main responsibility is to create and orchestrate
the clusters, nodes, profiles and policies.


Installation
~~~~~~~~~~~~

You will need to make sure you have a suitable environment for deploying
Senlin. Please refer to :ref:`Installation <guide-install>` for detailed
instructions on setting up an environment to use the Senlin service.
