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

.. _ref-scaling-policy:

==============
Scaling Policy
==============

The scaling policy is designed to supplement a cluster scaling request with
more detailed arguments based on user-provided rules. This policy type is
expected to be applicable on clusters of all profile types.


Properties
~~~~~~~~~~

.. schemaprops::
  :package: senlin.policies.scaling_policy.ScalingPolicy

Sample
~~~~~~

A typical spec for a scaling policy is shown below:

.. literalinclude :: /../../examples/policies/scaling_policy.yaml
  :language: yaml

You should pay special attentions to the ``event`` property, whose valid
values include "``CLUSTER_SCALE_IN``" and "``CLUSTER_SCALE_OUT``". One
implication of this design is that you have to attach two policies to the
same cluster if you want to control the scaling behavior both when you are
expanding the cluster and when you are shrinking it. You can not control the
scaling behavior in both directions using the same policy.

Senlin has carefully designed the builtin policy types so that for scaling
policies, you can attach more than one instance of the same policy type but
you may get an error when you are attempting to attach two policies of another
type (say ``senlin.policy.deletion``) to the same cluster.

The value of the ``event`` property indicates when the policy will be checked.
A policy with ``event`` set to "``CLUSTER_SCALE_IN``" will be checked when and
only when a corresponding action is triggered on the cluster. A policy with
``event`` set to "``CLUSTER_SCALE_OUT``" will be checked when and only when
a corresponding action is triggered. If the cluster is currently processing a
scaling action it will not accept another scaling action until the current
action has been processed and cooldown has been observed.

For both types of actions that can triggered the scaling policy, there are
always three types of adjustments to choose from as listed below. The type
of adjustment determines the interpretation of the ``adjustment.number`` value.

- ``EXACT_CAPACITY``: the value specified for ``adjustment.number`` means the
  new capacity of the cluster, so it has to be a non-negative integer.

- ``CHANGE_IN_CAPACITY``: the value specified for ``adjustment.number`` is the
  number of nodes to be added or removed. This means the value has to be a
  non-negative number as well.

- ``CHANGE_IN_PERCENTAGE``: the value specified for ``adjustment.number`` will
  be interpreted as the percentage of capacity changes. This value has to be
  a non-negative floating-point value.

For example, in the sample spec shown above, when a ``CLUSTER_SCALE_IN``
request is received, the policy will remove 10% of the total number of nodes
from the cluster.


Dealing With Percentage
~~~~~~~~~~~~~~~~~~~~~~~

As stated above, when ``adjustment.type`` is set to ``CHANGE_IN_PERCENTAGE``,
the value of ``adjustment.number`` can be a floating-point value, interpreted
as a percentage of the current node count of the cluster.

In many cases, the result of the calculation may be a floating-point value.
For example, if the current capacity of a cluster is 5 and the
``adjustment.number`` is set to 30%, the compute result will be 1.5. In this
situation, the scaling policy rounds the number up to its adjacent integer,
i.e. 2. If the ``event`` property has "``CLUSTER_SCALE_OUT``" as its value,
the policy decision is to add 2 nodes to the cluster. If on the other hand the
``event`` is set to "``CLUSTER_SCALE_IN``", the policy decision is to remove
2 nodes from the cluster.

There are other corner cases to consider as well. When the compute result is
less than 0.1, for example, it becomes a question whether the Senlin engine
should add (or remove) nodes. The property ``adjustment.min_step`` is designed
to make this decision. After policy has got the compute result, it will check
if it is less than the specified ``adjustment.min_step`` value and it will use
the ``adjustment.min_step`` value if so.


Best Effort Scaling
~~~~~~~~~~~~~~~~~~~

In many auto-scaling usage scenarios, the policy decision may break the size
constraints set on the cluster. As an example, a cluster has its ``min_size``
set to 5, ``max_size`` set to 10 and its current capacity is 7. If the policy
decision is to remove 3 nodes from the cluster, we are in a dilemma. Removing
3 nodes will change the cluster capacity to 4, which is not allowed by the
cluster. If we don't remove 3 nodes, we are not respecting the policy
decision.

The ``adjustment.best_effort`` property is designed to mitigate this situation.
When it is set to False, the scaling policy will strictly conform to the rules
set. It will reject the scaling request if the computed cluster capacity will
break its size constraints. However, if ``adjustment.best_effort`` is set to
True, the scaling policy will strive to compute a sub-optimal number which
will not break the cluster's size constraints. In the above example, this
means the policy decision will be "remove 2 nodes from the cluster". In other
words, the policy at least will try partially ful-fill the scaling goal for
the sake of respecting the size constraint.


Cooldown
~~~~~~~~

In real-life cluster deployments, workload pressure fluctuates rapidly. During
this minute, it smells like there is a need to add 10 more nodes to handle the
bursting workload. During the next minute, it may turn out to be a false
alarm, the workload is rapidly decreasing. Since it is very difficult to
accurately predict the workload changes, if possible at all, an auto-scaling
engine is not supposed to react too prematurely to workload fluctuations.

The ``cooldown`` property gives you a chance to specify an interval during
which the cluster will remain ignorant to scaling requests. Setting a large
value to this property will lead to a stable cluster, but the responsiveness
to urgent situation is also sacrificed. Setting a small value, on the
contrary, can meet the responsiveness requirement, but will also render the
cluster into a thrashing state where new nodes are created very frequently
only to be removed shortly.

There is never a recommended value that suits all deployments. You will have
to try different values in your own environment and tune it for different
applications or services.


Interaction with Other Policies
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The scaling policy is only tasked to decide the number of nodes to add or
remove. For newly added nodes, you will use other policies to determine where
they should be scheduled. For nodes to be deleted, you will use other polices
(e.g. the deletion policy) to elect the victim nodes.

The builtin policies were designed carefully so that they can work happily
together or by themselves.

