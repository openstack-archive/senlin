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


============================
Documentation for Developers
============================

Overview
~~~~~~~~

Senlin is a **clustering service** for OpenStack clouds. It creates and
operates clusters of homogeneous objects exposed by other OpenStack services.
The goal is to make orchestration of collections of similar objects easier.

This document targets senlin contributors.


Understanding the Design
~~~~~~~~~~~~~~~~~~~~~~~~

.. toctree::
   :maxdepth: 1

   authorization
   profile
   cluster
   node
   policy
   action
   receiver
   testing
   plugin_guide
   api_microversion


Built-in Policy Types
~~~~~~~~~~~~~~~~~~~~~

Senlin provides some built-in policy types which can be instantiated and then
attached to your clusters. These policy types are designed to be orthogonal so
that each of them can be used independently. They are also expected to work
in a collaborative way to meet the needs of complicated usage scenarios.

.. toctree::
   :maxdepth: 1

   policies/affinity_v1
   policies/deletion_v1
   policies/load_balance_v1
   policies/region_v1
   policies/scaling_v1
   policies/zone_v1


API Documentation
~~~~~~~~~~~~~~~~~

Follow the link below for the Senlin API design document.

-  `OpenStack API Complete Reference - Clustering`_


Indices and tables
~~~~~~~~~~~~~~~~~~

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`


.. _`OpenStack API Complete Reference - Clustering`: http://developer.openstack.org/api-ref/clustering/
