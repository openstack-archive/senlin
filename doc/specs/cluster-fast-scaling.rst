..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

====================
Cluster Fast Scaling
====================

The URL of launchpad blueprint:

https://blueprints.launchpad.net/senlin/+spec/add-attribute-fast-scaling-to-cluster

The major function of senlin is managing clusters, change the capacity of
cluster use scale out and scale in operation. Generally a single scaling
operation will cost tens of seconds, even a few minutes in extreme cases.
It's a long time for actual production environment, so we need to improve
senlin for fast scaling.

Rather than improve the performance of hardware or optimize code, a better way
is to create some standby nodes while create a new cluster. When cluster need
to change the capacity immediately or replace some nodes in 'error' state to
'active' state nodes, add nodes form standby nodes to cluster, or remove error
nodes from cluster and add active nodes from standby nodes to cluster.

To make cluster scaling fast, the spec proposes to extend senlin for create
standby nodes and improve scaling operation.


Problem description
===================

Before real scaling a cluster, senlin need to do many things, the slowest
process is to create or delete a node.

Use Cases
---------

If senlin support fast scaling, the follow cases will be possible:

- Change the capacity of cluster immediately, no longer waiting for creating
or deleting nodes.

- Replace the error nodes from cluster immediately, improve high availability
for cluster.

- Improve the situation that scaling many times in a short time.

Proposed change
===============

1. Add a new attribute 'fast_scaling' in metadata to cluster, with the
attribute set, senlin will create standby nodes when create a new cluster.
The number of standby nodes could be specify, but sum of standby nodes and
nodes in cluster should less than max size of the cluster.

2. Revise cluster create and cluster delete operation for support new attr,
delete standby nodes when delete a cluster.

3. Revise scale out and scale in operation, with the new attribute set, add
nodes form standby nodes to cluster or remove nodes from cluster to standby
nodes first.

4. Revise health policy, check the state of standby nodes and support replace
error nodes to active nodes from standby nodes.

5. Revise deletion policy, delete nodes or remove nodes to standby nodes when
perform deletion operation.

Alternatives
------------

Any other ideas of fast scale a cluster.

Data model impact
-----------------

None

REST API impact
---------------

None

Security impact
---------------

None

Notifications impact
--------------------

None

Other end user impact
---------------------

None

Performance Impact
------------------

The standby nodes will claimed some resources. We should control the number
of standby nodes in a reasonable range.

Other deployer impact
---------------------

None

Developer impact
----------------

None


Implementation
==============

Assignee(s)
-----------

chohoor(Hongbin Li) <chohoor@gmail.com>

Work Items
----------

Depends on the design plan.


Dependencies
============

None


Testing
=======

Need unit tests.


Documentation Impact
====================

Documentation about api and operation should be update.


References
==========

None


History
=======

None
