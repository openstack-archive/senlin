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

.. _verify:

========================
Verify Your Installation
========================

Verify operation of the Cluster service.


.. note::

   Perform these commands on the controller node.

#. Source the ``admin`` tenant credentials:

   .. code-block:: console

      $ . admin-openrc

#. List service components to verify successful launch and
   registration of each process:

   .. code-block:: console

      $ openstack cluster build info
      +--------+---------------------+
      | Field  | Value               |
      +--------+---------------------+
      | api    | {                   |
      |        |   "revision": "1.0" |
      |        | }                   |
      | engine | {                   |
      |        |   "revision": "1.0" |
      |        | }                   |
      +--------+---------------------+

You are ready to begin your journey (aka. adventure) with Senlin, now.
