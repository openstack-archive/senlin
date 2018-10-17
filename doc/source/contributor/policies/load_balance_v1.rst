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


==========================
Load Balancing Policy V1.1
==========================

This policy is designed to enable senlin clusters to leverage the Neutron
LBaaS V2 features so that workloads can be distributed across nodes in a
reasonable manner.

.. schemaspec::
    :package: senlin.policies.lb_policy.LoadBalancingPolicy


Actions Handled
~~~~~~~~~~~~~~~

The policy is capable of handling the following actions:

- ``CLUSTER_ADD_NODES``: an action that carries a list of node IDs for the
  nodes (servers) to be added into the cluster.

- ``CLUSTER_DEL_NODES``: an action that carries a list of node IDs for the
  nodes (servers) to be removed from the cluster.

- ``CLUSTER_SCALE_IN``: an action that carries an optional integer value named
  ``count`` in its ``inputs``.

- ``CLUSTER_SCALE_OUT``: an action that carries an optional integer value
  named ``count`` in its ``inputs``.

- ``CLUSTER_RESIZE``: an action that carries some additional parameters that
  specifying the details about the resize request, e.g. ``adjustment_type``,
  ``number`` etc. in its ``inputs``.

- ``NODE_CREATE``: an action originated directly from RPC request and it has
  a node associated with it.

- ``NODE_DELETE``: an action originated directly from RPC request and it has
  a node associated with it.

The policy will be checked **AFTER** one of the above mentioned actions that
adds new member nodes for the cluster is executed. It is also checked
**BEFORE** one of the above actions that removes existing members from the
cluster is executed.


Policy Properties
~~~~~~~~~~~~~~~~~

The load-balancing policy has its properties grouped into three categories:
``pool``, ``vip`` and ``health_monitor``. The ``pool`` property accepts a map
that contains detailed specification for the load-balancing pool that
contains the nodes as members such as "``protocol``", "``protocol_port``",
"``subnet``", "``lb_method``" etc. Most of the properties have a default value
except for the "``subnet``" which always requires an input.

The ``vip`` property also accepts a map that contains detailed specification
for the "virtual IP address" visible to the service users. These include for
example "``subnet``", "``address``", "``protocol``", "``protocol_port``"
values to be associated/assigned to the VIP.

The ``health_monitor`` property accepts a map that specifies the details about
the configuration of the "health monitor" provided by (embedded into) the
load-balancer. The map may contain values for keys like "``type``",
"``delay``", "``max_retries``", "``http_method``" etc.

For more details specifications of the policy specifications, you can use the
:command:`openstack cluster policy type show senlin.policy.loadbalance-1.1`
command.


Load Balancer Management
~~~~~~~~~~~~~~~~~~~~~~~~

When attaching a loadbalance policy to a cluster, the engine will always try
to create a new load balancer followed by adding existing nodes to the new
load-balancer created. If any member node cannot be added to the
load-balancer, the engine refuses to attach the policy to the cluster.

After having successfully added a node to the load balancer, the engine saves
a key-value pair "``lb_member: <ID>``" into the ``data`` field of the node.
After all existing nodes have been successfully added to the load balancer,
the engine saves the load balancer information into the policy binding data.
The information stored is something like the following example:

::

  {
    "LoadBalancingPolicy": {
      "version": 1.0,
      "data": {
        "loadbalancer": "bb73fa92-324d-47a6-b6ce-556eda651532",
        "listener": "d5f621dd-5f93-4adf-9c76-51bc4ec9f313",
        "pool": "0f58df07-77d6-4aa0-adb1-8ac6977e955f",
        "healthmonitor": "83ebd781-1417-46ac-851b-afa92844252d"
      }
    }
  }

When detaching a loadbalance policy from a cluster, the engine first checks
the information stored in the policy binding data where it will find the IDs
of the load balancer, the listener, the health monitor etc. It then proceeds
to delete these resources by invoking the LBaaS APIs. If any of the resources
cannot be deleted for some reasons, the policy detach request will be
rejected.

After all load balancer resources are removed, the engine will iterate through
all cluster nodes and delete the "``lb_member``" key-value pair stored there.
When all nodes have been virtually detached from the load-balancer, the detach
operation returns with a success.


Scenarios
~~~~~~~~~

S1: ``CLUSTER_SCALE_IN``
------------------------

When scaling in a cluster, there may and may not be a scaling policy attached
to the cluster. The loadbalance policy has to cope with both cases. The
loadbalance policy first attempts to get the number of nodes to remove then it
tries to get the candidate nodes for removal.

It will first check if there is a "``deletion``" key in the action's ``data``
field. If it successfully finds it, it means there are other policies already
helped decide the number of nodes to remove, even the candidate nodes for
removal. If the "``deletion``" key is not found, it means the policy has to
figure out the deletion count itself. It first checks if the action has an
input named "``count``". The ``count`` value will be used if found, or else it
will assume the ``count`` to be 1.

When the policy finds that the candidate nodes for removal have not yet been
chosen, it will try a random selection from all cluster nodes.

After the policy has figured out the candidate nodes for removal, it invokes
the LBaaS API to remove the candidates from the load balancer. If any of the
removal operation fails, the scale in operation fails before node removal
actually happens.

When all candidates have been removed from the load balancer, the scale in
operation continues to delete the candidate nodes.

S2: ``CLUSTER_DEL_NODES``
-------------------------

When deleting specified nodes from a cluster, the candidate nodes are already
provided in the action's ``inputs`` property, so the loadbalance policy just
iterate the list of candidate nodes to update the load balancer. The load
balancer side operation is identical to that outlined in scenario *S1*.

S3: ``CLUSTER_RESIZE`` that Shrinks a Cluster
---------------------------------------------

For a cluster resize operation, the loadbalance policy is invoked **BEFORE**
the operation is attempting to remove any nodes from the cluster. If there are
other policies (such as a scaling policy or a deletion policy) attached to the
cluster, the number of nodes along with the candidate nodes might have already
been decided.

The policy first checks the "``deletion``" key in the action's ``data`` field.
If it successfully finds it, it means there are other policies already helped
decide the number of nodes to remove, even the candidate nodes for removal.
If the "``deletion``" key is not found, it means the policy has to figure out
the deletion count itself. In the latter case, the policy will try to parse
the ``inputs`` property of the action and see if it is about to delete nodes
from the cluster. If the action is indeed about removing nodes, then the
policy gets what it wants, i.e. the ``count`` value. If the action is not
about deleting nodes, then the action passes the policy check directly.

After having figured out the number of nodes to delete, the policy may still
need to decide which nodes to remove, i.e. the candidates. When no other
policy has made a decision, the loadbalance policy randomly chooses the
specified number of nodes as candidates.

After the candidates is eventually selected, the policy proceeds to update the
load balancer as outlined in scenario *S1*.

S4: ``CLUSTER_SCALE_OUT``
-------------------------

The policy may be checked **AFTER** a scale out operation is performed on the
cluster. After new nodes have been created into the cluster, the loadbalance
policy needs to notify the load balancer about the new members added.
When the loadbalance policy is checked, there may and may not be other
policies attached to the cluster. So the policy will need to check both cases.

It first checks if there is a "``creation``" key in the action's ``data``
field. If the "``creation``" key is not found, it means the operation has
nothing to do with the loadbalance policy. For example, it could be a request
to resize a cluster, but the result is about removal of existing nodes instead
of creation of new nodes. In this case, the policy checking aborts immediately.

When new nodes are created, the operation is expected to have filled the
action's ``data`` field with data that looks like the following example:

::

  {
    "creation": {
      "count": 2,
      "nodes": [
        "4e54e810-6579-4436-a53e-11b18cb92e4c",
        "e730b3d0-056a-4fa3-9b1c-b1e6e8f7d6eb",
      ]
    }
  }

The "``nodes``" field in the ``creation`` map always contain a list of node
IDs for the nodes that have been created. After having get the node IDs, the
policy proceeds to add these nodes to the load balancer (recorded in the
policy binding data) by invoking the LBaaS API. If any update operation to the
load balancer fails, the policy returns with an error message. If a node has
been successfully added to the load balancer, the engine will record the
load balancer IDs into the node's ``data`` field.

S5: ``CLUSTER_ADD_NODES``
-------------------------

When a ``CLUSTER_ADD_NODES`` operation is completed, it will record the IDs of
the nodes into the ``creation`` property of the action's ``data`` field. The
logic to update the load balancer and the logic to update the ``data`` field
of individual nodes are identical to that described in scenario *S4*.

S6: ``CLUSTER_RESIZE`` that Expands a Cluster
---------------------------------------------

When a ``CLUSTER_RESIZE`` operation is completed and the operation results in
some new nodes created and added to the cluster, it will record the IDs of
the nodes into the ``creation`` property of the action's ``data`` field. The
logic to update the load balancer and the logic to update the ``data`` field
of individual nodes are identical to that described in scenario *S4*.

S7: Handling ``NODE_CREATE`` Action
-----------------------------------

When the action to be processed is a ``NODE_CREATE`` action, the new node has
been created and it is yet to be attached to the load balancer. The logic to
update the load balancer and the ``data`` field of the node in question are
identical to that described in scenario *S4*.

When the action to be processed is a ``NODE_DELETE`` action, the node is about
to be removed from the cluster. Before that, the policy is responsible to
detach it from the load balancer. The logic to update the load balancer and
the ``data`` field of the node in question are identical to that described in
scenario *S1*.
