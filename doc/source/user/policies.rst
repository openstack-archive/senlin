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


.. _ref-policies:

========
Policies
========

Concept
~~~~~~~

A :term:`Policy` is an object instantiated from a :term:`Policy Type`. Once
created, it can be dynamically attached to or detached from a cluster. Such a
policy usually contains rules to be checked/enforced when certain
:term:`action` is about to be executed or has been executed.

One policy can be attached to many clusters, and one cluster can be attached
with many policies. In addition to this, a policy on a cluster can be
dynamically enabled or disabled. Please refer to :ref:`ref-bindings` for
details.


Listing Policies
~~~~~~~~~~~~~~~~

The :program:`openstack cluster` command line provides a sub-command
:command:`openstack cluster policy list` that can be used to enumerate policy
objects known to the service. For example::

  $ openstack cluster policy list
  +----------+------+-----------------------------+---------------------+
  | id       | name | type                        | created_at          |
  +----------+------+-----------------------------+---------------------+
  | 239d7212 | dp01 | senlin.policy.deletion-1.0  | 2015-07-11T04:24:34 |
  | 7ecfd026 | lb01 | senlin.policy.placement-1.0 | 2015-07-11T04:25:28 |
  +----------+------+-----------------------------+---------------------+

Note that the first column in the output table is a *short ID* of a policy
object. Senlin command line use short IDs to save real estate on screen so
that more useful information can be shown on a single line. To show the *full
ID* in the list, you can add the :option:`--full-id` option to the command.


Sorting the List
----------------

You can specify the sorting keys and sorting direction when list policies,
using the option :option:`--sort`. The :option:`--sort` option accepts a
string of format ``key1[:dir1],key2[:dir2],key3[:dir3]``, where the keys used
are policy properties and the dirs can be one of ``asc`` and ``desc``. When
omitted, Senlin sorts a given key using ``asc`` as the default direction.

For example, the following command sorts the policies using the ``name``
property in descending order::

  $ openstack cluster policy list --sort name:desc

When sorting the list of policies, you can use one of ``type``, ``name``,
``created_at`` and ``updated_at``.


Paginating the List
-------------------

In case you have a huge collection of policy objects, you can limit the number
of policies returned from Senlin server, using the option :option:`--limit`.
For example::

  $ openstack cluster policy list --limit 1
  +----------+------+----------------------------+---------------------+
  | id       | name | type                       | created_at          |
  +----------+------+----------------------------+---------------------+
  | 239d7212 | dp01 | senlin.policy.deletion-1.0 | 2015-07-11T04:24:34 |
  +----------+------+----------------------------+---------------------+

Yet another option you can specify is the ID of a policy object after which
you want to see the list starts. In other words, you don't want to see those
policies with IDs that is or come before the one you specify. You can use the
option :option:`--marker <ID>` for this purpose. For example::

  $ openstack cluster policy list --limit 1 \
      --marker 239d7212-6196-4a89-9446-44d28717d7de

Combining the :option:`--marker` option and the :option:`--limit` option
enables you to do pagination on the results returned from the server.


Creating a Policy
~~~~~~~~~~~~~~~~~

When creating a new policy object, you need a "spec" file in YAML format. You
may want to check the :command:`openstack cluster policy type show` command in
:ref:`ref-policy-types` for the property names and types for a specific
:term:`policy type`. For example, the following is a spec for the policy type
``senlin.policy.deletion`` (the source can be found in the
:file:`examples/policies/deletion_policy.yaml` file)::

  # Sample deletion policy that can be attached to a cluster.
  type: senlin.policy.deletion
  version: 1.0
  properties:
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

The properties in this spec file are specific to the ``senlin.policy.deletion``
policy type. To create a policy object using this "spec" file, you can use the
following command::

  $ opentack cluster policy create --spec deletion_policy.yaml dp01
  +------------+-----------------------------------------------------------+
  | Property   | Value                                                     |
  +------------+-----------------------------------------------------------+
  | created_at | None                                                      |
  | id         | c2e3cd74-bb69-4286-bf06-05d802c8ec12                      |
  | name       | dp01                                                      |
  | spec       | {                                                         |
  |            |   "version": 1.0,                                         |
  |            |   "type": "senlin.policy.deletion",                       |
  |            |   "description": "A policy for choosing victim node(s).", |
  |            |   "properties": {                                         |
  |            |     "destroy_after_deletion": true,                       |
  |            |     "grace_period": 60,                                   |
  |            |     "reduce_desired_capacity": false,                     |
  |            |     "criteria": "OLDEST_FIRST"                            |
  |            |   }                                                       |
  |            | }                                                         |
  | type       | None                                                      |
  | updated_at | None                                                      |
  +------------+-----------------------------------------------------------+


Showing the Details of a Policy
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

You can use the :command:`openstack cluster policy show` command to show the
properties of a policy. You need to provide an identifier to the command
line to indicate the policy object you want to examine. The identifier can be
the ID, the name or the "short ID" of a policy object. For example::

  $ openstack cluster policy show dp01
  +------------+------------------------------------------------------------+
  | Property   | Value                                                      |
  +------------+------------------------------------------------------------+
  | created_at | 2015-07-11T04:24:34                                        |
  | id         | c2e3cd74-bb69-4286-bf06-05d802c8ec12                       |
  | name       | dp01                                                       |
  | spec       | {                                                          |
  |            |   "version": 1.0,                                          |
  |            |   "type": "senlin.policy.deletion",                        |
  |            |   "description": "A policy for choosing victim node(s).",  |
  |            |   "properties": {                                          |
  |            |     "destroy_after_deletion": true,                        |
  |            |     "grace_period": 60,                                    |
  |            |     "reduce_desired_capacity": false,                      |
  |            |     "criteria": "OLDEST_FIRST"                             |
  |            |   }                                                        |
  |            | }                                                          |
  | type       | None                                                       |
  | updated_at | None                                                       |
  +------------+------------------------------------------------------------+

When there is no policy object matching the identifier, you will get an error
message. When there are more than one object matching the identifier, you will
get an error message as well.


Updating a Policy
~~~~~~~~~~~~~~~~~

After a policy object is created, you may want to change some properties of
it.  You can use the :command:`openstack cluster policy update` to change the
"``name``" of a policy. For example, the following command renames a policy
object from "``dp01``" to "``dp01_bak``"::

  $ openstack cluster policy update --name dp01_bak dp01

If the named policy object could not be found or the parameter value fails the
validation, you will get an error message.


Deleting a Policy
~~~~~~~~~~~~~~~~~

When there are no clusters referencing a policy object, you can delete it from
the Senlin database using the following command::

  $ openstack cluster policy delete dp01

Note that in this command you can use the name, the ID or the "short ID" to
specify the policy object you want to delete. If the specified criteria
cannot match any policy objects, you will get a ``PolicyNotFound`` exception.
If more than one policy matches the criteria, you will get an error message.


See Also
~~~~~~~~

The list below provides links to documents related to the creation and usage
of policy objects.

* :doc:`Working with Policy Types <policy_types>`
* :doc:`Managing the Bindings between Clusters and Policies <bindings>`
* :doc:`Browsing Events <events>`
