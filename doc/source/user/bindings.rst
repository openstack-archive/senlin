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

=======================
Cluster-Policy Bindings
=======================

Concept
~~~~~~~

A :term:`Policy` object can attached to at least one :term:`Cluster` at the
same time. A cluster at any time can have more than one Policy objects
attached to it.

After a policy object is attached to a cluster, you can still enable or
disable it or update some properties of the policy object.


Listing Policies Attached to a Cluster
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The :program:`senlin` tool provides the :command:`cluster-policy-list` command
to list policy objects that are attached to a cluster. You can provide the
name, the ID or the "short ID" of a cluster as the identifier to reference a
cluster. For example, the command below lists the policies attached to the
cluster ``webservers``::

  $ senlin cluster-policy-list webservers


Sorting the List
----------------

You can specify the sorting keys and sorting direction when list cluster
policies, using the option :option:`--sort` (or :option:`-o`). The
:option:`--sort` option accepts a string of format
``key1[:dir1],key2[:dir2],key3[:dir3]``, where the keys used are properties
of the policy bound to a cluster and the dirs can be one of ``asc`` and
``desc``. When omitted, Senlin sorts a given key using ``asc`` as the default
direction.

For example, the following command instructs the :program:`senlin` command
line to sort policy bindings using the ``enabled`` property in descending
order::

  $ senlin cluster-policy-list -o enabled:desc 

When sorting the list of policies, ``enabled`` is the only key you can specify
for sorting.


Filtering the List
------------------

The :program:`senlin` command line also provides options for filtering the
policy list at the server side. The option :option:`--filters` (or
:option:`-f`) can be used for this purpose. For example, the following command
filters clusters by the ``enabled`` field::

  $ senlin cluster-policy-list -f enabled=True c3
  +-----------+--------+-----------------------+---------+
  | policy_id | policy | type                  | enabled |
  +-----------+--------+-----------------------+---------+
  | 0705f0f4  | up01   | senlin.policy.scaling | True    |
  +-----------+--------+-----------------------+---------+

The option :option:`--filters` accepts a list of key-value pairs separated by
semicolon (``;``), where each key-value pair is expected to be of format
``<key>=<value>``. The only key that can be used for filtering as of today is
``enabled``.


Attaching a Policy to a Cluster
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Senlin permits policy objects to be attached to clusters and to be detached
from clusters dynamically. When attaching a policy object to a cluster, you
can customize the policy properties for the particular cluster. For example,
you can specify whether the policy should be enabled once attached. 

The following options are supported for the :command:`cluster-policy-attach`
command:

- :option:`--enabled` (or :option:`-e`): a boolean indicating whether the
  policy to be enabled once attached.

For example, the following command attaches a policy named ``up01`` to the
cluster ``c3``, with its enabled status set to ``True``::

  $ senlin cluster-policy-attach -e -p up01 c3

Note that most of the time, Senlin doesn't more than one policy of the same
type to be attached to the same cluster. This restriction is relaxed for some
policy types. For example, when working with policies about scaling, you can
actually attach more than one policy instances to the same cluster, each of
which is about a specific scenario.

For the identifiers specified for the cluster and the policy, you can use the
name, the ID or the "short ID" of an object. The Senlin engine will try make a
guess on each case. If no entity matches the specified identifier or there are
more than one entity matching the identifier, you will get an error message.


Showing Policy Properties on a Cluster
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

To examine the detailed properties of a policy object that has been attached
to a cluster, you can use the command :command:`cluster-policy-show` with the
policy identifier and the cluster identifier specified. For example::

  $ senlin cluster-policy-show -p dp01 c3
  +--------------+--------------------------------------+
  | Property     | Value                                |
  +--------------+--------------------------------------+
  | cluster_id   | 2b7e9294-b5cd-470f-b191-b18f7e672495 |
  | cluster_name | c3                                   |
  | enabled      | True                                 |
  | policy       | dp01                                 |
  | policy_id    | 239d7212-6196-4a89-9446-44d28717d7de |
  | type         | senlin.policy.deletion-1.0           |
  +--------------+--------------------------------------+

You can use the name, the ID or the "short ID" of a policy and/or a cluster to
name the objects.


Updating Policy Properties on a Cluster
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Once a policy is attached to a cluster, you can request its property on this
cluster be changed by using the command :command:`cluster-policy-update`. At 
this stage, you can specify the ``enabled`` property to be updated.

For example, the following command disables a policy on the specified cluster::

  $ senlin cluster-policy-update -e False -p dp01 mycluster

The Senlin engine will perform validation of the arguments in the same way as
that for the policy attach operation. You can use the name, the ID or the
"short ID" of an entity to reference it, as you do with the policy attach
operation as well.


Detach a Policy from a Cluster
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Finally, to remove the binding between a specified policy object from a
cluster, you can use the :command:`cluster-policy-detach` command as shown
below::

  $ senlin cluster-policy-detach -p dp01 mycluster

This command will detach the specified policy from the specified cluster.
You will use the option :option:`--policy` (or `-p`) to specify the policy.
