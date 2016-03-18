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


====================
Deletion Policy V1.0
====================

The deletion policy is designed to be enforced when a cluster's size is to be
shrinked.


Applicable Profiles
~~~~~~~~~~~~~~~~~~~

The policy is designed to handle any (``ANY``) profile types.


Actions Handled
~~~~~~~~~~~~~~~

The policy is capable of handling the following actions:

- ``CLUSTER_SCALE_IN``: an action that carries an optional integer value named
  ``count`` in its ``inputs``.

- ``CLUSTER_DEL_NODES``: an action that carries a list value named
  ``candidates`` in its ``inputs`` value.

- ``CLUSTER_RESIZE``: an action that carries various key-value pairs as
  arguments to the action in its ``inputs`` value.

The policy will be checked **BEFORE** any of the above mentioned actions is
executed.


Scenarios
~~~~~~~~~

Under different scenarios, the policy works by checking different properties
of the action.


S1: ``CLUSTER_DEL_NODES``
-------------------------

This is the simplest case. A action of ``CLUSTER_DEL_NODES`` carries a list of
UUIDs for the nodes to be removed from the cluster. The deletion policy steps
in before the actual deletion happens so to help determine the following
details:

- whether the nodes should be destroyed after being removed from the cluster;
- whether the nodes should be granted a grace period before being destroyed;
- whether the ``desired_capacity`` of the cluster in question should be
  reduced after node removal.

After the policy check, the ``data`` field is updated with contents similar to
the following example: 

::

  {
    "status": "OK",
    "reason": "Candidates generated",
    "deletion": {
       "count": 2,
       "candidates": ["<node-id-1>", "<node-id-2"],
       "destroy_after_deletion": true,
       "grace_period": 0
    }
  }


S2: ``CLUSTER_SCALE_IN`` without Scaling Policy
-----------------------------------------------

When the request is about scaling in the target cluster, the Senlin engine
expects that the action carries a ``count`` key in its ``inputs``. If the
``count`` key doesn't exist, it means the requester has no idea (or he/she
doesn't care) the number of nodes to remove. The decision is left to the
scaling policy (if any) or to the Senlin engine.

When there is no :doc:`scaling policy <scaling_v1>` attached to the cluster,
Senlin engine takes the liberty to assume that the expectation is to remove
1 node from the cluster. This is equivalent to the case when ``count`` is
specified as ``1``.

The policy then continues evaluate the cluster nodes to select ``count``
victim node(s) based on the ``criteria`` property of the policy. Finally it
updates the action's ``data`` field with the list of node candidates along
with other properties, as described in scenario **S1**.


S3: ``CLUSTER_SCALE_IN`` with Scaling Policy
--------------------------------------------

If there is a :doc:`scaling policy <scaling_v1>` attached to the cluster, that
policy will yield into the action's ``data`` property some contents similar to
the following example:

::

  {
    "deletion": {
       "count": 2
    }
  }

The senlin engine will use value from the ``deletion.count`` field in the
``data`` property as the number of nodes to remove from cluster. It selects
victim nodes from the cluster based on the ``criteria`` specified and then
updates the action's ``data`` property along with other properties, as
described in scenario **S1**.


S4: ``CLUSTER_RESIZE`` without Scaling Policy
---------------------------------------------

If there is no :doc:`scaling policy <scaling_v1>` attached to the cluster,
the deletion policy won't be able to find a ``deletion.count`` field in the
action's ``data`` property. It then checks the ``inputs`` property of the
action directly and generates a ``deletion.count`` field if the request turns
out to be a scaling-in operation. If the request is not a scaling-in
operation, the policy check aborts immediately.

After having determined the number of nodes to remove, the policy proceeds to
select victim nodes based on its ``criteria`` property value.  Finally it
updates the action's ``data`` field with the list of node candidates along
with other properties, as described in scenario **S1**.


S5: ``CLUSTER_RESIZE`` with Scaling Policy
------------------------------------------

In the case there is already a :doc:`scaling policy <scaling_v1>` attached to
the cluster, the scaling policy will be evaluated before the deletion policy,
so the policy works in the same way as described in scenario **S3**.


S6: Deletion across Multiple Availability Zones
-----------------------------------------------

When you have a :doc:`zone placement policy <zone_v1>` attached to
a cluster, the zone placement policy will decide in which availability zone(s)
new nodes will be placed and from which availability zone(s) old nodes should
be deleted to maintain an expected node distribution. Such a zone placement
policy will be evaluated before this deletion policy, according to its builtin
priority value.

When scaling in a cluster, a zone placement policy yields a decision into the
action's ``data`` property that looks like:

::

  {
    "deletion": {
       "count": 3,
       "zones": {
           "AZ-1": 2,
           "AZ-2": 1
       }
    }
  }

The above data indicate how many nodes should be deleted globally and how many
nodes should be removed from each availability zone. The deletion policy then
evaluates nodes from each availability zone to select specified number of
nodes as candidates. This selection process is also based on the ``criteria``
property of the deletion policy.

After the evaluation, the deletion policy completes by modifying the ``data``
property to something like:

::

  {
    "status": "OK",
    "reason": "Candidates generated",
    "deletion": {
       "count": 3,
       "candidates": ["node-id-1", "node-id-2", "node-id-3"]
       "destroy_after_deletion": true,
       "grace_period": 0
    }
  }

In the ``deletion.candidates`` list, two of the nodes are from availability
zone ``AZ-1``, one of the nodes is from availability zone ``AZ-2``.

S6: Deletion across Multiple Regions
------------------------------------

When you have a :doc:`region placement policy <region_v1>` attached
to a cluster, the region placement policy will decide to which region(s) new
nodes will be placed and from which region(s) old nodes should be deleted to
maintain an expected node distribution. Such a region placement policy will be
evaluated before this deletion policy, according to its builtin priority value.

When scaling in a cluster, a region placement policy yields a decision into
the action's ``data`` property that looks like:

::

  {
    "deletion": {
       "count": 3,
       "region": {
           "R-1": 2,
           "R-2": 1
       }
    }
  }

The above data indicate how many nodes should be deleted globally and how many
nodes should be removed from each region. The deletion policy then evaluates
nodes from each region to select specified number of nodes as candidates. This
selection process is also based on the ``criteria`` property of the deletion
policy.

After the evaluation, the deletion policy completes by modifying the ``data``
property to something like:

::

  {
    "status": "OK",
    "reason": "Candidates generated",
    "deletion": {
       "count": 3,
       "candidates": ["node-id-1", "node-id-2", "node-id-3"]
       "destroy_after_deletion": true,
       "grace_period": 0
    }
  }

In the ``deletion.candidates`` list, two of the nodes are from region ``R-1``,
one of the nodes is from region ``R-2``.
