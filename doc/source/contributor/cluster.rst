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

========
Clusters
========

Clusters are first-class citizens in Senlin service design. A cluster is
defined as a collection of homogeneous objects. The "homogeneous" here means
that the objects managed (aka. Nodes) have to be instantiated from the same
"profile type".

A cluster can contain zero or more nodes. Senlin provides REST APIs for users
to create, retrieve, update, delete clusters. Using these APIs, a user can
manage the node membership of a cluster.

A cluster is owned by a user (the owner), and it is accessible from within the
Keystone project (tenant) which is the default project of the user.

A cluster has the following timestamps when instantiated:

- ``init_at``: the timestamp when a cluster object is initialized in the
  Senlin database, but the actual cluster creation has not yet started;
- ``created_at``: the timestamp when the cluster object is created, i.e.
  the ``CLUSTER_CREATE`` action has completed;
- ``updated_at``: the timestamp when the cluster was last updated.


Cluster Statuses
~~~~~~~~~~~~~~~~

A cluster can have one of the following statuses during its lifecycle:

- ``INIT``: the cluster object has been initialized, but not created yet;
- ``ACTIVE``: the cluster is created and providing service;
- ``CREATING``: the cluster creation action is still on going;
- ``ERROR``: the cluster is still providing services, but there are things
  going wrong that needs human intervention;
- ``CRITICAL``: the cluster is not operational, it may or may not be
  providing services as expected. Senlin cannot recover it from its current
  status. The best way to deal with this cluster is to delete it and then
  re-create it if needed.
- ``DELETING``: the cluster deletion is ongoing;
- ``WARNING``: the cluster is operational, but there are some warnings
  detected during past operations. In this case, human involvement is
  suggested but not required.
- ``UPDATING``: the cluster is being updated.

Along with the ``status`` property, Senlin provides a ``status_reason``
property for users to check what is the cause of the cluster's current status.

To avoid frequent databases accesses, a cluster object has a runtime data
property named ``rt`` which is a Python dictionary. The property caches the
profile referenced by the cluster, the list of nodes in the cluster and the
policies attached to the cluster. The runtime data is not directly visible to
users. It is merely a convenience for cluster operations.


Creating A Cluster
~~~~~~~~~~~~~~~~~~

When creating a cluster, the Senlin API will verify whether the request
carries a body with valid, sufficient information for the engine to complete
the creation job. The following fields are required in a map named ``cluster``
in the request JSON body:

- ``name``: the name of the cluster to be created;
- ``profile``: the name or ID or short-ID of a profile to be used;
- ``desired_capacity``: the desired number of nodes in the cluster, which is
  treated also as the initial number of nodes to be created.

The following optional fields can be provided in the ``cluster`` map in the
JSON request body:

- ``min_size``: the minimum number of nodes inside the cluster, default
  value is 0;
- ``max_size``: the maximum number of nodes inside the cluster, default
  value is -1, which means there is no upper limit on the number of nodes;
- ``timeout``: the maximum number of seconds to wait for the cluster to
  become ready, i.e. ``ACTIVE``.
- ``metadata``: a list of key-value pairs to be associated with the cluster.
- ``dependents``: A dict contains dependency information between nova server/
  heat stack cluster and container cluster. The container node's id will be
  stored in 'dependents' property of its host cluster.

The ``max_size`` and the ``min_size`` fields, when specified, will be checked
against each other by the Senlin API. The API also checks if the specified
``desired_capacity`` falls out of the range [``min_size``, ``max_size``]. If
any verification failed, a ``HTTPBadRequest`` exception is thrown and the
cluster creation request is rejected.

A cluster creation request is then forwarded to the Senlin RPC engine for
processing, where the engine creates an Action for the request and queues it
for any worker threads to execute. Once the action is queued, the RPC engine
returns the current cluster properties in a map to the API. Along with these
properties, the engine also returns the UUID of the Action that will do the
real job of cluster creation. A user can check the status of the action to
determine whether the cluster has been successfully completed or failed.


Listing Clusters
~~~~~~~~~~~~~~~~

Clusters in the current project can be queried using some query parameters.
None of these parameters is required. By default, the Senlin API will return
all clusters that are not deleted.

When listing clusters, the following query parameters can be specified,
individually or combined:

- ``filters``: a map containing key-value pairs for matching. Records that
  fail to match the criteria will be filtered out. The valid keys in this map
  include:

  * ``name``: name of clusters to list, can be a string or a list of strings;
  * ``status``: status of clusters, can be a string or a list of strings;

- ``limit``: a number that restricts the maximum number of records to be
  returned from the query. It is useful for displaying the records in pages
  where the page size can be specified as the limit.
- ``marker``: A string that represents the last seen UUID of clusters in
  previous queries. This query will only return results appearing after the
  specified UUID. This is useful for displaying records in pages.
- ``sort``: A string to enforce sorting of the results. It accepts a list of
  known property names of a cluster as sorting keys separated by commas. Each
  sorting key can optionally have either ``:asc`` or ``:desc`` appended to the
  key for controlling the sorting direction.
- ``global_project``: A boolean indicating whether cluster listing should be
  done in a tenant-safe way. When this value is specified as False (the
  default), only clusters from the current project that match the other
  criteria will be returned. When this value is specified as True, clusters
  that matching all other criteria would be returned, no matter in which
  project a cluster was created. Only a user with admin privilege is permitted
  to do a global listing.


Getting a Cluster
~~~~~~~~~~~~~~~~~

When a user wants to check the details about a specific cluster, he or she can
specify one of the following keys for query:

- cluster UUID: Clusters are queried strictly based on the UUID given. This is
  the most precise query supported.
- cluster name: Senlin allows multiple clusters to have the same name. It is
  user's responsibility to avoid name conflicts if needed. The output may be
  the details of a cluster if the cluster name is unique, or else Senlin will
  return a message telling users that multiple clusters found matching the
  specified name.
- short ID: Considering that UUID is a long string not so convenient to input,
  Senlin supports a short version of UUIDs for query. Senlin engine will use
  the provided string as a prefix to attempt a matching in the database. When
  the "ID" is long enough to be unique, the details of the matching cluster is
  returned, or else Senlin will return an error message indicating that more
  than one cluster matching the short ID have been found.

Senlin engine service will try the above three ways in order to find a match
in database.

In the returned result, Senlin injects a list of node IDs for nodes in the
cluster. It also injects the name of the profile used by the cluster. These
are all for user's convenience.


Updating A Cluster
~~~~~~~~~~~~~~~~~~

A cluster can be updated upon user's requests. In theory, all properties of a
cluster could be updated/changed. However, some update operations are light
-weight ones, others are heavy weight ones. This is because the semantics of
properties differ a lot from each other. Currently, cluster profile related
changes and cluster size related changes are heavy weight because they may
induce a chain of operations on the cluster. Updating other properties are
light weight operations.

In the JSON body of a ``cluster_update`` request, users can specify new values
for the following properties:

- ``name``: new cluster name;
- ``profile_id``: ID or name or short ID of a profile object to use;
- ``metadata``: a list of key-value pairs to be associated with the cluster,
  this dict will be merged with the existing key-value pairs based on keys.
- ``desired_capacity``: new *desired* size for the cluster;
- ``min_size``: new lower bound for the cluster size;
- ``max_size``: new upper bound for the cluster size.
- ``timeout``: new timeout value for the specified cluster.
- ``profile_only``: a boolean value indicating whether cluster will be only
  updated with profile.


Update Cluster's Profile
------------------------

When ``profile_id`` is specified, the request will be interpreted as a
wholistic update to all nodes across the cluster. The targeted use case is to
do a cluster wide system upgrade. For example, replacing glance images used by
the cluster nodes when new kernel patches have been applied or software
defects have been fixed.

When receiving such an update request, the Senlin engine will check if the new
profile referenced does exist and whether the new profile has the same profile
type as that of the existing profile. Exceptions will be thrown if any
verification has failed and thus the request is rejected.

After the engine has validated the request, an Action of ``CLUSTER_UPDATE`` is
created and queued internally for execution. Later on, when a worker thread
picks up the action for execution, it will first lock the whole cluster and
mark the cluster status as ``UPDATING``. It will then fork ``NODE_UPDATE``
actions per node inside the cluster, which are in turn queued for execution.
Other worker threads will pick up the node level update action for execution
and mark the action as completed/failed. When all these node level updates are
completed, the ``CLUSTER_UPDATE`` operation continues and marks the cluster as
``ACTIVE`` again.

Senlin also provides a parameter ``profile_only`` for this action, so that any
newly created nodes will use the new profile, but existing nodes should not be
changed.

The cluster update operation may take a long time to complete, depending on
the response time from the underlying profile operations. Note also, when
there is a update policy is attached to the cluster and enabled, the update
operation may be split into several batches so that 1) there is a minimum
number of nodes remained in service at any time; 2) the pressure on the
underlying service is controlled.


Update Cluster Size Properties
------------------------------

When either one of the ``desired_capacity``, ``min_size`` and ``max_size``
property is specified in the ``CLUSTER_UPDATE`` request, it may lead to a
resize operation on the cluster.

The Senlin API will do a preliminary validation upon the new property values.
For example, if both ``min_size`` and ``max_size`` are specified, they have to
be integers and the value for ``max_size`` is greater than the value for
``min_size``, unless the value of ``max_size`` is -1 which means the upper
bound of cluster size is unlimited.

When the request is then received by the Senlin engine, the engine first
retrieves the cluster properties from the database and do further
cross-verifications between the new property values and the current values.
For example, it is treated as an invalid request if a user has specified value
for ``min_size`` but no value for ``max_size``, however the new ``min_size``
is greater than the existing ``max_size`` of the cluster. In this case, the
user has to provide a valid ``max_size`` to override the existing value, or
he/she has to lower the ``min_size`` value so that the request becomes
acceptable.

Once the cross-verification has passed, Senlin engine will calculate the new
``desired_capacity`` and adjust the size of the cluster if deemed necessary.
For example, when the cluster size is below the new ``min_size``, new nodes
will be created and added to the cluster; when the cluster size is above the
new ``max_size``, some nodes will be removed from the cluster. If the
``desired_capacity`` is set and the property value falls between the new range
of cluster size, Senlin tries resize the cluster to the ``desired_capacity``.

When the size of the cluster is adjusted, Senlin engine will check if there
are relevant policies attached to the cluster so that the engine will add
and/or remove nodes in a predictable way.


Update Other Cluster Properties
-------------------------------

The update to other cluster properties is relatively straightforward. Senlin
engine simply verifies the data types when necessary and override the existing
property values in the database.

Note that in the cases where multiple properties are specified in a single
``CLUSTER_UPDATE`` request, some will take a longer time to complete  than
others. Any mixes of update properties are acceptable to the Senlin API and
the engine.


Cluster Actions
~~~~~~~~~~~~~~~

A cluster object supports the following asynchronous actions:

- ``add_nodes``: add a list of nodes into the target cluster;
- ``del_nodes``: remove the specified list of nodes from the cluster;
- ``replace_nodes``: replace the specified list of nodes in the cluster;
- ``resize``: adjust the size of the cluster;
- ``scale_in``: explicitly shrink the size of the cluster;
- ``scale_out``: explicitly enlarge the size of the cluster.
- ``policy_attach``: attach a policy object to the cluster;
- ``policy_detach``: detach a policy object from the cluster;
- ``policy_update``: modify the settings of a policy that is attached to the
  cluster.

The ``scale_in`` and the ``scale_out`` actions are subject to change in future.
We recommend using the unified ``CLUSTER_RESIZE`` action for cluster size
adjustments.

Software or a user can trigger a ``cluster_action`` API to issue an action
for Senlin to perform. In the JSON body of these requests, Senlin will verify
if the top-level key contains *one* of the above actions. When no valid action
name is found or more than one action is specified, the API will return error
messages to the caller and reject the request.


Adding Nodes to a Cluster
-------------------------

Senlin API provides the ``add_nodes`` action for user to add some existing
nodes into the specified cluster. The parameter for this action is interpreted
as a list in which each item is the UUID, name or short ID of a node.

When receiving an ``add_nodes`` action request, the Senlin API only validates
if the parameter is a list and if the list is empty. After this validation,
the request is forwarded to the Senlin engine for processing.

The Senlin engine will examine nodes in the list one by one and see if any of
the following conditions is true. Senlin engine rejects the request if so.

- Any node from the list is not in ``ACTIVE`` state?
- Any node from the list is still member of another cluster?
- Any node from the list is not found in the database?
- Number of nodes to add is zero?

When this phase of validation succeeds, the request is translated into a
``CLUSTER_ADD_NODES`` builtin action and queued for execution. The engine
returns to the user an action UUID for checking.

When the action is picked up by a worker thread for execution, Senlin checks
if the profile type of the nodes to be added matches that of the cluster.
Finally, a number of ``NODE_JOIN`` action is forked and executed from the
``CLUSTER_ADD_NODES`` action. When ``NODE_JOIN`` actions complete, the
``CLUSTER_ADD_NODES`` action returns with success.

In the cases where there are load-balancing policies attached to the cluster,
the ``CLUSTER_ADD_NODES`` action will save the list of UUIDs of the new nodes
into the action's ``data`` field so that those policies could update the
associated resources.


Deleting Nodes from a Cluster
-----------------------------

Senlin API provides the ``del_nodes`` action for user to delete some existing
nodes from the specified cluster. The parameter for this action is interpreted
as a list in which each item is the UUID, name or short ID of a node.

When receiving a ``del_nodes`` action request, the Senlin API only validates
if the parameter is a list and if the list is empty. After this validation,
the request is forwarded to the Senlin engine for processing.

The Senlin engine will examine nodes in the list one by one and see if any of
the following conditions is true. Senlin engine rejects the request if so.

- Any node from the list cannot be found from the database?
- Any node from the list is not member of the specified cluster?
- Number of nodes to delete is zero?

When this phase of validation succeeds, the request is translated into a
``CLUSTER_DEL_NODES`` builtin action and queued for execution. The engine
returns to the user an action UUID for checking.

When the action is picked up by a worker thread for execution, Senlin forks a
number of ``NODE_DELETE`` actions and execute them asynchronously. When all
forked actions complete, the ``CLUSTER_DEL_NODES`` returns with a success.

In the cases where there are load-balancing policies attached to the cluster,
the ``CLUSTER_DEL_NODES`` action will save the list of UUIDs of the deleted
nodes into the action's ``data`` field so that those policies could update the
associated resources.

If a deletion policy with hooks property is attached to the cluster, the
``CLUSTER_DEL_NODES`` action will create the ``CLUSTER_DEL_NODES`` actions
in ``WAITING_LIFECYCLE_COMPLETION`` status which does not execute them.  It
also sends the lifecycle hook message to the target specified in the
deletion policy.  If the complete lifecylcle API is called for a
``CLUSTER_DEL_NODES`` action, it will be executed.  If all the
``CLUSTER_DEL_NODES`` actions are not executed before the hook timeout
specified in the deletion policy is reached, the remaining
``CLUSTER_DEL_NODES`` actions are moved into ``READY`` status and scheduled
for execution.  When all actions complete, the ``CLUSTER_DEL_NODES``
returns with a success.

Note also that by default Senlin won't destroy the nodes that are deleted
from the cluster. It simply removes the nodes from the cluster so that they
become orphan nodes.
Senlin also provides a parameter ``destroy_after_deletion`` for this action
so that a user can request the deleted node(s) to be destroyed right away,
instead of becoming orphan nodes.


Replacing Nodes in a Cluster
----------------------------

Senlin API provides the ``replace_nodes`` action for user to replace some existing
nodes in the specified cluster. The parameter for this action is interpreted
as a dict in which each item is the node-pair{OLD_NODE:NEW_NODE}. The key OLD_NODE
is the UUID, name or short ID of a node to be replaced, and the value NEW_NODE is
the UUID, name or short ID of a node as replacement.

When receiving a ``replace_nodes`` action request, the Senlin API only validates
if the parameter is a dict and if the dict is empty. After this validation,
the request is forwarded to the Senlin engine for processing.

The Senlin engine will examine nodes in the dict one by one and see if all of
the following conditions is true. Senlin engine accepts the request if so.

- All nodes from the list can be found from the database.
- All replaced nodes from the list are the members of the specified cluster.
- All replacement nodes from the list are not the members of any cluster.
- The profile types of all replacement nodes match that of the specified
  cluster.
- The statuses of all replacement nodes are ACTIVE.

When this phase of validation succeeds, the request is translated into a
``CLUSTER_REPLACE_NODES`` builtin action and queued for execution. The engine
returns to the user an action UUID for checking.

When the action is picked up by a worker thread for execution, Senlin forks a
number of ``NODE_LEAVE`` and related ``NODE_JOIN`` actions, and execute them
asynchronously. When all forked actions complete, the ``CLUSTER_REPLACE_NODES``
returns with a success.


Resizing a Cluster
------------------

In addition to the ``cluster_update`` request, Senlin provides a dedicated API
for adjusting the size of a cluster, i.e. ``cluster_resize``. This operation
is designed for the auto-scaling and manual-scaling use cases.

Below is a list of API parameters recognizable by the Senlin API when parsing
the JSON body of a ``cluster_resize`` request:

- ``adjustment_type``: type of adjustment to be performed where the value
  should be one of the followings:

  * ``EXACT_CAPACITY``: the adjustment is about the targeted size of the
    cluster;
  * ``CHANGE_IN_CAPACITY``: the adjustment is about the number of nodes to be
    added or removed from the cluster and this is the default setting;
  * ``CHANGE_IN_PERCENTAGE``: the adjustment is about a relative percentage of
    the targeted cluster.

  This field is mandatory.
- ``number``: adjustment number whose value will be interpreted base on the
  value of ``adjustment_type``. This field is mandatory.
- ``min_size``: the new lower bound for the cluster size;
- ``max_size``: the new upper bound for the cluster size;
- ``min_step``: the minimum number of nodes to be added or removed when the
  ``adjustment_type`` is set to ``CHANGE_IN_PERCENTAGE`` and the absolute
  value computed is less than 1;
- ``strict``: a boolean value indicating whether the service should do a
  best-effort resizing operation even if the request cannot be fully met.

For example, the following request is about increasing the size of the cluster
by 20% and Senlin can try a best-effort if the calculated size is greater than
the upper limit of the cluster size:

::

  {
    "adj_type": "CHANGE_IN_PERCENTAGE",
    "number": "20",
    "strict": False,
  }

When Senlin API receives a ``cluster_resize`` request, it first validates the
data type of the values and the sanity of the value collection. For example,
you cannot specify a ``min_size`` greater than the current upper bound (i.e.
the ``max_size`` property of the cluster) if you are not providing a new
``max_size`` that is greater than the ``min_size``.

After the request is forwarded to the Senlin engine, the engine will further
validates the parameter values against the targeted cluster. When all
validations pass, the request is converted into a ``CLUSTER_RESIZE`` action
and queued for execution. The API returns the cluster properties and the UUID
of the action at this moment.

When executing the action, Senlin will analyze the request parameters and
determine the operations to be performed to meet user's requirement. The
corresponding cluster properties are updated before the resize operation
is started.


Scaling in/out a Cluster
------------------------

As a convenience method, Senlin provides the ``scale_out`` and the ``scale_in``
action API for clusters. With these two APIs, a user can request a cluster to
be resized by the specified number of nodes.

The ``scale_out`` and the ``scale_in`` APIs both take a parameter named
``count`` which is a positive integer. The integer parameter is optional, and
it specifies the number of nodes to be added or removed if provided. When it
is omitted from the request JSON body, Senlin engine will check if the cluster
has any relevant policies attached that will decide the number of nodes to be
added or removed respectively. The Senlin engine will use the outputs from
these policies as the number of nodes to create (or delete) if such policies
exist. When the request does contain a ``count`` parameter and there are
policies governing the scaling arguments, the ``count`` parameter value may
be overridden/ignored.

When a ``scale_out`` or a ``scale_in`` request is received by the Senlin
engine, a ``CLUSTER_SCALE_OUT`` or a ``CLUSTER_SCALE_IN`` action is then
created and queued for execution after some validation of the parameter value.

A worker thread picks up the action and execute it. The worker will check if
there are outputs from policy checkings. For ``CLUSTER_SCALE_OUT`` actions,
the worker checks if the policies checked has left a ``count`` key in the
dictionary named ``creation`` from the action's runtime ``data`` attribute.
The worker will use such a ``count`` value for node creation. For a
``CLUSTER_SCALE_OUT`` action, the worker checks if the policies checked has
left a ``count`` key in the dictionary named ``deletion`` from the action's
runtime ``data`` attribute. The worker will use such a ``count`` value for
node deletion.

Note that both ``scale_out`` and ``scale_in`` actions will adjust the
``desired_capacity`` property of the target cluster.


Cluster Policy Bindings
~~~~~~~~~~~~~~~~~~~~~~~

Senlin API provides the following action APIs for managing the binding
relationship between a cluster and a policy:

- ``policy_attach``: attach a policy to a cluster;
- ``policy_detach``: detach a policy from a cluster;
- ``policy_update``: update the properties of the binding between a cluster
  and a policy.


Attaching a Policy to a Cluster
-------------------------------

Once a policy is attached (bound) to a cluster, it will be enforced when
related actions are performed on that cluster, unless the policy is
(temporarily) disabled on the cluster.

When attaching a policy to a cluster, the following properties can be
specified:

- ``enabled``: a boolean indicating whether the policy should be enabled on
  the cluster once attached. Default is True. When specified, it will override
  the default setting for the policy.

Upon receiving the ``policy_attach`` request, the Senlin engine will perform
some validations then translate the request into a ``CLUSTER_ATTACH_POLICY``
action and queue the action for execution. The action's UUID is then returned
to Senlin API and finally the requestor.

When the engine executes the action, it will try find if the policy is already
attached to the cluster. This checking was not done previously because the
engine must ensure that the cluster has been locked before this checking, or
else there might be race conditions.

The engine calls the policy's ``attach`` method when attaching the policy and
record the binding into database if the ``attach`` method returns a positive
response.

Currently, Senlin does not allow two policies of the same type to be attached
to the same cluster. This constraint may be relaxed in future, but for now, it
is checked and enforced before a policy gets attached to a cluster.

Policies attached to a cluster are cached at the target cluster as part of its
runtime ``rt`` data structure. This is an optimization regarding DB queries.


Detaching a Policy from a Cluster
---------------------------------

Once a policy is attached to a cluster, it can be detached from the cluster at
user's request. The only parameter required for the ``policy_detach`` action
API is ``policy_id``, which can be the UUID, the name or the short ID of the
policy.

Upon receiving a ``policy_detach`` request, the Senlin engine will perform
some validations then translate the request into a ``CLUSTER_DETACH_POLICY``
action and queue the action for execution. The action's UUID is then returned
to Senlin API and finally the requestor.

When the Senlin engine executes the ``CLUSTER_DETACH_POLICY`` action, it will
try find if the policy is already attached to the cluster. This checking was
not done previously because the engine must ensure that the cluster has been
locked before this checking, or else there might be race conditions.

The engine calls the policy's ``detach`` method when detaching the policy from
the cluster and then removes the binding record from database if the
``detach`` method returns a True value.

Policies attached to a cluster are cached at the target cluster as part of its
runtime ``rt`` data structure. This is an optimization regarding DB queries.
The ``CLUSTER_DETACH_POLICY`` action will invalidate the cache when detaching
a policy from a cluster.


Updating a Policy on a Cluster
------------------------------

When a policy is attached to a cluster, there are some properties pertaining
to the binding. These properties can be updated as long as the policy is still
attached to the cluster. The properties that can be updated include:

- ``enabled``: a boolean value indicating whether the policy should be enabled
  or disabled. There are cases where some policies have to be temporarily
  disabled when other manual operations going on.

Upon receiving the ``policy_update`` request, Senlin API performs some basic
validations on the parameters passed.

Senlin engine translates the ``policy_update`` request into an action
``CLUSTER_UPDATE_POLICY`` and queue it for execution. The UUID of the action
is then returned to Senlin API and eventually the requestor.

During execution of the ``CLUSTER_UPDATE_POLICY`` action, Senlin engine
simply updates the binding record in the database and returns.
