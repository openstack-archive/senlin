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

.. _scenario-affinity:

======================
Support to AutoScaling
======================

The senlin service provides a rich set of facilities for building an
auto-scaling solution:

- *Operations*: The ``CLUSTER_SCALE_OUT``, ``CLUSTER_SCALE_IN`` operations are
  the simplest form of commands to scale a cluster. The ``CLUSTER_RESIZE``
  operation, on the other hand, provides more options for controlling the
  detailed cluster scaling behavior. These operations can be performed with
  and without policies attached to a cluster.

- *Policies*:

  The ``senlin.policy.scaling`` (:doc:`link <../user/policy_types/scaling>`)
  policy can be applied to fine tune the cluster scaling operations.

  The ``senlin.policy.deletion`` (:doc:`link <../user/policy_types/deletion>`)
  policy can be attached to a cluster to control how nodes are removed from a
  cluster.

  The ``senlin.policy.affinity`` (:doc:`link <../user/policy_types/affinity>`)
  policy can be used to control how node affinity or anti-affinity can be
  enforced.

  The ``senlin.policy.region_placement``
  (:doc:`link <../user/policy_types/region_placement>`) can be applied to
  scale a cluster across multiple regions.

  The ``senlin.policy.zone_placement``
  (:doc:`link <../user/policy_types/zone_placement>`) can be enforced to
  achieve a cross-availability-zone node distribution.

- *Receivers*: The receiver (:doc:`link <../user/receivers>`) concept provides a
  channel to which you can send signals or alarms from an external monitoring
  software or service so that scaling operations can be automated.

This section provides some guides on integrating senlin with other services
so that cluster scaling can be automated.
