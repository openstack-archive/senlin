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


===============
Affinity Policy
===============

The affinity policy is designed for senlin to leverage the *server group* API
in nova. Using this policy, you can specify whether the nodes in a cluster
should be collocated on the same physical machine (aka. "affinity") or they
should be spread onto as many physical machines as possible (aka.
"anti-affinity").

Currently, this policy can be used on nova server clusters only.

Properties
~~~~~~~~~~

The affinity policy has the following properties:

- ``servergroup.name``: An optional string that will be used as the name of
  server group to be created.
- ``servergroup.policies``: A string indicating the policy to be used for
  the server group.
- ``availability_zone``: Optional string specifying the availability zone for
  the nodes to launch from.
- ``enable_drs_extension``: A boolean indicating whether VMware vSphere
  extension should be enabled.

Since the ``os.nova.server`` profile type may contain ``scheduler_hints``
which has server group specified, the affinity policy will behave differently
based on different settings.

<TBC>
