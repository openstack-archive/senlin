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


.. _ref-profiles:

========
Profiles
========

Concept
~~~~~~~

A :term:`Profile` is the mould used for creating a :term:`Node` to be managed
by the Senlin service. It can be treated as an instance of a
:term:`Profile Type` with a unique ID. A profile encodes the information
needed for node creation in a property named ``spec``.

The primary job for a profile type implementation is to translate user provided
JSON data structure into information that can be consumed by a driver. A
driver will create/delete/update a physical object based on the information
provided.


Listing Profiles
~~~~~~~~~~~~~~~~

To examine the list of profile objects supported by the Senlin engine, you can
use the following command::

  $ openstack cluster profile list
  +----------+----------+--------------------+---------------------+
  | id       | name     | type               | created_at          |
  +----------+----------+--------------------+---------------------+
  | 560a8f9d | myserver | os.nova.server-1.0 | 2015-05-05T13:26:00 |
  | ceda64bd | mystack  | os.heat.stack-1.0  | 2015-05-05T13:26:25 |
  | 9b127538 | pstack   | os.heat.stack-1.0  | 2015-06-25T12:59:01 |
  +----------+----------+--------------------+---------------------+

Note that the first column in the output table is a *short ID* of a profile
object. Senlin command line use short IDs to save real estate on screen so
that more useful information can be shown on a single line. To show the *full
ID* in the list, you can add the :option:`--full-id` option to the command::

  $ openstack cluster profile list --full-id
  +-------------------+----------+--------------------+---------------------+
  | id                | name     | type               | created_at          |
  +-------------------+----------+--------------------+---------------------+
  | 560a8f9d-7596-... | myserver | os.nova.server-1.0 | 2015-05-05T13:26:00 |
  | ceda64bd-70b7-... | mystack  | os.heat.stack-1.0  | 2015-05-05T13:26:25 |
  | 9b127538-a675-... | pstack   | os.heat.stack-1.0  | 2015-06-25T12:59:01 |
  +-------------------+----------+--------------------+---------------------+

The ``id`` column above contains the full UUID of profiles.

Sorting the List
----------------

You can specify the sorting keys and sorting direction when list profiles,
using the option :option:`--sort`. The :option:`--sort` option accepts a
string of format ``key1[:dir1],key2[:dir2],key3[:dir3]``, where the keys used
are profile properties and the dirs can be one of ``asc`` and ``desc``. When
omitted, Senlin sorts a given key using ``asc`` as the default direction.

For example, the following command sorts the profiles using the ``name``
property in descending order::

  $ openstack cluster profile list --sort name:desc

When sorting the list of profiles, you can use one of ``type``, ``name``,
``created_at`` and ``updated_at``.


Filtering the List
------------------

The :program:`openstack cluster profile list` command also provides options
for filtering the profile list at the server side. The option
:option:`--filters` can be used for this purpose. For example, the following
command filters the profile by the ``type`` field::

  $ openstack cluster profile list --filter "type=os.heat.stack-1.0"
  +----------+----------+--------------------+---------------------+
  | id       | name     | type               | created_at          |
  +----------+----------+--------------------+---------------------+
  | ceda64bd | mystack  | os.heat.stack-1.0  | 2015-05-05T13:26:25 |
  | 9b127538 | pstack   | os.heat.stack-1.0  | 2015-06-25T12:59:01 |
  +----------+----------+--------------------+---------------------+

The option :option:`--filters` accepts a list of key-value pairs separated
by semicolon (``;``), where each key-value pair is expected to be of format
``<key>=<value>``. The valid keys for filtering include: ``name`` and
``type``.


Paginating the List
-------------------

In case you have a huge collection of profile objects, you can limit the
number of profiles returned from Senlin server, using the option
:option:`--limit <LIMIT>`. For example::

  $ openstack cluster profile list --limit 1
  +----------+----------+--------------------+---------------------+
  | id       | name     | type               | created_at          |
  +----------+----------+--------------------+---------------------+
  | 560a8f9d | myserver | os.nova.server-1.0 | 2015-05-05T13:26:00 |
  +----------+----------+--------------------+---------------------+

Yet another option you can specify is the ID of a profile object after which
you want to see the list starts. In other words, you don't want to see those
profiles with IDs is or come before the one you specify. You can use the
option :option:`--marker <ID>` for this purpose. For example::

  $ openstack cluster profile list --limit 1 \
      --marker ceda64bd-70b7-4711-9526-77d5d51241c5
  +----------+--------+-------------------+---------------------+
  | id       | name   | type              | created_at          |
  +----------+--------+-------------------+---------------------+
  | 9b127538 | pstack | os.heat.stack-1.0 | 2015-06-25T12:59:01 |
  +----------+--------+-------------------+---------------------+


Creating a Profile
~~~~~~~~~~~~~~~~~~

Before working with a :term:`Cluster` or a :term:`Node`, you will need a
:term:`Profile` object created with a profile type. To create a profile, you
will need a "spec" file in YAML format. For example, below is a simple spec
for the ``os.heat.stack`` profile type (the source can be found in the
:file:`/examples/profiles/heat_stack/random_string/
heat_stack_random_string.yaml` file).

::

  type: os.heat.stack
  version: 1.0
  properties:
    name: random_string_stack
    template: random_string_stack.yaml
    context:
      region_name: RegionOne

The ``random_string_stack.yaml`` is the name of a Heat template file to be used
for stack creation. It is given here only as an example. You can
decide which properties to use based on your requirements.

Now you can create a profile using the following command::

  $ cd /opt/stack/senlin/examples/profiles/heat_stack/random_string
  $ openstack cluster profile create \
      --spec heat_stack_random_string.yaml \
      my_stack
  +------------+-------------------------------------------------------------+
  | Field      | Value                                                       |
  +------------+-------------------------------------------------------------+
  | created_at | 2015-07-01T03:13:23                                         |
  | domain_id  | None                                                        |
  | id         | c0389712-9c1a-4c58-8ba7-caa61b34b8b0                        |
  | location   | None                                                        |
  | metadata   | {}                                                          |
  | name       | my_stack                                                    |
  | project_id | 333acb15a43242f4a609a27cb097a8f2                            |
  | spec       | +------------+--------------------------------------------+ |
  |            | | property   | value                                      | |
  |            | +------------+--------------------------------------------+ |
  |            | | version    | 1.0                                        | |
  |            | | type       | "os.heat.stack"                            | |
  |            | | properties | {                                          | |
  |            | |            |   "files": {                               | |
  |            | |            |     "file:///...": "<file contents>"       | |
  |            | |            |   },                                       | |
  |            | |            |   "disable_rollback": true,                | |
  |            | |            |   "template": {                            | |
  |            | |            |     "outputs": {                           | |
  |            | |            |       "result": {                          | |
  |            | |            |         "value": {                         | |
  |            | |            |           "get_attr": [                    | |
  |            | |            |             "random",                      | |
  |            | |            |             "value"                        | |
  |            | |            |           ]                                | |
  |            | |            |         }                                  | |
  |            | |            |       }                                    | |
  |            | |            |     },                                     | |
  |            | |            |     "heat_template_version": "2014-10-16", | |
  |            | |            |     "resources": {                         | |
  |            | |            |       "random": {                          | |
  |            | |            |         "type": "OS::Heat::RandomString",  | |
  |            | |            |         "properties": {                    | |
  |            | |            |           "length": 64                     | |
  |            | |            |         }                                  | |
  |            | |            |       }                                    | |
  |            | |            |     },                                     | |
  |            | |            |     "parameters": {                        | |
  |            | |            |       "file": {                            | |
  |            | |            |         "default": {                       | |
  |            | |            |           "get_file": "file:///..."        | |
  |            | |            |         },                                 | |
  |            | |            |         "type": "string"                   | |
  |            | |            |       }                                    | |
  |            | |            |     }                                      | |
  |            | |            |   },                                       | |
  |            | |            |   "parameters": {},                        | |
  |            | |            |   "timeout": 60,                           | |
  |            | |            |   "environment": {                         | |
  |            | |            |     "resource_registry": {                 | |
  |            | |            |       "os.heat.server": "OS::Heat::Server" | |
  |            | |            |     }                                      | |
  |            | |            |   },                                       | |
  |            | |            |   "context": {                             | |
  |            | |            |     "region_name": "RegionOne"             | |
  |            | |            |   }                                        | |
  |            | |            | }                                          | |
  |            | +------------+--------------------------------------------+ |
  | type       | os.heat.stack-1.0                                           |
  | updated_at | None                                                        |
  | user_id    | 5e5bf8027826429c96af157f68dc9072                            |
  +------------+-------------------------------------------------------------+

From the outputs, you can see that the profile is created with a new ``id``
generated. The ``spec`` property is dumped for the purpose of verification.

Optionally, you can attach some key-value pairs to the new profile when
creating it. This data is referred to as the *metadata* for the profile::

  $ openstack cluster profile create \
      --spec heat_stack_random_string.yaml \
      --metadata "author=Tom;version=1.0" \
      my_stack

  $ openstack cluster profile create \
      --spec heat_stack_random_string.yaml \
      --metadata author=Tom --metadata version=1.0 \
      my_stack


Showing the Details of a Profile
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Once there are profile objects in Senlin database, you can use the following
command to show the properties of a profile::

  $ openstack cluster profile show myserver
  +------------+---------------------------------------------------------+
  | Field      | Value                                                   |
  +------------+---------------------------------------------------------+
  | created_at | 2015-07-01T03:18:58                                     |
  | domain_id  | None                                                    |
  | id         | 70a36cc7-9fc7-460e-98f6-d44e3302e604                    |
  | location   | None                                                    |
  | metadata   | {}                                                      |
  | name       | my_server                                               |
  | project_id | 333acb15a43242f4a609a27cb097a8f2                        |
  | spec       | +------------+----------------------------------------+ |
  |            | | property   | value                                  | |
  |            | +------------+----------------------------------------+ |
  |            | | version    | 1.0                                    | |
  |            | | type       | "os.nova.server"                       | |
  |            | | properties | {                                      | |
  |            | |            |   "key_name": "oskey",                 | |
  |            | |            |   "flavor": 1,                         | |
  |            | |            |   "networks": [                        | |
  |            | |            |     {                                  | |
  |            | |            |       "network": "private"             | |
  |            | |            |     }                                  | |
  |            | |            |   ],                                   | |
  |            | |            |   "image": "cirros-0.3.2-x86_64-uec",  | |
  |            | |            |   "name": "cirros_server"              | |
  |            | |            | }                                      | |
  |            | +------------+----------------------------------------+ |
  | type       | os.nova.server-1.0                                      |
  | update_at  | None                                                    |
  | user_id    | 5e5bf8027826429c96af157f68dc9072                        |
  +------------+---------------------------------------------------------+

Note that :program:`openstack cluster` command line accepts one of the
following values when retrieving a profile object:

- name: the name of a profile;
- ID: the UUID of a profile;
- short ID: an "abbreviated version" of the profile UUID.

Since Senlin doesn't require a profile name to be unique, specifying profile
name for the :command:`openstack cluster profile show` command won't guarantee
that a profile object is returned. You may get a ``MultipleChoices`` exception
if more than one profile object match the name.

As another option, when retrieving a profile (or in fact any other objects,
e.g. a cluster, a node, a policy etc.), you can specify the leading sub-string
of an UUID as the "short ID" for query. For example::

  $ openstack cluster profile show 70a36cc7
  +------------+---------------------------------------------------------+
  | Field      | Value                                                   |
  +------------+---------------------------------------------------------+
  | created_at | 2015-07-01T03:18:58                                     |
  | domain_id  | None                                                    |
  | id         | 70a36cc7-9fc7-460e-98f6-d44e3302e604                    |
  | location   | None                                                    |
  | metadata   | {}                                                      |
  | name       | my_server                                               |
  | project_id | 333acb15a43242f4a609a27cb097a8f2                        |
  | spec       | +------------+----------------------------------------+ |
  |            | | property   | value                                  | |
  |            | +------------+----------------------------------------+ |
  |            | | version    | 1.0                                    | |
  |            | | type       | "os.nova.server"                       | |
  |            | | properties | {                                      | |
  |            | |            |   "key_name": "oskey",                 | |
  |            | |            |   "flavor": 1,                         | |
  |            | |            |   "networks": [                        | |
  |            | |            |     {                                  | |
  |            | |            |       "network": "private"             | |
  |            | |            |     }                                  | |
  |            | |            |   ],                                   | |
  |            | |            |   "image": "cirros-0.3.2-x86_64-uec",  | |
  |            | |            |   "name": "cirros_server"              | |
  |            | |            | }                                      | |
  |            | +------------+----------------------------------------+ |
  | type       | os.nova.server-1.0                                      |
  | update_at  | None                                                    |
  | user_id    | 5e5bf8027826429c96af157f68dc9072                        |
  +------------+---------------------------------------------------------+
    $ openstack cluster profile show 70a3
  +------------+---------------------------------------------------------+
  | Field      | Value                                                   |
  +------------+---------------------------------------------------------+
  | created_at | 2015-07-01T03:18:58                                     |
  | domain_id  | None                                                    |
  | id         | 70a36cc7-9fc7-460e-98f6-d44e3302e604                    |
  | location   | None                                                    |
  | metadata   | {}                                                      |
  | name       | my_server                                               |
  | project_id | 333acb15a43242f4a609a27cb097a8f2                        |
  | spec       | +------------+----------------------------------------+ |
  |            | | property   | value                                  | |
  |            | +------------+----------------------------------------+ |
  |            | | version    | 1.0                                    | |
  |            | | type       | "os.nova.server"                       | |
  |            | | properties | {                                      | |
  |            | |            |   "key_name": "oskey",                 | |
  |            | |            |   "flavor": 1,                         | |
  |            | |            |   "networks": [                        | |
  |            | |            |     {                                  | |
  |            | |            |       "network": "private"             | |
  |            | |            |     }                                  | |
  |            | |            |   ],                                   | |
  |            | |            |   "image": "cirros-0.3.2-x86_64-uec",  | |
  |            | |            |   "name": "cirros_server"              | |
  |            | |            | }                                      | |
  |            | +------------+----------------------------------------+ |
  | type       | os.nova.server-1.0                                      |
  | update_at  | None                                                    |
  | user_id    | 5e5bf8027826429c96af157f68dc9072                        |
  +------------+---------------------------------------------------------+

As with query by name, a "short ID" won't guarantee that a profile object is
returned even if it does exist. When there are more than one object matching
the short ID, you will get a ``MultipleChoices`` exception.


Updating a Profile
~~~~~~~~~~~~~~~~~~

In general, a profile object should not be updated after creation. This is a
restriction to keep cluster and node status consistent at any time. However,
considering that there are cases where a user may want to change some
properties of a profile, :program:`openstack cluster` command line does
support the :command:`profile update` sub-command. For example, the following
command changes the name of a profile to ``new_server``::

  $ openstack cluster profile update --name new_server myserver

The following command creates or updates the metadata associated with the given
profile::

  $ openstack cluster profile update --metadata version=2.2 myserver

Changing the "spec" of a profile is not allowed. The only way to make a change
is to create a new profile using the :command:`profile create` sub-command.


Deleting a Profile
~~~~~~~~~~~~~~~~~~

When there are no clusters or nodes referencing a profile object, you can
delete it from the Senlin database using the following command::

  $ openstack cluster profile delete myserver

Note that in this command you can use the name, the ID or the "short ID" to
specify the profile object you want to delete. If the specified criteria
cannot match any profiles, you will get a ``ResourceNotFound`` exception.If
more than one profile matches the criteria, you will get a ``MultipleChoices``
exception. For example::

  $ openstack cluster profile delete my
  ERROR(404): The profile (my) could not be found.
  Failed to delete any of the specified profile(s).


See Also
~~~~~~~~

The following is a list of the links to documents related to profile's
creation and usage:

- :doc:`Working with Profile Types <profile_types>`
- :ref:`Nova Profile <ref-nova-profile>`
- :ref:`Stack Profile <ref-stack-profile>`
- :ref:`Docker Profile <ref-docker-profile>`
- :doc:`Creating and Managing Clusters <clusters>`
- :doc:`Creating and Managing Nodes <nodes>`
- :doc:`Managing Cluster Membership <membership>`
- :doc:`Examining Actions <actions>`
- :doc:`Browsing Events <events>`
