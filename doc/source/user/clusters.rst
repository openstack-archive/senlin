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


.. _ref-clusters:

========
Clusters
========

Concept
~~~~~~~

A :term:`Cluster` is a group of logical objects, each of which is called a
:term:`Node` in Senlin's terminology. A cluster can contain zero or more
nodes. A cluster has a ``profile_id`` property that specifies which
:term:`Profile` to use when new nodes are created as members the cluster.

Senlin provides APIs and command line supports to manage the cluster
membership. Please refer to :ref:`ref-membership` for details. Senlin also
supports attaching :term:`Policy` objects to a cluster, customizing the policy
properties when attaching a policy to a cluster. Please refer to
:ref:`ref-bindings` for details.

Listing Clusters
~~~~~~~~~~~~~~~~

The following command shows the clusters managed by the Senlin service::

  $ openstack cluster list
  +----------+------+--------+---------------------+
  | id       | name | status | created_at          |
  +----------+------+--------+---------------------+
  | 2959122e | c1   | ACTIVE | 2015-05-05T13:27:28 |
  | 092d0955 | c2   | ACTIVE | 2015-05-05T13:27:48 |
  +----------+------+--------+---------------------+

Note that the first column in the output table is a *short ID* of a cluster
object. Senlin command line use short IDs to save real estate on screen so
that more useful information can be shown on a single line. To show the *full
ID* in the list, you can add the :option:`--full-id` option to the command::

  $ openstack cluster list --full-id
  +--------------------+------+--------+---------------------+------------+
  | id                 | name | status | created_at          | updated_at |
  +--------------------+------+--------+---------------------+------------+
  | 2959122e-11c7-.... | c1   | ACTIVE | 2015-05-05T13:27:28 | None       |
  | 092d0955-2645-.... | c2   | ACTIVE | 2015-05-05T13:27:48 | None       |
  +--------------------+------+--------+---------------------+------------+


Sorting the List
----------------

You can specify the sorting keys and sorting direction when list clusters,
using the option :option:`--sort`. The :option:`--sort` option accepts a
string of format ``key1[:dir1],key2[:dir2],key3[:dir3]``, where the keys used
are cluster properties and the dirs can be one of ``asc`` and ``desc``. When
omitted, Senlin sorts a given key using ``asc`` as the default direction.

For example, the following command sorts the clusters using the ``name``
property in descending order::

  $ openstack cluster list --sort name:desc

When sorting the list of clusters, you can use one of ``name``, ``status``,
``init_at``, ``created_at`` and ``updated_at``.


Filtering the List
------------------

The :program:`openstack cluster list` command also provides options for
filtering the cluster list at the server side. The option :option:`--filters`
can be used for this purpose. For example, the following command filters the
clusters by the ``status`` field::

  $ openstack cluster list --filters status=ACTIVE
  +----------+------+--------+---------------------+
  | id       | name | status | created_at          |
  +----------+------+--------+---------------------+
  | 2959122e | c1   | ACTIVE | 2015-05-05T13:27:28 |
  | 092d0955 | c2   | ACTIVE | 2015-05-05T13:27:48 |
  +----------+------+--------+---------------------+

The option :option:`--filters` accepts a list of key-value pairs separated by
semicolon (``;``), where each key-value pair is expected to be of format
``<key>=<value>``. The valid keys for filtering include: ``status``, ``name``,
``project`` and ``user``.


Paginating the Query Results
----------------------------

In case you have a huge collection of clusters, you can limit the number of
clusters returned from Senlin server each time, using the option
:option:`--limit <LIMIT>`. For example::

  $ openstack cluster list --limit 1
  +----------+------+--------+---------------------+
  | id       | name | status | created_at          |
  +----------+------+--------+---------------------+
  | 2959122e | c1   | ACTIVE | 2015-05-05T13:27:28 |
  +----------+------+--------+---------------------+

Another option you can specify is the ID of a cluster after which you want to
see the returned list starts. In other words, you don't want to see those
clusters with IDs that is or come before the one you specify. You can use the
option :option:`--marker <ID>` for this purpose. For example::

  $ openstack cluster list --limit 1 \
      --marker 2959122e-11c7-4e82-b12f-f49dc5dac270
  +----------+------+--------+---------------------+
  | id       | name | status | created_at          |
  +----------+------+--------+---------------------+
  | 092d0955 | c2   | ACTIVE | 2015-05-05T13:27:48 |
  +----------+------+--------+---------------------+

Only 1 cluster record is returned in this example and its UUID comes after the
the one specified from the command line.


Creating a Cluster
~~~~~~~~~~~~~~~~~~

To create a cluster, you need to provide the ID or name of the profile to be
associated with the cluster. For example::

  $ openstack cluster create --profile qstack c3
  +------------------+--------------------------------------+
  | Property         | Value                                |
  +------------------+--------------------------------------+
  | created_at       | None                                 |
  | data             | {}                                   |
  | desired_capacity | 0                                    |
  | domain           | None                                 |
  | id               | 60424eb3-6adf-4fc3-b9a1-4a035bf171ac |
  | max_size         | -1                                   |
  | metadata         | {}                                   |
  | min_size         | 0                                    |
  | name             | c3                                   |
  | nodes            |                                      |
  | profile_id       | bf38dc9f-d204-46c9-b515-79caf1e45c4d |
  | profile_name     | qstack                               |
  | project          | 333acb15a43242f4a609a27cb097a8f2     |
  | status           | INIT                                 |
  | status_reason    | Initializing                         |
  | timeout          | None                                 |
  | updated_at       | None                                 |
  | user             | 0b82043b57014cd58add97a2ef79dac3     |
  +------------------+--------------------------------------+

From the output you can see that a new cluster object created and put to
``INIT`` status. Senlin will verify if profile specified using the option
:option:`--profile <PROFILE>` does exist. The server allows the ``<PROFILE>``
value to be a profile name, a profile ID or the short ID of a profile object.
If the profile is not found or multiple profiles found matching the value, you
will receive an error message.


Controlling Cluster Capacity
----------------------------

When creating a cluster, by default :program:`senlin` will create a cluster
with no nodes, i.e. the ``desired_capacity`` will be set to 0. However, you
can specify the desired capacity of the cluster, the maximum size and/or the
minimum size of the cluster. The default value for ``min_size`` is 0 and the
default value for ``max_size`` is -1, meaning that there is no upper bound for
the cluster size.

The following command creates a cluster named "``test_cluster``", with its
desired capacity set to 2, its minimum size set to 1 and its maximum size set
to 3::

  $ openstack cluster create --desired_capacity 2 \
      --min-size 1 --max-size 3 \
      --profile myprofile \
      test_cluster

Senlin API and Senlin engine will validate the settings for these capacity
arguments when receiving this request. An error message will be returned if
the arguments fail to pass this validation, or else the cluster creation
request will be queued as an action for execution.

When ``desired_capacity`` is not specified and ``min_size`` is not specified,
Senlin engine will create an empty cluster. When either ``desired_capacity``
or ``min_size`` is specified, Senlin will start the process of creating nodes
immediately after the cluster object is created.


Other Properties
----------------

You can use the option :option:`--metadata` (or :option:`-M`) to associate
some key-value pairs to the cluster to be created. These data are referred to
as the "metadata" for the cluster.

Since cluster operations may take some time to finish when being executed and
Senlin interacts with the backend services to make it happen, there needs a
way to verify whether an operation has timed out. When creating a cluster
using the :program:`opentack cluster create` command line, you can use the
option :option:`--timeout <TIMEOUT>` to specify the default time out in number
of seconds. This value would be the global setting for the cluster.


Showing Details of a Cluster
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

When there are clusters in the Senlin database, you can request Senlin to show
the details about a cluster you are intested in.

You can use the name, the ID or the "short ID" of a cluster to name a cluster
for show. Senlin API and engine will verify if the identifier you specified
can uniquely identify a cluster. An error message will be returned if there is
no cluster matching the identifier or if more than one cluster matching it.

An example is shown below::

  $ openstack cluster show c3
  +------------------+--------------------------------------+
  | Property         | Value                                |
  +------------------+--------------------------------------+
  | created_at       | 2015-07-07T03:30:53                  |
  | data             | {}                                   |
  | desired_capacity | 0                                    |
  | domain           | None                                 |
  | id               | 2b7e9294-b5cd-470f-b191-b18f7e672495 |
  | max_size         | -1                                   |
  | metadata         | {}                                   |
  | min_size         | 0                                    |
  | name             | c3                                   |
  | nodes            | b28692a5-2536-4921-985b-1142d6045e1f |
  |                  | 4be10a88-e340-4518-a9e1-d742c53ac37f |
  | profile_id       | bf38dc9f-d204-46c9-b515-79caf1e45c4d |
  | profile_name     | qstack                               |
  | project          | 333acb15a43242f4a609a27cb097a8f2     |
  | status           | ACTIVE                               |
  | status_reason    | Node stack2: Creation succeeded      |
  | timeout          | None                                 |
  | updated_at       | None                                 |
  | user             | 0b82043b57014cd58add97a2ef79dac3     |
  +------------------+--------------------------------------+

From the result, you can examine the list of nodes (if any) that are members
of this cluster.


Updating a Cluster
~~~~~~~~~~~~~~~~~~

Once a cluster has been created, you change its properties using the
:program:`openstack cluster update` command. For example, to change the name
of a cluster, you can use the following command::

  $ openstack cluster update --name web_bak web_servers

You can change the ``timeout`` property using option :option:`--timeout`.
You can change the metadata associated with cluster using option
:option:`--metadata`.

Using the :command:`openstack cluster update` command, you can change the
profile used by the cluster and its member nodes. The following example
launches a global update on the cluster for switching to a different profile::

  $ openstack cluster update --profile fedora21_server web_cluster

Suppose the cluster ``web_cluster`` is now using a profile of type
``os.nova.server`` where a Fedora 20 image is used, the command above will
initiate a global upgrade to a new profile where a Fedora 21 image is used.

Senlin engine will verify whether the new profile has the same profile type
with that of the existing one and whether the new profile has a well-formed
``spec`` property. If everything is fine, the engine will start a node level
profile update process. The node level update operation is subject to policy
checkings/enforcements when there is an update policy attached to the cluster.
Please refer to :ref:`ref-policies` and :ref:`ref-bindings` for more
information.


Resizing a Cluster
~~~~~~~~~~~~~~~~~~

The :program:`openstack cluster` command line supports several different
sub-commands to resize a cluster.


``openstack cluster resize``
----------------------------

The command :command:`openstack cluster resize` takes several arguments that
allow you to resize a cluster in various ways:

- you can change the size of a cluster to a specified number;
- you can add a specified number of nodes to a cluster or remove a specified
  number of nodes from a cluster;
- you can instruct :program:`openstack cluster resize` to resize a cluster by
  a specified percentage;
- you can tune the ``min_size`` and/or ``max_size`` property of a cluster when
  resizing it;
- you can request a size change made on a best-effort basis, if the resize
  operation cannot be fully realized due to some restrictions, this argument
  tells Senlin engine whether it is still expected to partially realize the
  resize operation.

You can specify one and only one of the following options for the
:command:`openstack cluster resize` command:

- use :option:`--capacity <CAPACITY>` (:option:`-c <CAPACITY>`) to specify
  the exact value of the new cluster size;
- use :option:`--adjustment <ADJUSTMENT>` (:option:`-a <ADJUSTMENT>`) to
  specify the relative number of nodes to add/remove;
- use :option:`--percentage <PERCENTAGE>` (:option:`-p <PERCENTAGE>`) to
  specify the percentage of cluster size change.

The following command resizes the cluster ``test_cluster`` to 2 nodes,
provided that the ``min_size`` is less than or equal to 2 and the ``max_size``
is either no less than 2 or equal to -1 (indicating that there is no upper
bound for the cluster size). This command makes use of the option
:option:`--capacity <CAPACITY>`, where ``<CAPACITY>`` is the new size of the
cluster::

  $ openstack cluster resize --capacity 2 test_cluster

Another way to resize a cluster is by specifying the :option:`--adjustment
<ADJUSTMENT>` option, where ``<ADJUSTMENT>`` can be a positive or a negative
integer giving the number of nodes to add or remove respectively. For example,
the following command adds two nodes to the specified cluster::

  $ openstack cluster resize --adjustment 2 test_cluster

The following command removes two nodes from the specified cluster::

  $ openstack cluster resize --adjustment -2 test_cluster

Yet another way to resize a cluster is by specifying the size change in
percentage. You will use the option :option:`--percentage <PERCENTAGE>` for
this purpose. The ``<PERCENTAGE>`` value can be either a positive float value
or a negative float value giving the percentage of cluster size. For example,
the following command increases the cluster size by 30%::

  $ openstack cluster resize --percentage 30 test_cluster

The following command decreases the cluster size by 25%::

  $ openstack cluster resize --percentage -25 test_cluster

Senlin engine computes the actual number of nodes to add or to remove based on
the current size of the cluster, the specified percentage value, the
constraints (i.e. the ``min_size`` and the ``max_size`` properties).

When computing the new capacity for the cluster, senlin engine will determine
the value based on the following rules:

- If the value of new capacity is greater than 1.0 or less than -1.0, it will
  be rounded to the integer part of the value. For example, 3.4 will be rounded
  to 3, -1.9 will be rounded to -1;
- If the value of the new capacity is between 0 and 1, Senlin will round it up
  to 1;
- If the value of the new capacity is between 0 and -1, Senlin will round it
  down to -1;
- The new capacity should be in the range of ``min_size`` and ``max_size``,
  inclusively, unless option :option:`--strict` is specified;
- The range checking will be performed against the current size constraints if
  no new value for ``min_size`` and/or ``max_size`` is given, or else Senlin
  will first verify the new size constraints and perform range checking
  against the new constraints;
- If option :option:`--min-step <MIN_STEP>` is specified, the ``<MIN_STEP>``
  value will be used if the absolute value of the new capacity value is less
  than ``<MIN_STEP>``.

If option :option:`--strict`` is specified, Senlin will strictly conform to
the cluster size constraints. If the capacity value falls out of the range,
the request will be rejected. When :option:`--strict` is set to ``False``,
Senlin engine will do a resize on a best-effort basis.

Suppose we have a cluster A with ``min_size`` set to 5 and its current size is
7. If the new capacity value is 4 and option :option:`--strict` is set to
``True``, the request will be rejected with an error message. If the new
capacity value is 4 and the option :option:`--strict` is not set, Senlin will
try resize the cluster to 5 nodes.

Along with the :command:`openstack cluster resize` command, you can specify
the new size constraints using either the option :option:`--min-size` or
the option :option:`--max-size` or both.


``openstack cluster shrink`` and ``openstack cluster expand``
-------------------------------------------------------------

The :command:`openstack cluster shrink` command and the
:command:`openstack cluster expand` command are provided for convenience when
you want to remove a specific number of nodes from a cluster or add a specific
number of nodes to a cluster, respectively. These two commands both take an
argument ``<COUNT>`` which is a positive integer representing the number of
nodes to add or remove. For example, the following command adds two nodes to
the ``web_servers`` cluster::

  $ openstack cluster expand --count 2 web_servers

The following command removes two nodes from the ``web_servers`` cluster::

  $ openstack cluster shrink --count 2 web_servers

The option :option:`--count <COUNT>` is optional. If this option is specified,
Senlin will use it for cluster size change, even when there are scaling
policies attached to the cluster. If this option is omitted, however, Senlin
will treat it as implicitly set to value 1.


Deleting a Cluster
~~~~~~~~~~~~~~~~~~

A cluster can be deleted using the :command:`openstack cluster delete`
command, for example::

  $ openstack cluster delete mycluster

Note that in this command you can use the name, the ID or the "short ID" to
specify the cluster object you want to delete. If the specified criteria
cannot match any clusters, you will get a ``ClusterNotFound`` error. If more
than one cluster matches the criteria, you will get a ``MultipleChoices``
error.

When there are nodes in the cluster, the Senlin engine will launch a process
to delete all nodes from the cluster and destroy them before deleting the
cluster object itself.


See Also
~~~~~~~~

There are other operations related to clusters. Please refer to the following
links for operations related to cluster membership management and the creation
and management of cluster-policy bindings:

- :doc:`Managing Cluster Membership <membership>`
- :doc:`Bindging Policies to Clusters <bindings>`
- :doc:`Examining Actions <actions>`
- :doc:`Browsing Events <events>`
