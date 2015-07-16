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


.. _guide-bindings:

Cluster-Policy Bindings
=======================

Concept
-------

A :term:`Policy` object can attached to at least one :term:`Cluster` at the
same time. A cluster at any time can have more than one Policy objects
attached to it.

When created, a policy object has a default ``enforcement-level`` value and a
default ``cooldown`` value. When attaching the policy to a cluster, you can
specify a different value for the ``enforcement-level`` property and/or a
different value for the ``cooldown`` property. These new values can be treated
as a customization of the policy for the cluster.

After a policy object is attached to a cluster, you can still enable or
disable it or update some properties of the policy object.


Listing Policies Attached to a Cluster
--------------------------------------

The :program:`senlin` tool provides the :command:`cluster-policy-list` command
to list policy objects that are attached to a cluster. You can provide the
name, the ID or the "short ID" of a cluster as the identifier to reference a
cluster. For example, the command below lists the policies attached to the
cluster ``webservers``::

  $ senlin cluster-policy-list webservers


Sorting the List
^^^^^^^^^^^^^^^^

You specify the sorting keys and sorting directions for the policy list,
using the option :option:`--sort-keys` (or :option:`-k`) and the option
:option:`--sort-dir` (or :option:`-s`). For example, the following command
instructs the :program:`senlin` command line to sort policies using the
``priority`` property in descending order::

  $ senlin cluster-policy-list -k priority -s desc c3
  +--------------------------------------+--------+----------------+----------+-------+----------+---------+
  | policy_id                            | policy | type           | priority | level | cooldown | enabled |
  +--------------------------------------+--------+----------------+----------+-------+----------+---------+
  | 239d7212-6196-4a89-9446-44d28717d7de | dp01   | DeletionPolicy | 40       | 50    | 60       | True    |
  | 0705f0f4-629e-4417-84d7-30569d23b271 | up01   | UpdatePolicy   | 20       | 50    | 60       | True    |
  +--------------------------------------+--------+----------------+----------+-------+----------+---------+

For sorting the policy list, the valid keys are: ``priority``, ``level``,
``cooldown`` and ``enabled``, the valid sorting directions are: ``asc`` and
``desc``.


Filtering the List
^^^^^^^^^^^^^^^^^^

The :program:`senlin` command line also provides options for filtering the
policy list at the server side. The option :option:`--filters` (or
:option:`-f`) can be used for this purpose. For example, the following command
filters clusters by the ``priority`` field::

]$ senlin cluster-policy-list -f priority=20 c3
+--------------------------------------+--------+----------------+----------+-------+----------+---------+
| policy_id                            | policy | type           | priority | level | cooldown | enabled |
+--------------------------------------+--------+----------------+----------+-------+----------+---------+
| 0705f0f4-629e-4417-84d7-30569d23b271 | up01   | UpdatePolicy   | 20       | 50    | 60       | True    |
+--------------------------------------+--------+----------------+----------+-------+----------+---------+

The option :option:`--filters` accepts a list of key-value pairs separated by
semicolon (``;``), where each key-value pair is expected to be of format
``<key>=<value>``. The valid keys for filtering include: ``priority``,
``level``, ``cooldown``, ``enabled``.


Attaching a Policy to a Cluster
-------------------------------

Senlin permits policy objects to be attached to clusters and to be detached
from clusters dynamically. When attaching a policy object to a cluster, you
can customize the policy properties for the particular cluster. For example,
you can specify a different value for the "``level``" property from the
default value in the policy. This value will be used to indicate the
enforcement level of a policy object on this cluster.

The following options are supported for the :command:`cluster-policy-attach`
command:

- :option:`--priority` (or :opiton:`-r`): specifies the relative priority
  among all policies attached to the same cluster. Policies with a lower
  priority value (higher priority) will be evaluated before those with a
  higher value (lower priority).
- :option:`--level` (or :option:`-l`): specifies the enforcement level of the
  policy object. It must be a value between 0 and 100.
- :option:`--cooldown` (or :option:`-c`): an integer indicating the cooldown
  seconds once the policy is effected.
- :option:`--enabled` (or :option:`-e`): a boolean indicating whether the
  policy to be enabled once attached.

For example, the following command attaches a policy named ``up01`` to the
cluster ``c3``, with the policy's priority set to 20, its cooldown set to 60
(seconds) and its enforcement level set to 50::

  $ senlin cluster-policy-attach -r 20 -l 50 -c 60 -e -p up01 c3

Note that currently, Senlin doesn't more than one policy of the same type to
be attached to the same cluster. In future, this restriction may be removed.

For the identifiers specified for the cluster and the policy, you can use the
name, the ID or the "short ID" of an object. The Senlin engine will try make a
guess on each case. If no entity matches the specified identifier or there are
more than one entity matching the identifier, you will get an error message.


Showing Policy Properties on a Cluster
-------------------------------------

To examine the detailed properties of a policy object that has been attached
to a cluster, you can use the command :command:`cluster-policy-show` with the
policy identifier and the cluster identifier specified. For example::

  $ senlin cluster-policy-show -p dp01 c3
  +--------------+--------------------------------------+
  | Property     | Value                                |
  +--------------+--------------------------------------+
  | cluster_id   | 2b7e9294-b5cd-470f-b191-b18f7e672495 |
  | cluster_name | c3                                   |
  | cooldown     | 60                                   |
  | enabled      | True                                 |
  | level        | 50                                   |
  | policy       | dp01                                 |
  | policy_id    | 239d7212-6196-4a89-9446-44d28717d7de |
  | priority     | 40                                   |
  | type         | DeletionPolicy                       |
  +--------------+--------------------------------------+

You can use the name, the ID or the "short ID" of a policy and/or a cluster to
name the objects.


Updating Policy Properties on a Cluster
------------------------------------------

Once a policy is attached to a cluster, you can request its property on this
cluster be changed by using the command :command:`cluster-policy-update`. For
this command, you can specify the ``priority``, the ``cooldown``, the
``level`` and or the ``enabled`` property to be updated. The arguments
acceptable are identical to those for the :command:`cluster-policy-attach`
command.

For example, the following command updates a policy's priority to 60 on the
specified cluster::

  $ senlin cluster-policy-update -r 60 -p deletion_polity mycluster

The Senlin engine will perform validation of the arguments in the same way as
that for the policy attach operation. You can use the name, the ID or the
"short ID" of an entity to reference it, as you do with the policy attach
operation as well.

The :program:`senlin` command line also provides two convenient commands for
toggling the ``enabled`` status of a policy on a cluster. For example, the
following two commands temporarily disables a policy on a cluster and then
reenable it::

  $ senlin cluster-policy-disable -p dp01 mycluster
  $ senlin cluster-policy-enable -p dp01 mycluster

For these two commands, you can use the name, the ID or the "short ID" of an
object to name it as well.


Detach a Policy from a Cluster
------------------------------

Finally, to remove the binding between a specified policy object from a
cluster, you can use the :command:`cluster-policy-detach` command as shown
below::

  $ senlin cluster-policy-detach -p dp01 mycluster

This command will detach the specified policy from the specified cluster.
You will use the option :option:`--policy` (or `-p`) to specify the policy.
