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

.. _ref-region-policy:

=======================
Region Placement Policy
=======================

The region placement policy is designed to enable the deployment and management
resource pools across multiple regions. Note that the current design is only
concerned with a single keystone endpoint for multiple regions, interacting
with keystone federation is planned for future extension.

The policy is designed to work with clusters of any profile types.


Properties
~~~~~~~~~~

.. schemaprops::
  :package: senlin.policies.region_placement.RegionPlacementPolicy

Sample
~~~~~~

A typical spec for a region placement policy is shown in the following sample:

.. literalinclude :: /../../examples/policies/placement_region.yaml
  :language: yaml

In this sample spec, two regions are provided, namely "``region_1``" and
"``region_2``". There are "weight" and "cap" attributes associated with them,
both of which are optional.

The "``weight``" value is to be interpreted as a relative number. The value
assigned to one region has to be compared to those assigned to other regions
for an assessment. In the sample shown above, ``region_1`` and ``region_2``
are assigned weights with 100 and 200 respectively. This means that among
every 3 nodes creation, one is expected to be scheduled to ``region_1`` and
the other 2 is expected to be scheduled to ``region_2``. Put it in another
way, the chance for ``region_2`` receiving a node creation request is twice of
that for ``region_1``.

The "``weight``" value has to be a positive integer, if specified. The default
value is 100 for all regions whose weight is omitted.

There are cases where each region has different amounts of resources
provisioned so their capacity for creating and running nodes differ. To deal
with these situations, you can assign a "``cap``" value to such a region. This
effectively tells the Senlin engine that a region is not supposed to
accommodate nodes more than the specified number.


Validation
~~~~~~~~~~

When creating a region placement policy, the Senlin engine validates whether
the region names given are all known to be available regions by the keystone
identity service. Do NOT pass in an invalid region name and hope Senlin can
create a region for you.

Later on when the policy is triggered by node creation or deletion, it always
validates if the provided regions are still valid and usable.


Node Distribution
~~~~~~~~~~~~~~~~~

After a region placement policy is attached to a cluster and enabled, all
future node creations (by cluster scaling for example) will trigger an
evaluation of the policy.

The region placement policy will favor regions with highest weight value when
selecting a region for nodes to be created. It will guarantee that no more
than the provided ``cap`` number of nodes will be allocated to a specific
region.

Node distribution is calculated not only when new nodes are created and added
to a cluster, it is also calculated when existing nodes are to be removed from
the cluster. The policy will strive to maintain a distribution close to the
one computed from the weight distribution of all regions.
