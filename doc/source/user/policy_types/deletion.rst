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

.. _ref-deletion-policy:

===============
Deletion Policy
===============

The deletion policy is provided to help users control the election of victim
nodes when a cluster is about to be shrank. In other words, when the size of
a cluster is to be decreased, which node(s) should be removed first.

Currently, this policy is applicable to clusters of all profile types and it
is enforced when the cluster's size is about to be reduced.

Properties
~~~~~~~~~~

.. schemaprops::
  :package: senlin.policies.deletion_policy.DeletionPolicy

Sample
~~~~~~

Below is a typical spec for a deletion policy:

.. literalinclude :: /../../examples/policies/deletion_policy.yaml
  :language: yaml

The valid values for the "``criteria`` property include:

- ``OLDEST_FIRST``: always select node(s) which were created earlier than
  other nodes.

- ``YOUNGEST_FIRST``: always select node(s) which were created recently
  instead of those created earlier.

- ``OLDEST_PROFILE_FIRST``: compare the profile used by each individual nodes
  and select the node(s) whose profile(s) were created earlier than others.

- ``RANDOM``: randomly select node(s) from the cluster for deletion. This is
  the default criteria if omitted.

.. NOTE::

  There is an implicit rule (criteria) when electing victim nodes. Senlin
  engine always rank those nodes which are not in ACTIVE state or which are
  marked as tainted before others.

There are more several actions that can trigger a deletion policy. Some of
them may already carry a list of candidates to remove, e.g.
``CLUSTER_DEL_NODES`` or ``NODE_DELETE``; others may only carry a number of
nodes to remove, e.g. ``CLUSTER_SCALE_IN`` or ``CLUSTER_RESIZE``. For actions
that already have a list of candidates, the deletion policy will respect the
action inputs. The election of victims only happens when no such candidates
have been identified.


Deletion vs Destroy
~~~~~~~~~~~~~~~~~~~

There are cases where you don't want the node(s) removed from a cluster to be
destroyed. Instead, you prefer them to become "orphan" nodes so that in future
you can quickly add them back to the cluster without having to create new
nodes.

If this is your situation, you may want to set ``destroy_after_deletion`` to
``false``. Senlin engine won't delete the node(s) after removing them from the
cluster.

The default behavior is to delete (destroy) the node(s) after they are
deprived of their cluster membership.


Grace Period
~~~~~~~~~~~~

Another common scenario is to grant a node a period of time for it to shutdown
gracefully. Even if a node doesn't have a builtin logic to perform a graceful
shutdown, granting them some extra time may still help ensure the resources
they were using have been properly released.

The default value for ``grace_period`` property is 0, which means the node
deletion happens as soon as it is removed from the cluster. You can customize
this value according to your need. Note that the grace period will be granted
to all node(s) deleted. When setting this value to a large number, be sure
it will not exceed the typical timeout value for action execution. Or else the
node deletion will be a failure.


Reduce Desired Capacity or Not
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

In most cases, users would anticipate the "desired_capacity" of a cluster be
reduced when there are nodes removed from it. Since the victim selection
algorithm always pick nodes in non-ACTIVE status over ACTIVE ones, you can
actually remove erroneous nodes by taking advantage of this rule.

For example, there are 4 nodes in a cluster and 2 of them are known to be in
inactive status. You can use the command :command:`openstack cluster members
del` to remove the bad nodes. If you have a deletion policy attached to the
cluster, you get a chance to tell the Senlin engine that you don't want to
change the capacity of the cluster. Instead, you only want the bad nodes
removed. With the help of other cluster health related commands, you can
quickly recover the cluster to a healthy status. You don't have to change the
desired capacity of the cluster to a smaller value and then change it back.

If this is your use case, you can set ``reduce_desired_capacity`` to ``false``
in the policy spec. The cluster's desired capacity won't be changed after
cluster membership is modified.


Lifecycle Hook
~~~~~~~~~~~~~~

If there is a need to receive notification of a node deletion, you can
specify a lifecycle hook in the deletion policy:

.. code-block:: yaml

  type: senlin.policy.deletion
  version: 1.1
  properties:
    hooks:
      type: 'zaqar'
      timeout: 120
      params:
        queue: 'my_queue'

The valid values for the ``type`` are:

- ``zaqar``: send message to zaqar queue.  The name of the zaqar must be
  specified in ``queue`` property.

- ``webhook``: send message to webhook URL.  The URL of the webhook must be
  specified in ``url`` property.

``timeout`` property specifies the number of seconds to wait before the
actual node deletion happens.  This timeout can be preempted by calling
complete lifecycle hook API.

.. NOTE::

  Hooks of type ``webhook`` will be supported in a future version.  Currently
  only hooks of type ``zaqar`` are supported.


Deleting Nodes Across Regions
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

With the help of :ref:`ref-region-policy`, you will be able to distribute
a cluster's nodes into different regions as instructed. However, when you are
removing nodes from more than one regions, the same distribution rule has to
be respected as well.

When there is a region placement policy in effect, the deletion policy will
first determine the number of nodes to be removed from each region. Then in
each region, the policy performs a victim election based on the criteria you
specified in the policy spec.


Deleting Nodes Across Availability Zones
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Similarly, when there is a zone placement policy attached to the cluster in
question, nodes in the cluster may get distributed across a few availability
zones based on a preset algorithm.

The deletion policy, when triggered, will first determine the number for nodes
to be removed from each availability zone. Then it proceeds to elect victim
nodes based on the criteria specified in the policy spec within each
availability zone.
