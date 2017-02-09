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

.. _ref-scenario-affinity:

======================
Managing Node Affinity
======================

When deploying multiple nodes running identical instances of the same service
(or application) for the sake of load-balancing or high-availability, it is
very likely you don't want all nodes deployed onto the same physical machine.
However, when you have a cluster with some nodes playing one role (e.g.
Application Server) and other nodes playing another role (.e.g. Database),
you may want to collocate these nodes onto the same physical machine so that
inter-node communication can be faster.

To meet these intra-cluster node collocation requirements, you have different
choices.


Use Server Group in Profile
~~~~~~~~~~~~~~~~~~~~~~~~~~~

For the purpose of managing cluster node affinity, you may choose to create
a *server group* by invoking nova command line, e.g.:

::

  $ openstack server group create sg01 --policy affinity
  +--------------+------+------------+---------+---------------+---------+----------+
  | Id           | Name | Project Id | User Id | Policies      | Members | Metadata |
  +--------------+------+------------+---------+---------------+---------+----------+
  | 54a88567-... | sg01 | ...        | ...     | [u'affinity'] | []      | {}       |
  +--------------+------+------------+---------+---------------+---------+----------+

Then when you create a nova server profile, you can input the name of the
server group into the ``scheduler_hints`` property as shown below:

::

  $ cat web_cluster.yaml
  type: os.nova.server
  version: 1.0
  properties:
    name: web_server

    <... other properties go here ...>

    scheduler_hints:
      group: sg01

Later, when you create a cluster using this profile, the server nodes will be
booted on the same physical host if possible. In other words, the affinity
is managed directly by the nova compute service. If there are no physical
hosts satisfying the constraints, node creation requests will fail.


Use Same-Host or Different-Host in Profile
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

When adding nodes to an existing cluster, the new nodes can reference a
different profile object of the same profile type (i.e. ``os.nova.server``).
If a new node is expected to be launched on the same/different host from a
set of server nodes, you can specify the constraint as a ``scheduler_hints``
as well.

Suppose you have two server nodes in a cluster with UUID "UUID1" and "UUID2"
respectively, you can input the scheduling constraints in a profile as shown
below:

::

  $ cat standalone_server.yaml
  type: os.nova.server
  version: 1.0
  properties:
    name: web_server

    <... other properties go here ...>

    scheduler_hints:
      different_host:
        - UUID1
        - UUID2

When adding a node that uses this profile into the cluster, the node creation
either fails (e.g. no available host found) or the node is created
successfully on a different host from the specified server nodes.

Similarly, you can replace the ``different_host`` key above by ``same_host``
to instruct that the new node collocated with the specified existing node(s).


Managing Affinity using Affinity Policy
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Another option to manage node affinity is to use the affinity policy
(see :doc:`Affinity Policy <../user/policy_types/affinity>`). By creating and
attaching an affinity policy to a cluster, you can still control how nodes
are distributed relative to the underlying hosts. See the above link for usage
of the policy.


See Also
~~~~~~~~

* :doc:`Managing Policies <../user/policies>`
* :doc:`Builtin Policy - Affinity Policy <../user/policy_types/affinity>`
