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

.. _tutorial-receivers:

======================
Working with Receivers
======================

Receivers are the event sinks associated to senlin clusters so that when
certain events (or alarms) are seen by a monitoring software, the software can
notify the senlin clusters of those events (or alarms). When senlin receives
those notifications, it can automatically trigger some predefined operations
with preset parameter values.

Creating a Receiver
~~~~~~~~~~~~~~~~~~~

To create a receiver, you need to specify the target cluster and the target
action to be triggered in future. For example, the following command creates
a receiver that will trigger the ``CLUSTER_SCALE_IN`` operation on the target
cluster:

.. code-block:: console

  $ senlin receiver-create -c mycluster -a CLUSTER_SCALE_IN w_scale_in

The output from the command will be something like shown below:

.. code-block:: console

  $ senlin receiver-create -c mycluster -a CLUSTER_SCALE_IN w_scale_in
  +------------+-------------------------------------------------------------------------+
  | Property   | Value                                                                   |
  +------------+-------------------------------------------------------------------------+
  | action     | CLUSTER_SCALE_IN                                                        |
  | actor      | {                                                                       |
  |            |   "trust_id": "1bc958f5780b4ad38fb6583701a9f39b"                        |
  |            | }                                                                       |
  | channel    | {                                                                       |
  |            |   "alarm_url": "http://node1:8778/v1/webhooks/5dacde18-.../trigger?V=1" |
  |            | }                                                                       |
  | cluster_id | 7fb3d988-3bc1-4539-bd5d-3f72e8d6e0c7                                    |
  | created_at | 2016-05-23T01:36:39                                                     |
  | domain     | None                                                                    |
  | id         | 5dacde18-661e-4db4-b7a8-f2a6e3466f98                                    |
  | name       | w_scale_in                                                              |
  | params     | None                                                                    |
  | project    | eee0b7c083e84501bdd50fb269d2a10e                                        |
  | type       | webhook                                                                 |
  | updated_at | None                                                                    |
  | user       | ab79b9647d074e46ac223a8fa297b846                                        |
  +------------+-------------------------------------------------------------------------+

From the output of the ``receiver-create`` command, you can see:

- There is a ``type`` property whose value is set to ``webhook`` which is the
  only receiver type senlin supports today.
- There is a ``channel`` property which contains an ``alarm_url`` key. The
  value of the ``alarm_url`` is the endpoint for your to post a request.

Triggering a Receiver with CURL
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Once we have a receiver created, you can test it by triggering the specified
action using tools like ``curl``.

.. code-block:: console

  $ curl -X POST http://node1:8778/v1/webhooks/5dacde18-661e-4db4-b7a8-f2a6e3466f98/trigger?V=1 

After a while, you can check that the cluster has been shrinked by 1 node.

For more details about managing receivers, please check the
:doc:`Receivers <../user/receivers>` section in the
:doc:`User References <../user/index>` documentation.

Triggering a Receiver with an Aodh Alarm
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. TODO::

  Check aodh command line and figure out how to create alarms.
