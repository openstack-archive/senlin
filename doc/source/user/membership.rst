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


.. _guide-membership:

==================
Cluster Membership
==================

Concept
~~~~~~~

A :term:`Node` can belong to at most one :term:`Cluster` at any time. A node
is referred to as an *orphan node* when it doesn't belong to any cluster.

A node can be made a member of cluster when creation, or you can change the
cluster membership after the cluster and and the node have been created.


Listing Nodes in a Cluster
~~~~~~~~~~~~~~~~~~~~~~~~~~

Using the command :command:`cluster-node-list`, you can list the nodes that
are members of a specific cluster. For example, to list nodes in cluster
``c3``, you can use the following command::

  $ senlin cluster-node-list c3
  +----------+--------+-------+--------+-------------+---------------------+
  | id       | name   | index | status | physical_id | created_at          |
  +----------+--------+-------+--------+-------------+---------------------+
  | b28692a5 | stack1 | 1     | ACTIVE | fdf028a6    | 2015-07-07T05:23:40 |
  | 4be10a88 | stack2 | 2     | ACTIVE | 7c87f545    | 2015-07-07T05:27:54 |
  +----------+--------+-------+--------+-------------+---------------------+

You can use the name, the ID or the "short ID" of a cluster as the argument
for node listing. If the specified cluster identifier cannot match any cluster
or it matches more than one cluster, you will get an error message.

From the list, you can see the ``index``, ``status``, ``physical_id`` of each
node in this cluster. Note that the ``id`` field and the ``physical_id`` field
are shown as "short ID"s by default. If you want to see the full IDs, you can
specify the :option:`--full-id` (or :option:`-F`) option to indicate that::

  $ senlin cluster-node-list -F c3
  +------------...-+--------+-------+--------+-------------+-----------..-+
  | id             | name   | index | status | physical_id | created_at   |
  +------------...-+--------+-------+--------+-------------+-----------..-+
  | b28692a5-25... | stack1 | -1    | ACTIVE | fdf0...     | 2015-07-07.. |
  | 4be10a88-e3... | stack2 | -1    | ACTIVE | 7c87...     | 2015-07-07.. |
  +------------...-+--------+-------+--------+-------------+-----------..-+

In cases where you want to list nodes that have been soft-deleted, you can add
the option :option:`--show-deleted` (or :option:`-D`) for this purpose. For
example, the following command will list all nodes that were members of the
``webservers`` cluster, no matter the nodes are soft-deleted or not::

  $ senlin cluster-node-list -D webservers

If the cluster size is very large, you may want to list the nodes in pages.
This can be achieved by using the :option:`--marker` (or :option:`-m`) option
together with the :option:`--limit` (or :option:`-l`) option. The ``marker``
option value specifies a node ID after which you want the resulted list to
start; and the ``limit`` option value specifies the number of nodes you want
to include in the resulted list. For example, the following command lists the
nodes starting behind a specific node ID with the length of the list set to 10::

  $ senlin cluster-node-list -m b28692a5 -l 10 webservers

Another useful option for listing nodes is the :option:`--filters <FILTERS>`
(or :option:`-f <FILTERS>`) option. The option value accepts a string of
format "``K1=V1;K2=V2...``", where "``K1``" and "``K2``" are node properties
for checking, "``V1``" and "``V2``" are values for filtering. The acceptable
properties for filtering are ``name`` and ``status``. For example, the
following command lists cluster nodes from a cluster based on whether a node's
status is "``ACTIVE``"::

  $ senlin cluster-node-list -f status=ACTIVE webservers


Specify the Cluster When Creating a Node
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

There are several ways to make a node a member of a cluster. When creating a
node using command :command:`node-create`, you can specify the option
:option:`--cluster` (or :option:`-c`) to tell Senlin to which cluster the new
node belongs. Please refer to :ref:`guide-nodes` for detailed instructions.


Adding Node(s) to A Cluster
~~~~~~~~~~~~~~~~~~~~~~~~~~~

When you already have some nodes and some clusters, you can add some specified
nodes to a specified cluster using the command :command:`cluster-node-add`.
For example, the following command adds two nodes to a cluster::

  $ senlin cluster-node-add -n node3,node4 cluster1

You can use the name, the ID or the "short ID" to name the node(s) to be
added, you can also use the name, the ID or the "short ID" to specify the
cluster. When the identifiers you specify cannot match any existing nodes or
clusters respectively, you will receive an error message. If the identifier
provided matches more than one object, you will get an error message as well.

Before Senlin engine performs the cluster membership changes, it will verify
if the nodes to be added have the same :term:`profile type` with the target
cluster. If the profile types don't match, you will get an error message.

When nodes are added to a cluster, they will get new ``index`` property values
that can be used to uniquely identify them within the cluster.


Removing Node(s) from a Cluster
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The :program:`senlin` command line also provides command
:command:`cluster-node-del` to remove node(s) from a cluster. In this case,
you can use the name, the ID or the "short ID" to specify the node(s) and the
cluster. The identifier specified must uniquely identifies a node or a cluster
object, or else you will get an error message indicating that the request was
rejected. The following command removes two nodes from a cluster::

  $ senlin cluster-node-del -n node21,node22 webservers

When performing this operation, Senlin engine will check if the specified
nodes are actually members of the specified cluster. If any node from the
specified node list does not belong to the target cluster, you will get an
error message and the command fails.

When nodes are removed from a cluster, they will get their ``index`` property
reset to -1.


See Also
~~~~~~~~

Below are links to documents related to clusters and nodes:

- :doc:`Creating Clusters <clusters>`
- :doc:`Creating Nodes <nodes>`
