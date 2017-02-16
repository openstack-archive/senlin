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

.. _ref-health-policy:

=============
Health Policy
=============

The health policy is designed for Senlin to detect cluster node failures and
to recover them in a way customizable by users. The health policy is not
meant to be an universal solution that can solve all problems related to
high-availability. However, the ultimate goal for the development team is to
provide an auto-healing framework that is usable, flexible, extensible for
most deployment scenarios.

The policy type is currently applicable to clusters whose profile type is one
of ``os.nova.server`` or ``os.heat.stack``. This could be extended in future.


.. note::

  The health policy is still under rapid development. More features are being
  designed, implemented and verified. Its support status is still
  ``EXPERIMENTAL``, which means there could be changes at the discretion of
  the development team before it is formally supported.


Properties
~~~~~~~~~~

A typical spec for a health policy looks like the following example:

.. code-block:: yaml

  type: senlin.policy.health
  version: 1.0
  properties:
    detection:
      type: NODE_STATUS_POLLING
      options:
        interval: 60
    recovery:
      actions:
        - name: REBOOT
          params:
            type: soft
      fencing:
        - compute


There are two groups of properties (``detection`` and ``recovery``),  each of
which provides information related to the failure detection and the failure
recovery aspect respectively.

For failure detection, you can specify one of the following two values:

- ``NODE_STATUS_POLLING``: Senlin engine (more specifically, the health
  manager service) is expected to poll each and every nodes periodically to
  find out if they are "alive" or not.

- ``LIFECYCLE_EVENTS``: Many services can emit notification messages on the
  message queue when configured. Senlin engine is expected to listen to these
  events and react to them appropriately.

Both detection types can carry an optional map of ``options``. When the
detection type is set to "``NODE_STATUS_POLLING``", for example, you can
specify a value for ``interval`` property to customize the frequency at which
your cluster nodes are polled.

As the policy type implementation stabilizes, more options may be added later.

For failure recovery, there are currently two properties: ``actions`` and
``fencing``. The ``actions`` property takes a list of action names and an
optional map of parameters specific to that action. For example, the
``REBOOT`` action can be accompanied with a ``type`` parameter that indicates
if the intended reboot operation is a soft reboot or a hard reboot.

.. note::

  The plan for recovery actions is to support a list of actions which can be
  tried one by one by the Senlin engine. Currently, you can specify only
  *one* action due to implementation limitation.

  Another extension to the recovery action is to add triggers to user provided
  workflows. This is also under development.


Validation
~~~~~~~~~~

Due to implementation limitation, currently you can only specify *one* action
for the ``recovery.actions`` property. This constraint will be removed soon
after the support to action list is completed.


Fencing
~~~~~~~

Fencing may be an important step during a reliable node recovery process.
Without fencing, we cannot ensure that the compute, network and/or storage
resources are in a consistent, predictable status. However, fencing is very
difficult because it always involves an out-of-band operation to the resource
controller, for example, an IPMI command to power off a physical host sent to
a specific IP address.

Currently, the health policy only supports the fencing of virtual machines by
forcibly delete it before taking measures to recover it.


Snapshots
~~~~~~~~~

There have been some requirements to take snapshots of a node before recovery
so that the recovered node(s) will resume from where they failed. This feature
is also on the TODO list for the development team.
