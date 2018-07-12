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

=======
Actions
=======

An action is an abstraction of some logic that can be executed by a worker
thread. Most of the operations supported by Senlin are executed asynchronously,
which means they are queued into database and then picked up by certain worker
thread for execution.

Currently, Senlin only supports builtin actions listed below. In future, we
may evolve to support user-defined actions (UDAs). A user-defined action may
carry a Shell script to be executed on a target Nova server, or a Heat
SoftwareConfig to be deployed on a stack, for example. The following builtin
actions are supported at the time of this design:

- ``CLUSTER_CREATE``: An action for creating a cluster;
- ``CLUSTER_DELETE``: An action for deleting a cluster;
- ``CLUSTER_UPDATE``: An action for updating a cluster;
- ``CLUSTER_ADD_NODES``: An action for adding existing nodes to a cluster;
- ``CLUSTER_DEL_NODES``: An action for removing nodes from a cluster;
- ``CLUSTER_REPLACE_NODES``: An action for replacing nodes in a cluster;
- ``CLUSTER_RESIZE``: An action for adjusting the size of a cluster;
- ``CLUSTER_SCALE_IN``: An action to shrink the size of a cluster by removing
  nodes from the cluster;
- ``CLUSTER_SCALE_OUT``: An action to extend the size of a cluster by creating
  new nodes using the ``profile_id`` of the cluster;
- ``CLUSTER_ATTACH_POLICY``: An action to attach a policy to a cluster;
- ``CLUSTER_DETACH_POLICY``: An action to detach a policy from a cluster;
- ``CLUSTER_UPDATE_POLICY``: An action to update the properties of a binding
  between a cluster and a policy;
- ``CLUSTER_CHECK``: An action for checking a cluster and execute ``NODE_CHECK``
  for all its nodes;
- ``CLUSTER_RECOVER``: An action for recovering a cluster and execute
  ``NODE_RECOVER`` for all the nodes in 'ERROR' status;
- ``NODE_CREATE``: An action for creating a new node;
- ``NODE_DELETE``: An action for deleting an existing node;
- ``NODE_UPDATE``: An action for updating the properties of an existing node;
- ``NODE_JOIN``: An action for joining a node to an existing cluster;
- ``NODE_LEAVE``: An action for a node to leave its current owning cluster;
- ``NODE_CHECK``: An action for checking a node to see if its physical node is
  'ACTIVE' and update its status with 'ERROR' if not;
- ``NODE_RECOVER``: An action for recovering a node;


Action Properties
~~~~~~~~~~~~~~~~~

An action has the following properties when created:

- ``id``: a globally unique ID for the action object;
- ``name``: a string representation of the action name which might be
  generated automatically for actions derived from other operations;
- ``context``: a dictionary that contains the calling context that will be
  used by the engine when executing the action. Contents in this dictionary
  may contain sensitive information such as user credentials.
- ``action``: a text property that contains the action body to be executed.
  Currently, this property only contains the name of a builtin action. In
  future, we will provide a structured definition of action for UDAs.
- ``target``: the UUID of an object (e.g. a cluster, a node or a policy) to
  be operated;
- ``cause``: a string indicating the reason why this action was created. The
  purpose of this property is for the engine to check whether a new lock should
  be acquired before operating an object. Valid values for this property
  include:

  * ``RPC Request``: this indicates that the action was created upon receiving
    a RPC request from Senlin API, which means a lock is likely needed;
  * ``Derived Action``: this indicates that the action was created internally
    as part of the execution path of another action, which means a lock might
    have been acquired;

- ``owner``: the UUID of a worker thread that currently "owns" this action and
  is responsible for executing it.
- ``interval``: the interval (in seconds) for repetitive actions, a value of 0
  means that the action won't be repeated;
- ``start_time``: timestamp when the action was last started. This field is
  provided for action execution timeout detection;
- ``stop_time``: timestamp when the action was stopped. This field is provided
  for measuring the execution time of an action;
- ``timeout``: timeout (in seconds) for the action execution. A value of 0
  means that the action does not have a customized timeout constraint, though
  it may still have to honor the system wide ``default_action_timeout``
  setting.
- ``status``: a string representation of the current status of the action. See
  subsection below for detailed status definitions.
- ``status_reason``: a string describing the reason that has led the action to
  its current status.
- ``control``: a string for holding the pending signals such as ``CANCEL``,
  ``SUSPEND`` or ``RESUME``.
- ``inputs``: a dictionary that provides inputs to the action when executed;
- ``outputs``: a dictionary that captures the outputs (including error
  messages) from the action execution;
- ``depends_on``: a UUID list for the actions that must be successfully
  completed before the current action becomes ``READY``. An action cannot
  become ``READY`` when this property is not an empty string.
- ``depended_by``: a UUID list for the actions that depends on the successful
  completion of current action. When the current action is completed with a
  success, the actions listed in this property will get notified.
- ``created_at``: the timestamp when the action was created;
- ``updated_at``: the timestamp when the action was last updated;

*TODO*: Add support for scheduled action execution.

*NOTE*: The default value of the ``default_action_timeout`` is 3600 seconds.


The Action Data Property
------------------------

An action object has a property named ``data`` which is used for saving policy
decisions. This property is a Python dict for different policies to save and
exchange policy decision data.

Suppose we have a scaling policy, a deletion policy and a load-balancing
policy attached to the same cluster. By design, when an ``CLUSTER_SCALE_IN``
action is picked up for execution, the following sequence will happen:

1) When the action is about to be executed, the worker thread checks all
   policies that have registered a "pre_op" on this action type.
2) Based on the built-in priority setting, the "pre_op" of the scaling policy
   is invoked, and the policy determines the number of nodes to be deleted.
   This decision is saved to the action's ``data`` property in the following
   format:

::

   "deletion": {
     "count": 2
   }

3) Based on the built-in priority setting, the deletion policy is evaluated
   next. When the "pre_op" method of the deletion policy is invoked, it first
   checks the ``data`` property of the action where it finds out the number of
   nodes to delete. Then it will calculate the list of candidates to be
   deleted using its selection criteria (e.g. ``OLDEST_FIRST``). Finally, it
   saves the list of candidate nodes to be deleted to the ``data`` property of
   the action, in the following format:

::

   "deletion": {
     "count": 2,
     "candidates": ["1234-4567-9900", "3232-5656-1111"]
   }

4) According to the built-in priority setting, the load-balancing policy is
   evaluated last.  When invoked, its "pre_op" method checks the ``data``
   property of the action and finds out the candidate nodes to be removed from
   the cluster. With this information, the method removes the nodes from the
   load-balancer maintained by the policy.

5) The action's ``execute()`` method is now invoked and it removes the nodes
   as given in its ``data`` property, updates the cluster's last update
   timestamp, then returns.

From the example above, we can see that the ``data`` property of an action
plays a critical role in policy checking and enforcement. To avoid losing of
the in-memory ``data`` content during service restart, Senlin persists the
content to database whenever it is changed.

Note that there are policies that will write to the ``data`` property of a
node for a similar reason. For example, a placement policy may decide where a
new node should be created. This information is saved into the ``data``
property of a node. When a profile is about to create a node, it is supposed
to check this property and enforce it. For a Nova server profile, this means
that the profile code will inject ``scheduler_hints`` to the server instance
before it is created.


Action Statuses
~~~~~~~~~~~~~~~

An action can be in one of the following statuses during its lifetime:

- ``INIT``: Action object is being initialized, not ready for execution;
- ``READY``: Action object can be picked up by any worker thread for
  execution;
- ``WAITING``: Action object has dependencies on other actions, it may
  become ``READY`` only when the dependents are all completed with successes;
- ``WAITING_LIFECYCLE_COMPLETION``: Action object is a node deletion that is
  awaiting lifecycle completion.  It will become ``READY`` when complete
  lifecycle API is called or the lifecycle hook timeout in deletion policy is
  reached.
- ``RUNNING``: Action object is being executed by a worker thread;
- ``SUSPENDED``: Action object is suspended during execution, so the only way
  to put it back to ``RUNNING`` status is to send it a ``RESUME`` signal;
- ``SUCCEEDED``: Action object has completed execution with a success;
- ``FAILED``: Action object execution has been aborted due to failures;
- ``CANCELLED``: Action object execution has been aborted due to a ``CANCEL``
  signal.

Collectively, the ``SUCCEEDED``, ``FAILED`` and ``CANCELLED`` statuses are all
valid action completion status.


The ``execute()`` Method and Return Values
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Each subclass of the base ``Action`` must provide an implementation of the
``execute()`` method which provides the actual logic to be invoked by the
generic action execution framework.

Senlin defines a protocol for the execution of actions. The ``execute()``
method should always return a tuple ``<RES>, <REASON>`` where the ``<RES>``
indicates whether the action procedure execution was successful and the
``<REASON>`` provides an explanation of the result, e.g. the error message
when the execution has failed. In this protocol, the action procedure can
return one of the following values:

- ``OK``: the action execution was a complete success;
- ``ERROR``: the action execution has failed with error messages;
- ``RETRY``: the action execution has encountered some resource competition
  situation, so the recommendation is to re-start the action if possible;
- ``CANCEL``: the action has received a ``CANCEL`` signal and thus has aborted
  its execution;
- ``TIMEOUT``: the action has detected a timeout error when performing some
  time consuming jobs.

When the return value is ``OK``, the action status will be set to
``SUCCEEDED``; when the return value is ``ERROR`` or ``TIMEOUT``, the action
status will be set to ``FAILED``; when the return value is ``CANCEL``, the
action status will be set to ``CANCELLED``; finally, when the return value is
``RETRY``, the action status is reset to ``READY``, and the current worker
thread will release its lock on the action so that other threads can pick it
up when resources permit.


Creating An Action
~~~~~~~~~~~~~~~~~~

Currently, Senlin actions are mostly generated from within the Senlin engine,
either due to a RPC request, or due to another action's execution.

In future, Senlin plans to support user-defined actions (UDAs). Senlin API will
provide API for creating an UDA and invoking an action which can be an UDA.


Listing Actions
~~~~~~~~~~~~~~~

Senlin provides an ``action_list`` API for users to query the action objects
in the Senlin database. Such a query request can be accompanied with the
following query parameters in the query string:

- ``filters``: a map that will be used for filtering out records that fail to
  match the criteria. The recognizable keys in the map include:

  * ``name``: the name of the actions where the value can be a string or a
    list of strings;
  * ``target``: the UUID of the object targeted by the action where the value
    can be a string or a list of strings;
  * ``action``: the builtin action for matching where the value can be a
    string or a list of strings;

- ``limit``: a number that restricts the maximum number of action records to be
  returned from the query. It is useful for displaying the records in pages
  where the page size can be specified as the limit.
- ``marker``: A string that represents the last seen UUID of actions in
  previous queries. This query will only return results appearing after the
  specified UUID. This is useful for displaying records in pages.
- ``sort``: A string to enforce sorting of the results. It accepts a list of
  known property names of an action as sorting keys separated by commas. Each
  sorting key can optionally have either ``:asc`` or ``:desc`` appended to the
  key for controlling the sorting direction.


Getting An Action
~~~~~~~~~~~~~~~~~

Senlin API provides the ``action_show`` API call for software or a user to
retrieve a specific action for examining its details. When such a query
arrives at the Senlin engine, the engine will search the database for the
``action_id`` specified.

User can provide the UUID, the name or the short ID of an action as the
``action_id`` for query. The Senlin engine will try each of them in sequence.
When more than one action matches the criteria, an error message is returned
to user, or else the details of the action object is returned.


Signaling An Action
~~~~~~~~~~~~~~~~~~~

When an action is in ``RUNNING`` status, a user can send signals to it. A
signal is actually a word that will be written into the ``control`` field of
the ``action`` table in the database.

When an action is capable of handling signals, it is supposed to check its
``control`` field in the DB table regularly and abort execution in a graceful
way. An action has the freedom to check or ignore these signals. In other
words, Senlin cannot guarantee that a signal will have effect on any action.

The currently supported signal words are:

- ``CANCEL``: this word indicates that the target action should cancel its
  execution and return when possible;
- ``SUSPEND``: this word indicates that the target action should suspend its
  execution when possible. The action doesn't have to return. As an
  alternative, it can sleep waiting on a ``RESUME`` signal to continue its
  work;
- ``RESUME``: this word indicates that the target action, if suspended, should
  resume its execution.

The support to ``SUSPEND`` and ``RESUME`` signals are still under development.
