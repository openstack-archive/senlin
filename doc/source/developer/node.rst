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

Nodes
=====

A node is a logical entity managed by the Senlin service. Each node can belong
to at most one cluster. A node that does not belong to any cluster can be
referred to as an "orphan" node.


---------------
Node Properties
---------------

There are some common properties that are defined for all nodes. The following
properties are always available on a node:

- ``profile_id``: ID of the profile from which the node is created.
- ``cluster_id``: When a node is a member of a cluster, the ``cluster_id``
  value indicates the ID of the owning cluster. For an orphan node, this
  property is empty.
- ``name``: The name of a node doesn't have to be unique even in the scope of
  the owning cluster (if there is one). For nodes created by Senlin service
  upon policy enforcement or when performing certain actions, Senlin engine
  will generate names for them automatically.
- ``index``: Each node has an ``index`` value which is unique in the scope of
  its owning cluster. The value is used to uniquely identify the node inside
  a cluster. For orphan nodes, the ``index`` value will be -1.
- ``role``: Each node in a cluster may have a role to play. The value of this
  property is a string that specifies the role a node plays in the owning
  cluster. Each profile type may support different set of roles.
- ``user``: ID of the user who is the creator (owner) of the node.
- ``project``: ID of the Keystone project in which the node was created.
- ``domain``: ID of the Keystone domain in which the node was created.
- ``init_time``: The timestamp when the node object was initialized.
- ``created_time``: The timestamp when the node was created.
- ``updated_time``: The timestamp when last time the node was updated.
- ``deleted_time``: The timestamp when the cluster is deleted. Once this
  property is set to a non-empty value, the cluster is regarded as deleted.
- ``metadata``: A list of key-value pairs that are associated with the node.
- ``physical_id``: The UUID of the physical object that backs this node. The
  property value is empty if there is no physical objects associated with it.
- ``status``: A string indicating the current status of the node.
- ``status_reason``: A string describing the reason why the node transited to
  its current status.

In addition to the above properties, when a node is retrieved and shown to the
user, Senlin provides a pseudo-property named ``profile_name`` for user's
convenience.


------------------
Cluster Membership
------------------

A prerequisite for a node to become a member of a cluster is that the node
must share the same profile type with the cluster. When adding nodes to an
existing cluster, Senlin engine will check if the profile types actually
match.

It is *NOT* treated as an error that a node has a different profile
(identified by the profile object's ID) from the cluster. The profile
referenced by the cluster can be interpreted as the 'desired' profile, while
the profile referenced by individual nodes can be treated as the 'actual'
profile(s). When the cluster scales out, new nodes will use the 'desired'
profile referenced by the cluster. When existing nodes are added to an
existing cluster, the existing nodes may have different profile IDs from the
cluster. In this case, Senlin will not force an unncecessary profile update to
the nodes.


---------------
Creating A Node
---------------

When receiving a request to create a node, Senlin API checks if any required
fields are missing and whether there are invalid values specified to some
fields. The following fields are required for a node creation request:

- ``name``: Name of the node to be created;
- ``profile_id``: ID of the profile to be used for creating the backend
  physical object.

Optionally, the request can contain the following fields:

- ``cluster_id``: When specified, the newly created node will become a
  member of the specified cluster. Otherwise, the new node will be an orphan
  node. The ``cluster_id`` provided can be a name of a cluster, the UUID of a
  cluster or the short ID of a cluster.
- ``role``: A string value specifying the role the node will play inside the
  cluster.
- ``metadata``: A list of key-value pairs to be associated with the node.


-------------
Listing Nodes
-------------

Nodes in the current project can be queried/listed using some query parameters.
None of these parameters is required. By default, the Senlin API will return
all nodes that are not deleted.

When listing nodes, the following query parameters can be specified,
individually or combined:

- ``filters``: a map containing key-value pairs that will be used for matching
  node records. Records that fail to match this criteria will be filtered out.
  The following strings are valid as filter keys:

  * ``name``: name of nodes to list, can be a string or a list of strings;
  * ``status``: status of nodes, can be a string or a list of strings;

- ``cluster_id``: A string specifying the name, the UUID or the short ID of a
  cluster for which the nodes are to be listed.
- ``limit``: a number that restricts the maximum number of records to be
  returned from the query. It is useful for displaying the records in pages
  where the page size can be specified as the limit.
- ``marker``: A string that represents the last seen UUID of stacks in previous
  queries. This query will only return results appearing after the
  specified UUID. This is useful for displaying records in pages.
- ``sort_dir``: A string to enforce sorting of the results. It can accept
  either ``asc`` or ``desc`` as its value.
- ``sort_keys``: A string or a list of strings where each string gives a node
  property name used for sorting.
- ``show_deleted``: A boolean indicating whether deleted nodes should be
  included in the results. The default is False.
- ``show_nested``: A boolean indicating whether nested clusters should be
  included in the results. The default is True. This feature is yet to be
  supported.
- ``global_project``: A boolean indicating whether node listing should be done
  in a tenant safe way. When this value is specified as False (the default),
  only nodes from the current project that match the other criteria will be
  returned. When this value is specified as True, nodes that matching all other
  criteria would be returned, no matter in which project the node was created.
  Only a user with admin privilege is permitted to do a global listing.

**NOTE**: The ``sort_keys`` and ``sort_dir`` parameters are deprecating. In
future, sorting parameters will be specified in a more generic way as
suggested by the API working group.

--------------
Getting A Node
--------------

When a user wants to check the details about a specific node, he or she can
specify one of the following values for query:

- Node UUID: Query is performed strictly based on the UUID value given. This
  is the most precise query supported.
- Node name: Senlin allows multiple nodes to have the same name. It is user's
  responsibility to avoid name conflicts if needed. The output is the details
  of a node if the node name is unique, otherwise Senlin will return a message
  telling users that multiple nodes found matching this name.
- short ID: Considering that UUID is a long string not so convenient to input,
  Senlin supports a short version of UUIDs for query. Senlin engine will use
  the provided string as a prefix to attemp a matching in the database. When
  the "ID" is long enough to be unique, the details of the matching node is
  returned, or else Senlin will return an error message indicating that
  multiple nodes were found matching the specified short ID.

Senlin engine service will try the above three ways in order to find a match
in database.

In addition to the key for query, a user can provide an extra boolean option
named ``show_details``.  When this option is set, Senlin service will retrieve
the properties about the physical object that backs the node. For example, for
a Nova server, this information will contain the IP address allocated to the
server, along with other useful information.

In the returned result, Senlin injects the name of the profile used by the
node for the user's convenience.


---------------
Updating A Node
---------------

Some node properties are updatable after the node has been created. These
properties include:

- ``name``: Name of node as seen by the user;
- ``role``: The role that is played by the node in its owning cluster;
- ``metadata``: The key-value pairs attached to the node;
- ``profile_id``: The ID of the profile used by the node.

Note that update of ``profile_id`` is different from the update of other
properties in that it may take time to complete. When receiving a request to
update the profile used by a node, the Senlin engine creates an Action that
is executed asynchronously by a worker thread.

When validating the node update request, Senlin rejects requests that attempt
to change the profile type used by the node.


---------------
Deleting A Node
---------------

A node can be deleted no matter if it is a member of a cluster or not. Node
deletion is handled asynchronously in Senlin. When the Senlin engine receives
a request, it will create an Action to be executed by a worker thread.


------------------
Cluster Membership
------------------

Senlin service provides APIs for users to add a node to a cluster or remove a
node from a cluster. From a node's perspective, it means a node can "join" an
existing cluster or "leave" from its owning cluster.

Upon receiving the ``node_join`` request, the Senlin API checks if the target
cluster does exists and whether the node and the cluster share the same profile
type. After the request passes these validations, it is transformed into an
internal Action object and persisted into Senlin database. When receiving a
``node_leave`` request, the Senlin API only checks if the node does exists.

When the ``NODE_JOIN`` action is executed, the node's ``cluster_id`` property
is set to the UUID of the cluster and its ``index`` property will be assigned
with a value that can uniquely identify the node in the cluster.

Similarly, when a ``NODE_LEAVE`` action is executed, the node's ``cluster_id``
property is set to empty, and its ``index`` property is set to -1.

Both a ``NODE_JOIN`` and a ``NODE_LEAVE`` actoin will be propagated to the
profile layer so that the profile object has an opportunity to perform
additional operations over the physical object that backs the node.
