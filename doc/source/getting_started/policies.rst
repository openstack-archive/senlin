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


.. _guide-policies:

Policies
========

Concept
-------

A :term:`Policy` is an object instantiated from a :term:`Policy Type`. Once
created, it can be dynamically attached to or detached from a cluster. Such a
policy usually contains rules to be checked/enforced when certain
:term:`action` is about to be executed or has been executed.

One policy can be attached to many clusters, and one cluster can be attached
with many policies. When more than one policy is attached to a cluster, you
can specify the relative "priority" among the policy objects on the cluster.
In addition to this, a policy on a cluster can be dynamically enabled or
disabled. Please refer to :ref:`guide-bindings` for details.


Listing Policies
----------------

The :program:`senlin` command line provides a command :command:`policy-list`
that can be used to enumerate profile objects known to the service. For
example::

  $ senlin policy-list
  +----------+------+---------------------+-------+----------+---------------------+
  | id       | name | type                | level | cooldown | created_time        |
  +----------+------+---------------------+-------+----------+---------------------+
  | 239d7212 | dp01 | DeletionPolicy      | 0     | 0        | 2015-07-11T04:24:34 |
  | 7ecfd026 | lb01 | LoadBalancingPolicy | 0     | 0        | 2015-07-11T04:25:28 |
  +----------+------+---------------------+-------+----------+---------------------+

Note that the first column in the output table is a *short ID* of a policy
object. Senlin command line use short IDs to save real estate on screen so
that more useful information can be shown on a single line. To show the *full
ID* in the list, you can add the :option:`-F` (or :option:`--full-id`) option
to the command.

By default, the command :command:`policy-list` filters out policy objects
that have been soft deleted. However, you can add the `--show-deleted` (or
:option:`-D`) option to the command to indicate that soft-deleted policies
be included in the list.

In case you have a huge collection of policy objects, you can limit the number
of policies returned from Senlin server, using the option :option:`--limit` (or
(or `-l`). For example::

  $ senlin policy-list -l 1
  +----------+------+----------------+-------+----------+---------------------+
  | id       | name | type           | level | cooldown | created_time        |
  +----------+------+----------------+-------+----------+---------------------+
  | 239d7212 | dp01 | DeletionPolicy | 0     | 0        | 2015-07-11T04:24:34 |
  +----------+------+----------------+-------+----------+---------------------+

Yet another option you can specify is the ID of a policy object from which
you want to see the list starts. In other words, you don't want to see those
policies with IDs that come before the one you specify. You can use the option
:option:`--marker <ID>` (or option:`-m <ID>`) for this purpose. For example::

  $ senlin profile-list -l 1 -m 239d7212-6196-4a89-9446-44d28717d7de

Combining the :option:`-m` and the :option:`-l` enables you to do pagination
on the results returned from the server.


Creating a Policy
-----------------

When creating a new policy object, you need a "spec" file in YAML format. You
may want to check the :command:`policy-type-schema` command in
:ref:`guide-policy_types` for the property names and types for a specific
:term:`policy type`. For example, the following is a spec for the policy type
``DeletionPolicy`` (the source can be found in the
:file:`examples/policies/deletion_policy.spec` file)::

  # Sample deletion policy that can be attached to a cluster.

  # The valid values include:
  # OLDEST_FIRST, OLDEST_PROFILE_FIRST, YOUNGEST_FIRST, RANDOM
  criteria: OLDEST_FIRST

  # Whether deleted node should be destroyed
  destroy_after_deletion: True

  # Length in number of seconds before the actual deletion happens
  # This param buys an instance some time before deletion
  grace_period: 60

  # Whether the deletion will reduce the desired capability of
  # the cluster as well.
  reduce_desired_capacity: False

The properties in this spec file are specific to the ``DeletionPolicy`` policy
type. To create a policy object using this "spec" file, you can use the
following command::

  $ senlin policy-create -t DeletionPolicy -s deletion_policy.spec dp01
  +--------------+--------------------------------------+
  | Property     | Value                                |
  +--------------+--------------------------------------+
  | cooldown     | 0                                    |
  | created_time | None                                 |
  | deleted_time | None                                 |
  | id           | 239d7212-6196-4a89-9446-44d28717d7de |
  | level        | 0                                    |
  | name         | dp01                                 |
  | spec         | {                                    |
  |              |   "destroy_after_deletion": true,    |
  |              |   "grace_period": 60,                |
  |              |   "reduce_desired_capacity": false,  |
  |              |   "criteria": "OLDEST_FIRST"         |
  |              | }                                    |
  | type         | DeletionPolicy                       |
  | updated_time | None                                 |
  +--------------+--------------------------------------+


Showing the Details of a Policy
-------------------------------

You can use the :command:`policy-show` command to show the properties of a
profile. You need to provide an identifier to the :program:`senlin` command
line to indicate the policy object you want to examine. The identifier can be
the ID, the name or the "short ID" of a policy object. For example::

  $ senlin policy-show dp01
  +--------------+--------------------------------------+
  | Property     | Value                                |
  +--------------+--------------------------------------+
  | cooldown     | 0                                    |
  | created_time | 2015-07-11T04:24:34                  |
  | deleted_time | None                                 |
  | id           | 239d7212-6196-4a89-9446-44d28717d7de |
  | level        | 0                                    |
  | name         | dp01                                 |
  | spec         | {                                    |
  |              |   "destroy_after_deletion": true,    |
  |              |   "grace_period": 60,                |
  |              |   "reduce_desired_capacity": false,  |
  |              |   "criteria": "OLDEST_FIRST"         |
  |              | }                                    |
  | type         | DeletionPolicy                       |
  | updated_time | None                                 |
  +--------------+--------------------------------------+

When there is no policy object matching the identifier, you will get an error
message. When there are more than one object matching the identifier, you will
get an error message as well.


Updating a Policy
-----------------

After a policy object is created, you may want to change some properties of it.
You can use the :command:`policy-update` to change the "cooldown", the "name",
or the "enforcement level" of a policy by specifying an identifier. For
example, the following command renames a policy object from "``dp01``" to
"``dp01_bak``"::

  $ senlin policy-update -n dp01_bak dp01

The Senlin engine will validate if the new value for the named property is
acceptable. For example, the value for option :option:`--enforcement-level`
(or :option:`-l`) must be a value between 0 and 100; the value for the option
:option:`--cooldown` (or :option:`-c`) must be greater than or equal to 0.

If the named policy object could not be found or the parameter value fails the
validation, you will get an error message.


Deleting a Policy
-----------------

When there are no clusters referencing a policy object, you can delete it from
the Senlin database using the following command::

  $ senlin policy-delete dp01

Note that in this command you can use the name, the ID or the "short ID" to
specify the policy object you want to delete. If the specified criteria
cannot match any policy objects, you will get a ``PolicyNotFound`` exception.
If more than one policy matches the criteria, you will get an error message.


See Also
--------

The list below provides links to documents related to the creation and usage
of policy objects.

* :doc:`Working with Policy Types <policy_types>`
* :doc:`Managing the Bindings between Clusters and Policies <bindings>`
* :doc:`Browsing Events <events>`
