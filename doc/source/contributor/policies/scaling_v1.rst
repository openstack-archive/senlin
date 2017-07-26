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


===================
Scaling Policy V1.0
===================

This policy is designed to help decide the detailed, quantitative parameters
used for scaling in/out a cluster. Senlin does provide a more complicated API
for resizing a cluster (i.e. ``cluster_resize``), however, in some use cases,
we cannot assume the requesters have all the factors to determine each and
every detailed parameters for resizing a cluster. There are cases where the
only thing a requester knows for sure is that a cluster should be scaled out,
or be scaled in. A scaling policy helps derive appropriate, quantitative
parameters for such a request.

Note that when calculating the target capacity of the cluster, Senlin only
considers the **ACTIVE** nodes.


Applicable Profiles
~~~~~~~~~~~~~~~~~~~

The policy is designed to handle any (``ANY``) profile types.


Actions Handled
~~~~~~~~~~~~~~~

The policy is capable of handling the following actions:

- ``CLUSTER_SCALE_IN``: an action that carries an optional integer value named
  ``count`` in its ``inputs``.

- ``CLUSTER_SCALE_OUT``: an action that carries an optional integer value
  named ``count`` in its ``inputs``.

The policy will be checked **BEFORE** any of the above mentioned actions is
executed. Because the same policy implementation is used for covering both the
cases of scaling out a cluster and the cases of scaling in, the scaling policy
exposes a "``event``" property to differentiate a policy instance. This is
purely an implementation convenience.

Senlin engine respects the user-provided "``count``" input parameter if it is
specified. Or else, the policy computes a ``count`` value based on the policy's
``adjustment`` property. In both cases, the policy will validate the targeted
capacity against the cluster's size constraints.

After validating the ``count`` value, the deletion policy proceeds to update
the ``data`` property of the action based on the validation result. If the
validation fails, the ``data`` property of the action will be updated to
something similar to the following example:

::

  {
    "status": "ERROR",
    "reason": "The target capacity (3) is less than cluster's min_size (2)."
  }

If the validation succeeds, the ``data`` property of the action is updated
accordingly (see Scenarios below).


Scenarios
~~~~~~~~~

S1: ``CLUSTER_SCALE_IN``
------------------------

The request may carry a "``count``" parameter in the action's ``inputs`` field.
The scaling policy respects the user input if provided, or else it will
calculate the number of nodes to be removed based on other properties of the
policy. In either case, the policy will check if the ``count`` value is a
positive integer (or it can be convert to one).

In the next step, the policy check if the "``best_effort``" property has been
set to ``True`` (default is ``False``). When the value is ``True``, the policy
will attempt to use the actual difference between the cluster's minimum size
and its current capacity rather than the ``count`` value if the latter is
greater than the former.

When the proper ``count`` value is generated and passes validation, the policy
updates the ``action`` property of the action into something like the
following example:

::

  {
    "status": "OK",
    "reason": "Scaling request validated.",
    "deletion": {
      "count": 2
    }
  }


S2: ``CLUSTER_SCALE_OUT``
-------------------------

The request may carry a "``count``" parameter in the action's ``inputs`` field.
The scaling policy respects the user input if provided, or else it will
calculate the number of nodes to be added based on other properties of the
policy. In either case, the policy will check if the ``count`` value is a
positive integer (or it can be convert to one).

In the next step, the policy check if the "``best_effort``" property has been
set to ``True`` (default is ``False``). When the value is ``True``, the policy
will attempt to use the actual difference between the cluster's maximum size
and its current capacity rather than the ``count`` value if the latter is
greater than the former.

When the proper ``count`` value is generated and passes validation, the policy
updates the ``action`` property of the action into something like the
following example:

::

  {
    "status": "OK",
    "reason": "Scaling request validated.",
    "creation": {
      "count": 2
    }
  }


S3: Cross-region or Cross-AZ Scaling
------------------------------------

When scaling a cluster across multiple regions or multiple availability zones,
the scaling policy will be evaluated before the
:doc:`region placement policy <region_v1>` or the
:doc:`zone placement policy <zone_v1>` respectively. Based on
builtin priority settings, checking of this scaling policy always happen
before the region placement policy or the zone placement policy.

The ``creation.count`` or ``deletion.count`` field is expected to be respected
by the region placement or zone placement policy. In other words, those
placement policies will base their calculation of node distribution on the
``creation.count`` or ``deletion.count`` value respectively.
