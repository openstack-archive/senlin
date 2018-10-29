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

.. _ref-zone-policy:

=====================
Zone Placement Policy
=====================

The zone placement policy is designed to enable the deployment and management
resource pools across multiple availability zones. Note that the current design
is only concerned with the availability zones configured to Nova compute
service. Support to Cinder availability zones and Neutron availability zones
may be added in future when we have volume storage specific or network
specific profile types.

The current implementation of the zone placement policy works with clusters of
Nova virtual machines only.


Properties
~~~~~~~~~~

.. schemaprops::
  :package: senlin.policies.zone_placement.ZonePlacementPolicy

Sample
~~~~~~

A typical spec for a zone placement policy is exemplified in the following
sample:

.. literalinclude :: /../../examples/policies/placement_zone.yaml
  :language: yaml

In this sample spec, two availability zones are provided, namely "``az_1``" and
"``az_2``". Each availability zone can have an optional "``weight``" attribute
associated with it.

The "``weight``" value is to be interpreted as a relative number. The value
assigned to one zone has to be compared to those assigned to other zones for
an assessment. In the sample shown above, ``az_1`` and ``az_2`` are assigned
weights of 100 and 200 respectively. This means that among every 3 nodes
creation, one is expected to be scheduled to ``az_1`` and the other 2 are
expected to be scheduled to ``az_2``. In other words, the chance for ``az_2``
receiving a node creation request is twice of that for ``az_1``.

The "``weight``" value has to be a positive integer, if specified. The default
value is 100 for all zones whose weight is omitted.


Validation
~~~~~~~~~~

When creating a zone placement policy, the Senlin engine validates whether
the zone names given are all known to be usable availability zones by the Nova
compute service. Do NOT pass in an invalid availability zone name and hope
Senlin can create a zone for you.

Later on when the zone placement policy is triggered upon node creation or node
deletion actions, it always validates if the provided availability zones are
still valid and usable.


Node Distribution
~~~~~~~~~~~~~~~~~

After a zone placement policy is attached to a cluster and enabled, all future
node creations (by cluster scaling for example) will trigger an evaluation of
the policy. Similarly, a node deletion action will also trigger an evaluation
of it because the policy's goal is to maintain the node distribution based on
the one computed from the weight distribution of all zones.

The zone placement policy will favor availability zones with highest weight
values when selecting a zone for nodes to be created.
