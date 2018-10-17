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

.. _ref-affinity-policy:

===============
Affinity Policy
===============

The affinity policy is designed for senlin to leverage the *server group* API
in nova. Using this policy, you can specify whether the nodes in a cluster
should be collocated on the same physical machine (aka. "affinity") or they
should be spread onto as many physical machines as possible (aka.
"anti-affinity").

Currently, this policy can be used on nova server clusters only. In other
words, the type name of the cluster's profile has to be ``os.nova.server``.

Properties
~~~~~~~~~~

.. schemaprops::
  :package: senlin.policies.affinity_policy.AffinityPolicy

Sample
~~~~~~

A typical spec for an affinity policy looks like the following example:

.. literalinclude :: /../../examples/policies/affinity_policy.yaml
  :language: yaml

The affinity policy has the following properties:

- ``servergroup.name``: An optional string that will be used as the name of
  server group to be created.
- ``servergroup.policies``: A string indicating the policy to be used for
  the server group.
- ``availability_zone``: Optional string specifying the availability zone for
  the nodes to launch from.
- ``enable_drs_extension``: A boolean indicating whether VMware vSphere
  extension should be enabled.


Validation
~~~~~~~~~~

When creating an affinity policy, the Senlin engine checks if the provided spec
is valid:

- The value for ``servergroup.policies`` must be one of "``affinity``" or
  "``anti-affinity``". The default value is "``affinity``" if omitted.

- The value of ``availability_zone`` is the name of an availability zone known
  to the Nova compute service.


Server Group Name
~~~~~~~~~~~~~~~~~

Since the ``os.nova.server`` profile type may contain ``scheduler_hints``
which has server group specified, the affinity policy will behave differently
based on different settings.

If the profile used by a cluster contains a ``scheduler_hints`` property (as
shown in the example), the Senlin engine checks if the specified group name
("``group_135``" in this case) is actually known to the Nova compute service
as a valid server group. The server group name from the profile spec will
take precedence over the ``servergroup.name`` value in the policy spec.

.. code-block:: yaml

  type: os.nova.server
  version: 1.0
  properties:
    flavor: m1.small
    ...
    scheduler_hints:
      group: group_135

If the ``group`` value is found to be a valid server group name, the Senlin
engine will try compare if the policies specified for the nova server group
matches that specified in the affinity policy spec. If the policies don't
match, the affinity policy won't be able to be attached to the cluster.

If the profile spec doesn't contain a ``scheduler_hints`` property or the
``scheduler_hints`` property doesn't have a ``group`` value, the Senlin engine
will use the ``servergroup.name`` value from the affinity policy spec, if
provided. If the policy spec also failed to provide a group name, the Senlin
engine will try to create a server group with a random name, e.g.
"``server_group_x2mde78a``".  The newly created server group will be deleted
automatically when you detach the affinity policy from the cluster.


Availability Zone Name
~~~~~~~~~~~~~~~~~~~~~~

The spec property ``availability_zone`` is optional, no matter the value for
``enable_drs_extension`` is specified or not or what value it is assigned.
However, if the ``availability_zone`` property does have a value, it will have
an impact on the placement of newly created nodes. This subsection discusses
the cases when DRS extension is not enabled.

In the case that DRS extension is not enabled and the ``availability_zone``
property doesn't have a value. Senlin engine won't assign an availability zone
for newly created nodes.

By contrast, if the ``availability_zone`` property does have a value and it
has been validated to be name of an availability zone known to Nova, all newly
created nodes will be created into the specified availability zone.


DRS Extension
~~~~~~~~~~~~~

The property ``enable_drs_extension`` tells Senlin engine that the affinity
would be enforced by the VMware vSphere extension. In this case, the value of
the ``availability_zone`` property will be used to search for a suitable
hypervisor to which new nodes are scheduled.

All newly created nodes in the cluster, when an affinity policy is attached
and enabled, will be scheduled to an availability zone named
``<ZONE>:<HOST>`` where ``<ZONE>`` is the value of ``availability_zone`` and
``<HOST>`` is the hostname of a selected DRS hypervisor.
