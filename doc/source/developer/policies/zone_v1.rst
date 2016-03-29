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
Zone Placement Policy V1.0
==========================

This policy is designed to make sure the nodes in a cluster are distributed
across multiple availability zones according to a specified scheme.


Applicable Profiles
~~~~~~~~~~~~~~~~~~~

The policy is designed to handle Nova server clusters only, i.e. clusters with
a profile of type ``os.nova.server-1.0`` for example.


Actions Handled
~~~~~~~~~~~~~~~

The policy is capable of handling the following actions:

- ``CLUSTER_SCALE_IN``: an action that carries an optional integer value named
  ``count`` in its ``inputs``.

- ``CLUSTER_SCALE_OUT``: an action that carries an optional integer value
  named ``count`` in its ``inputs``.

- ``CLUSTER_RESIZE``: an action that accepts a map as its input parameters in
  its ``inputs`` property, such as "``adjustment_type``", "``number``" etc.


The policy will be checked **BEFORE** any of the above mentioned actions is
executed. Because the same policy implementation is used for covering both the
cases of scaling out a cluster and the cases of scaling in, the zone placment
policy need to parse the inputs in different scenarios.

The placement policy can be used independently, with and without other polices
attached to the same cluster. So the policy needs to understand whether there
are policy decisions from other policies (such as a
:doc:`scaling policy <scaling_v1>`).

When the policy is checked, it will first attempt to get the proper ``count``
input value, which may be an outcome from other policies or the inputs for
the action. For more details, check the scenarios described in following
sections.


Scenarios
~~~~~~~~~

S1: ``CLUSTER_SCALE_IN``
------------------------

The placement policy first checks if there are policy decisions from other
policies by looking into the ``deletion`` field of the action's ``data``
property. If there is such a field, the policy attempts to extract the
``count`` value from the ``deletion`` field. If the ``count`` value is not
found, 1 is assumed to be the default.

If, however, the policy fails to find the ``deletion`` field, it tries to find
if there is a ``count`` field in the action's ``inputs`` property. If the
answer is true, the policy will use it, or else it will fall back to assume 1
as the default count.

After the policy has find out the ``count`` value (i.e. number of nodes to be
deleted), it validates the list of availability zone names provided to the
policy. If for some reason, none of the provided names passed the validation,
the policy check fails with the following data recorded in the action's
``data`` property:

::

  {
    "status": "ERROR",
    "reason": "No availability zone found available.",
  }

With the list of availability zones known to be good and the map of node
distribution specified in the policy spec, senlin engine continues to
calculate a distribution plan that best matches the desired distribution.
If there are nodes that cannot be fit into the distribution plan, the policy
check failes with an error recorded in the action's ``data``, as shown below:

::

  {
    "status": "ERROR",
    "reason": "There is no feasible plan to handle all nodes."
  }

If there is a feasible plan to remove nodes from each availability zone, the
policy saves the plan into the ``data`` property of the action as exemplified
below:

::

  {
    "status": "OK",
    "deletion": {
      "count": 3,
      "zones": {
        "nova-1": 2,
        "nova-2": 1
      }
    }
  }

This means in total, 3 nodes should be removed from the cluster. Among them,
2 nodes should be selected from availability zone "``nova-1``" and the rest
one should be selected from availability zone "``nova-2``".

**NOTE**: When there is a :doc:`deletion policy <deletion_v1>` attached to the
same cluster. That deletion policy will be evaluated after the zone placement
policy and it is expected to rebase its candidate selection on the zone
distribution enforced here. For example, if the deletion policy is tasked to
select the oldest nodes for deletion, it will adapt its behavior to select
the oldest nodes from each availability zone. The number of nodes to be chosen
from each availability zone would be based on the output from this placement
policy.


S2: ``CLUSTER_SCALE_OUT``
-------------------------

The placement policy first checks if there are policy decisions from other
policies by looking into the ``creation`` field of the action's ``data``
property. If there is such a field, the policy attempts to extract the
``count`` value from the ``creation`` field. If the ``count`` value is not
found, 1 is assumed to be the default.

If, however, the policy fails to find the ``creation`` field, it tries to find
if there is a ``count`` field in the action's ``inputs`` property. If the
answer is true, the policy will use it, or else it will fall back to assume 1
as the default node count.

After the policy has find out the ``count`` value (i.e. number of nodes to be
created), it validates the list of availability zone names provided to the
policy and extracts the current distribution of nodes among those availability
zones.

If for some reason, none of the provided names passed the validation,
the policy check fails with the following data recorded in the action's
``data`` property:

::

  {
    "status": "ERROR",
    "reason": "No availability zone found available.",
  }

The logic of generating a distribution plan is almost identical to what have
been described in scenario *S1*, except for the output format. When there is
a feasible plan to accommodate all nodes, the plan is saved into the ``data``
property of the action as shown in the following example:

::

  {
    "status": "OK",
    "creation": {
      "count": 3,
      "zones": {
        "nova-1": 1,
        "nova-2": 2
      }
    }
  }

This means in total, 3 nodes should be created into the cluster. Among them,
2 nodes should be created at availability zone "``nova-1``" and the left one
should be created at availability zone "``nova-2``".

S3: ``CLUSTER_RESIZE``
----------------------

The placement policy first checks if there are policy decisions from other
policies by looking into the ``creation`` field of the action's ``data``
property. If there is such a field, the policy extracts the ``count`` value
from the ``creation`` field. If the ``creation`` field is not found, the policy
tries to find if there is a ``deletion`` field in the action's ``data``
property. If there is such a field, the policy extracts the ``count`` value
from the ``creation`` field. If neither ``creation`` nor ``deletion`` is found
in the action's ``data`` property, the policy proceeds to parse the raw inputs
of the action.

The output from the parser may indicate an invalid combination of input
values. If that is the case, the policy check fails with the action's
``data`` set to something like the following example:

::

  {
    "status": "ERROR",
    "reason": <error message from the parser.>
  }

If the parser successfully parsed the action's raw inputs, the policy tries
again to find if there is either ``creation`` or ``deletion`` field in the
action's ``data`` property. It will use the ``count`` value from the field
found as the number of nodes to be handled.

When the placement policy finds out the number of nodes to create (or delete),
it proceeds to calculate a distribution plan. If the action is about growing
the size of the cluster, the logic and the output format are the same as that
have been outlined in scenario *S2*. Otherwise, the logic and the output
format are identical to that have been described in scenario *S1*.
