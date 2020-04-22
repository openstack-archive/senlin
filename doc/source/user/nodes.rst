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


.. _ref-nodes:

=====
Nodes
=====

Concept
~~~~~~~

A :term:`Node` is a logical object managed by the Senlin service. A node can
be a member of at most one cluster at any time. A node can be an orphan node
which means it doesn't belong to any clusters. Senlin provides APIs and
command line supports to manage node's cluster membership. Please refer to
:ref:`ref-membership` for details.

A node has a ``profile_id`` property when created that specifies which
:term:`Profile` to use when creating a physical object that backs the node.
Please refer to :ref:`ref-profiles` for the creation and management of
profile objects.


Listing Nodes
~~~~~~~~~~~~~

To list nodes that are managed by the Senlin service, you will use the command
:command:`openstack cluster node list`. For example::

  $ openstack cluster node list
  +----------+--------+-------+--------+------------+-------------+...
  | id       | name   | index | status | cluster_id | physical_id |
  +----------+--------+-------+--------+------------+-------------+...
  | e1b39a08 | node1  | -1    | ACTIVE |            | 89ce0d2b    |
  | 57962220 | node-3 | -1    | ACTIVE |            | 3386e306    |
  | b28692a5 | stack1 |  1    | ACTIVE | 2b7e9294   | fdf028a6    |
  | 4be10a88 | stack2 |  2    | ACTIVE | 2b7e9294   | 7c87f545    |
  +----------+--------+-------+--------+------------+-------------+...

Note that some columns in the output table are *short ID* of objects. Senlin
command line use short IDs to save real estate on screen so that more useful
information can be shown on a single line. To show the *full ID* in the list,
you can add the option :option:`--full-id` to the command.


Sorting the List
----------------

You can specify the sorting keys and sorting direction when list nodes,
using the option :option:`--sort`. The :option:`--sort` option accepts a
string of format ``key1[:dir1],key2[:dir2],key3[:dir3]``, where the keys used
are node properties and the dirs can be one of ``asc`` and ``desc``. When
omitted, Senlin sorts a given key using ``asc`` as the default direction.

For example, the following command sorts the nodes using the ``status``
property in descending order::

  $ openstack cluster node list --sort status:desc

When sorting the list of nodes, you can use one of ``index``, ``name``,
``status``, ``init_at``, ``created_at`` and ``updated_at``.


Filtering the List
------------------

You can specify the option :option:`--cluster <CLUSTER>` to list nodes that
are members of a specific cluster. For example::

  $ openstack cluster node list --cluster c3
  +----------+---------+-------+--------+------------+-------------+...
  | id       | name    | index | status | cluster_id | physical_id |
  +----------+---------+-------+--------+------------+-------------+...
  | b28692a5 | stack1  |  1    | ACTIVE | 2b7e9294   | fdf028a6    |
  | 4be10a88 | stack2  |  2    | ACTIVE | 2b7e9294   | 7c87f545    |
  +----------+---------+-------+--------+------------+-------------+...

Besides these two options, you can add the option :option:`--filters
<K1=V1;K2=V2...>` to the command :command:`openstack cluster node list` to
specify keys (node property names) and values you want to filter the list.
The valid keys for filtering are ``name`` and ``status``. For example, the
command below filters the list by node status ``ACTIVE``::

  $ openstack cluster node list --filters status=ACTIVE


Paginating the List
-------------------

In case you have a large number of nodes, you can limit the number of nodes
returned from Senlin server each time, using the option :option:`--limit
<LIMIT>`. For example::

  $ openstack cluster node list --limit 1

Another option you can specify is the ID of a node after which you want to
see the returned list starts. In other words, you don't want to see those
nodes with IDs that is or come before the one you specify. You can use the
option :option:`--marker <ID>` for this purpose. For example::

  $ openstack cluster node list --marker 765385ed-f480-453a-8601-6fb256f512fc

With option :option:`--marker` and option :option:`--limit`, you will be able
to control how many node records you will get from each request.


Creating a Node
~~~~~~~~~~~~~~~

To create a node, you need to specify the ID or name of the profile to be
used. For example, the following example creates a node named ``test_node``
using a profile named ``pstack``::

  $ openstack cluster node create --profile pstack test_node
  +---------------+--------------------------------------+
  | Property      | Value                                |
  +---------------+--------------------------------------+
  | cluster_id    |                                      |
  | created_at    | None                                 |
  | data          | {}                                   |
  | dependents    | {}                                   |
  | details       | None                                 |
  | domain_id     | None                                 |
  | id            | 1984b5a0-9dd7-4dda-b1e6-e8c1f640598f |
  | index         | -1                                   |
  | init_at       | 2015-07-09T11:41:18                  |
  | location      | None                                 |
  | metadata      | {}                                   |
  | name          | test_node                            |
  | physical_id   | None                                 |
  | profile_id    | 9b127538-a675-4271-ab9b-f24f54cfe173 |
  | profile_name  | pstack                               |
  | project_id    | 333acb15a43242f4a609a27cb097a8f2     |
  | role          |                                      |
  | status        | INIT                                 |
  | status_reason | Initializing                         |
  | updated_at    | None                                 |
  | user_id       | 5e5bf8027826429c96af157f68dc9072     |
  +---------------+--------------------------------------+

When processing this request, Senlin engine will verify if the profile value
specified is a profile name, a profile ID or the short ID of a profile object.
If the profile is not found or multiple profiles found matching the value, you
will receive an error message.

Note that the ``index`` property of the new node is -1. This is because we
didn't specify the owning cluster for the node. To join a node to an existing
cluster, you can either use the :command:`openstack cluster member add`
command (:ref:`ref-membership`) after the node is created, or specify the
owning cluster upon node creation, as shown by the following example::

  $ openstack cluster node create --profile pstack --cluster c1 test_node

The command above creates a new node using profile ``pstack`` and makes it a
member of the cluster ``c1``, specified using the option :option:`--cluster`.
When a node becomes a member of a cluster, it will get a value for its
``index`` property that uniquely identifies itself within the owning cluster.

When the owning cluster is specified, Senlin engine will verify if the cluster
specified is referencing a profile that has the same :term:`Profile Type` as
that of the new node. If the profile types don't match, you will receive an
error message from the :command:`openstack cluster` command.

Another argument that could be useful when creating a new node is the option
:option:`--role <ROLE>`. The value could be used by a profile type
implementation to treat nodes differently. For example, the following command
creates a node with a ``master`` role::

  $ openstack cluster node create --profile pstack --cluster c1 \
      --role master master_node

A profile type implementation may check this role value when operating the
physical object that backs the node. It is okay for a profile type
implementation to ignore this value.

The last argument you can specify when creating a new node is the option
:option:`--metadata <K1=V1;K2=V2...>`. The value for this option is a list of
key-value pairs separated by a semicolon ('``;``'). These key-value pairs are
attached to the node and can be used for whatever purposes. For example::

  $ openstack cluster node create --profile pstack \
      --metadata owner=JohnWhite test_node


Showing Details of a Node
~~~~~~~~~~~~~~~~~~~~~~~~~

You can use the name, the ID or the "short ID" of a node to name a node for
show. The Senlin API and engine will verify if the identifier you specified
can uniquely identify a node. An error message will be returned if there is
no node matching the identifier or if more than one node matching it.

An example is shown below::

  $ openstack cluster node show test_node
  +---------------+--------------------------------------+
  | Field         | Value                                |
  +---------------+--------------------------------------+
  | cluster_id    | None                                 |
  | created_at    | 2015-07-09T11:41:20                  |
  | data          | {}                                   |
  | dependents    | {}                                   |
  | details       | {}                                   |
  | domain_id     | None                                 |
  | id            | 1984b5a0-9dd7-4dda-b1e6-e8c1f640598f |
  | index         | -1                                    |
  | init_at       | 2015-07-09T11:41:18                  |
  | location      | None                                 |
  | metadata      | {}                                   |
  | name          | test_node                            |
  | physical_id   | 0e444642-b280-4c88-8be4-76ad0d158dac |
  | profile_id    | 9b127538-a675-4271-ab9b-f24f54cfe173 |
  | profile_name  | pstack                               |
  | project_id    | 333acb15a43242f4a609a27cb097a8f2     |
  | role          | None                                 |
  | status        | ACTIVE                               |
  | status_reason | Creation succeeded                   |
  | updated_at    | None                                 |
  | user_id       | 5e5bf8027826429c96af157f68dc9072     |
  +---------------+--------------------------------------+

From the output, you can see the ``physical_id`` of a node (if it has been
successfully created). For different profile types, this value may be the
ID of an object that is of certain type. For example, if the profile type used
is "``os.heat.stack``", this means the Heat stack ID; if the profile type used
is "``os.nova.server``", it gives the Nova server ID.

An useful argument for the command :command:`openstack cluster node show` is
the option :option:`--details`. When specified, you will get the details about
the physical object that backs the node. For example::

  $ openstack cluster node show --details test_node


Checking a Node
~~~~~~~~~~~~~~~

Once a node has been created, you can use the name, the ID or the "short ID" of
a node to name a node for check. senlin-engine performs a profile-specific check
operation to get the latest status of the physical resource (for example a virtual
machine). If the virtual machine status is not ACTIVE, the node will be set to
ERROR status. For example::

  $ openstack cluster node check node-biQA3BOM


Recovering a Node
~~~~~~~~~~~~~~~~~
After a node has been created and running for a period of time, if the node goes
into ERROR status, you can use to try to restore the node to ACTIVE status, using
the :command:`openstack cluster node recover`. The restore operation will delete
the specified node and recreate it. For example::

  $ openstack cluster node recover node-biQA3BOM


Updating a Node
~~~~~~~~~~~~~~~

Once a node has been created, you can change its properties using the command
:command:`openstack cluster node update`. For example, to change the name of a
node, you can use the option :option:`--name` , as shown by the following
command::

  $ openstack cluster node update --name new_node_name old_node_name

Similarly, you can modify the ``role`` property of a node using the option
:option:`--role`. For example::

  $ openstack cluster node update --role slave master_node

You can change the metadata associated with a node using the option
:option:`--metadata`::

  $ openstack cluster node update --metadata version=2.1 my_node

Using the :command:`openstack cluster node update` command, you can change the
profile used by a node. The following example updates a node for switching to
use a different profile::

  $ openstack cluster node update --profile fedora21_server fedora20_server

Suppose the node ``fedora20_server`` is now using a profile of type
``os.nova.server`` where a Fedora 20 image is used, the command above will
initiate an upgrade to use a new profile with a Fedora 21 image.

Senlin engine will verify whether the new profile has the same profile type
with that of the existing one and whether the new profile has a well-formed
``spec`` property. If everything is fine, the engine will start profile update
process.


Adopting a Node
~~~~~~~~~~~~~~~

In Senlin service, we can adopt an existing resource as a node and create a
profile for this node. To adopt a node, you need to specify the resource
physical ID by setting :option:`--identity <identity>` and resource
profile_type name by setting :option:`--type <type>`. For example, the
following example adopts a server with ID
``1177c8e8-8472-4e9d-8f15-1d4866b85b8b`` as a node named ``test_adopt_node``::

  $ openstack cluster node adopt --identity \
            1177c8e8-8472-4e9d-8f15-1d4866b85b8b --type os.nova.server-1.0 \
            --name test_adopt_node
  +---------------+--------------------------------------+
  | Field         | Value                                |
  +---------------+--------------------------------------+
  | cluster_id    |                                      |
  | created_at    | 2017-08-16T07:52:50Z                 |
  | data          | {}                                   |
  | dependents    | {}                                   |
  | details       | None                                 |
  | domain_id     | None                                 |
  | id            | f88b1d7d-1e25-4362-987c-52f8aea26520 |
  | index         | -1                                   |
  | init_at       | 2017-08-16T07:52:50Z                 |
  | location      | None                                 |
  | metadata      | {}                                   |
  | name          | test_adopt_node                      |
  | physical_id   | 1177c8e8-8472-4e9d-8f15-1d4866b85b8b |
  | profile_id    | f9e5e3dd-d4f3-44a1-901e-351fa39e5801 |
  | profile_name  | prof-test_adopt_node                 |
  | project_id    | 138cf3f92bb3459da02363db8d53ac30     |
  | role          |                                      |
  | status        | ACTIVE                               |
  | status_reason | Node adopted successfully            |
  | updated_at    | None                                 |
  | user_id       | 67dc524bfb45492496c8ff7ecdedd394     |
  +---------------+--------------------------------------+

The :option:`--name <NAME>` is optional, if omitted, Senlin engine will
generate a random name start with ``node-`` for the node.

The option :option:`--role <ROLE>` could be used by a profile type
implementation to treat nodes differently. For example, the following command
adopts a server as a node with a ``master`` role::

  $ openstack cluster node adopt --identity \
            1177c8e8-8472-4e9d-8f15-1d4866b85b8b --type os.nova.server-1.0 \
            --name test_adopt_node --role master

The option :option:`--metadata <K1=V1;K2=V2...>` is a list of
key-value pairs separated by a semicolon ('``;``'). These key-value pairs are
attached to the node and can be used for whatever purposes. For example::

  $ openstack cluster node adopt --identity \
            1177c8e8-8472-4e9d-8f15-1d4866b85b8b --type os.nova.server-1.0 \
            --name test_adopt_node --metadata "key1=value1;key2=value2"

Another option :option:`--overrides <JSON>` support user to override
the node profile properties. For example, the following command can adopt a
server as a node and override the network properties in node's profile::

  $ openstack cluster node adopt --identity \
                1177c8e8-8472-4e9d-8f15-1d4866b85b8b \
                --type os.nova.server-1.0 \
                --override '{"networks":[{"network": "public"}]}'

The option :option:`--snapshot <SNAPSHOT>` is boolean type. If set, senlin
Senlin engine will create a snapshot for the resource before accept the
resource as a node.


Previewing a Node for Adoption
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

A resource can be previewed before getting adopted as a Senlin node using the
:command:`openstack cluster node adopt` command with option
:option:`--preview <PREVIEW>`. To preview a node, you need to specify the
resource physical ID by setting :option:`--identity <identity>` and resource
profile_type name by setting :option:`--type <type>`. For example::

  $ openstack cluster node adopt --preview \
                    --identity 1177c8e8-8472-4e9d-8f15-1d4866b85b8b \
                    --type os.nova.server-1.0
  +--------------+----------------------------------------------------------------------+
  | Field        | Value                                                                |
  +--------------+----------------------------------------------------------------------+
  | node_preview | +------------+-----------------------------------------------------+ |
  |              | | property   | value                                               | |
  |              | +------------+-----------------------------------------------------+ |
  |              | | properties | {                                                   | |
  |              | |            |   "name": "test0",                                  | |
  |              | |            |   "availability_zone": "nova",                      | |
  |              | |            |   "block_device_mapping_v2": [],                    | |
  |              | |            |   "image": "6232a7b9-8af1-4dce-8eb5-f2988a0e34bc",  | |
  |              | |            |   "key_name": "oskey",                              | |
  |              | |            |   "auto_disk_config": false,                        | |
  |              | |            |   "flavor": "1",                                    | |
  |              | |            |   "metadata": {},                                   | |
  |              | |            |   "networks": [                                     | |
  |              | |            |     {                                               | |
  |              | |            |       "network": "private"                          | |
  |              | |            |     }                                               | |
  |              | |            |   ],                                                | |
  |              | |            |   "security_groups": [                              | |
  |              | |            |     "default",                                      | |
  |              | |            |     "default"                                       | |
  |              | |            |   ],                                                | |
  |              | |            |   "config_drive": false                             | |
  |              | |            | }                                                   | |
  |              | | type       | os.nova.server                                      | |
  |              | | version    | 1.0                                                 | |
  |              | +------------+-----------------------------------------------------+ |
  +--------------+----------------------------------------------------------------------+

The option :option:`--overrides <JSON>` support user to override the node
profile properties. For example, the following command can adopt a server
as a node and override the network properties in node's profile::

  $ openstack cluster node adopt --preview --identity \
                1177c8e8-8472-4e9d-8f15-1d4866b85b8b \
                --type os.nova.server-1.0 \
                --override '{"networks":[{"network": "public"}]}'
  +--------------+----------------------------------------------------------------------+
  | Field        | Value                                                                |
  +--------------+----------------------------------------------------------------------+
  | node_preview | +------------+-----------------------------------------------------+ |
  |              | | property   | value                                               | |
  |              | +------------+-----------------------------------------------------+ |
  |              | | properties | {                                                   | |
  |              | |            |   "name": "test0",                                  | |
  |              | |            |   "availability_zone": "nova",                      | |
  |              | |            |   "block_device_mapping_v2": [],                    | |
  |              | |            |   "image": "6232a7b9-8af1-4dce-8eb5-f2988a0e34bc",  | |
  |              | |            |   "key_name": "oskey",                              | |
  |              | |            |   "auto_disk_config": false,                        | |
  |              | |            |   "flavor": "1",                                    | |
  |              | |            |   "metadata": {},                                   | |
  |              | |            |   "networks": [                                     | |
  |              | |            |     {                                               | |
  |              | |            |       "network": "public"                           | |
  |              | |            |     }                                               | |
  |              | |            |   ],                                                | |
  |              | |            |   "security_groups": [                              | |
  |              | |            |     "default",                                      | |
  |              | |            |     "default"                                       | |
  |              | |            |   ],                                                | |
  |              | |            |   "config_drive": false                             | |
  |              | |            | }                                                   | |
  |              | | type       | os.nova.server                                      | |
  |              | | version    | 1.0                                                 | |
  |              | +------------+-----------------------------------------------------+ |
  +--------------+----------------------------------------------------------------------+

The option :option:`--snapshot <SNAPSHOT>` is boolean type. If set, senlin
Senlin engine will create a snapshot for the resource before accept the
resource as a node.


Deleting a Node
~~~~~~~~~~~~~~~

A node can be deleted using the :command:`openstack cluster node delete`
command, for example::

  $ openstack cluster node delete my_node

Note that in this command you can use the name, the ID or the "short ID" to
specify the node you want to delete. If the specified criteria cannot match
any nodes, you will get a ``ResourceNotFound`` exception. If more than one
node matches the criteria, you will get a ``MultipleChoices`` exception.


See Also
~~~~~~~~

Below are links to documents related to node management:

- :doc:`Managing Profile Objects <profiles>`
- :doc:`Creating Clusters <clusters>`
- :doc:`Managing Cluster Membership <membership>`
- :doc:`Examining Actions <actions>`
- :doc:`Browsing Events <events>`
