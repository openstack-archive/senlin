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

.. _tutorial-autoscaling:

===========================
Making Your Cluster Elastic
===========================

Creating Receivers
~~~~~~~~~~~~~~~~~~

Suppose you want a cluster to scale out by one node each time an event occurs,
you can create a receiver for this task:

.. code-block:: console

  $ openstack cluster receiver create --type webhook --cluster mycluster \
      --action CLUSTER_SCALE_OUT so_receiver_1
  +------------+---------------------------------------------------+
  | Field      | Value                                             |
  +------------+---------------------------------------------------+
  | action     | CLUSTER_SCALE_OUT                                 |
  | actor      | {                                                 |
  |            |   "trust_id": "b2b8fd71c3d54f67ac14e5851c0117b8"  |
  |            | }                                                 |
  | channel    | {                                                 |
  |            |   "alarm_url": "<WEBHOOK_URL>"                    |
  |            | }                                                 |
  | cluster_id | 30d7ef94-114f-4163-9120-412b78ba38bb              |
  | created_at | 2017-02-08T02:08:13Z                              |
  | domain_id  | None                                              |
  | id         | 5722a2b0-1f5f-4a82-9c08-27da9982d46f              |
  | location   | None                                              |
  | name       | so_receiver_1                                     |
  | params     | {}                                                |
  | project_id | 36d551c0594b4cc99d1bbff8bf202ec3                  |
  | type       | webhook                                           |
  | updated_at | None                                              |
  | user_id    | 9563fa29642a4efdb1033bf8aab07daa                  |
  +------------+---------------------------------------------------+


The command above creates a receiver named ``so_receiver_1`` which can be used
to initiate a ``CLUSTER_SCALE_OUT`` action on the cluster ``my_cluster``. From
the output of this command, you will find an ``alarm_url`` value from the
``channel`` property. This will be the URL for you to trigger the scaling
operation.

.. note::

  You are expected to treat the ``alarm_url`` value as a secret. Any person or
  software which knows this value will be able to trigger the scaling operation
  on your cluster. This may not be what you wanted.

The default type of receiver would be "``webhook``". You may choose to create
a "``message``" type of receiver if you have the zaqar messaging service
installed. For more details, please refer to :ref:`ref-receivers`.

Triggering Scaling
~~~~~~~~~~~~~~~~~~

Once you have received a channel from the created receiver, you can use it to
trigger the associated action on the specified cluster. The simplest way to
do this is to use the :command:`curl` command as shown below:

.. code-block:: console

  $ curl -X POST <WEBHOOK_URL>

Once the above request is received by the senlin-api, your cluster will be
scaled out by one node. In other words, a new node is created into the
cluster.


Creating Scaling Policies
~~~~~~~~~~~~~~~~~~~~~~~~~

Senlin provides some builtin policy types to control how a cluster will be
scaled when a relevant request is received. A scaling request can be a simple
``CLUSTER_SCALE_OUT`` or ``CLUSTER_SCALE_IN`` action which can accept an
optional ``count`` argument; it can be a more complex ``CLUSTER_RESIZE``
action which can accept more arguments for fine-tuning the scaling behavior.

In the absence of such arguments (which is not uncommon if you are using a
3rd party monitoring software which doesn't have the intelligence to decide
each and every argument), you can always use scaling policies for this
purpose.

Below is a sample YAML file (:file:`examples/policies/scaling_policy.yaml`)
used for creating a scaling policy object::

  type: senlin.policy.scaling
  version: 1.0
  properties:
    event: CLUSTER_SCALE_IN
    adjustment:
      type: CHANGE_IN_CAPACITY
      number: 2
      min_step: 1
      best_effort: True
      cooldown: 120

To create a policy object, you can use the following command:

.. code-block:: console

  $ openstack cluster policy create \
    --spec-file examples/policies/scaling_policy.yaml \
    policy1
  +------------+--------------------------------------+
  | Field      | Value                                |
  +------------+--------------------------------------+
  | created_at | 2016-12-08T02:41:30.000000           |
  | data       | {}                                   |
  | domain_id  | None                                 |
  | id         | 3ca962c5-68ce-4293-9087-c73964546223 |
  | location   | None                                 |
  | name       | policy1                              |
  | project_id | 36d551c0594b4cc99d1bbff8bf202ec3     |
  | spec       | {                                    |
  |            |   "version": 1.0,                    |
  |            |   "type": "senlin.policy.scaling",   |
  |            |   "properties": {                    |
  |            |     "adjustment": {                  |
  |            |       "min_step": 1,                 |
  |            |       "cooldown": 120,               |
  |            |       "best_effort": true,           |
  |            |       "number": 1,                   |
  |            |       "type": "CHANGE_IN_CAPACITY"   |
  |            |     },                               |
  |            |     "event": "CLUSTER_SCALE_IN"      |
  |            |   }                                  |
  |            | }                                    |
  | type       | senlin.policy.scaling-1.0            |
  | updated_at | None                                 |
  | user_id    | 9563fa29642a4efdb1033bf8aab07daa     |
  +------------+--------------------------------------+

The next step to enforce this policy on your cluster is to attach the policy
to it, as shown below:

.. code-block:: console

  $ openstack cluster policy attach --policy policy1 mycluster
  Request accepted by action: 89626141-0999-4e76-9795-a86c4cfd531f

  $ openstack cluster policy binding list mycluster
  +-----------+-------------+---------------------------+------------+
  | policy_id | policy_name | policy_type               | is_enabled |
  +-----------+-------------+---------------------------+------------+
  | 3ca962c5  | policy1     | senlin.policy.scaling-1.0 | True       |
  +-----------+-------------+---------------------------+------------+

In future, when your cluster is about to be scaled in (no matter the request
comes from a user or a software or via a receiver), the scaling policy attached
will help determine 1) how many nodes to be removed, 2) whether the scaling
operation should be done on a best effort basis, 3) for how long the cluster
will not respond to further scaling requests, etc.

For more information on using scaling policy, you can refer to
:ref:`ref-scaling-policy`.
