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


.. _ref-actions:


=======
Actions
=======

Concept
~~~~~~~

An :term:`Action` is an operation that can be performed on a :term:`cluster`
or a :term:`node`. Each action is executed asynchronously by a worker thread
after being created. Most Senlin APIs are executed asynchronously inside the
Senlin engine except for some object retrieval or object listing APIs.

Different types of objects support different sets of actions. For example, a
cluster object supports the following actions:

* ``CREATE``: creates a cluster;
* ``DELETE``: deletes a cluster;
* ``UPDATE``: update the properties and/or the profile used by a cluster;
* ``ADD_NODES``: add existing nodes to a cluster;
* ``DEL_NODES``: remove nodes from a cluster;
* ``ATTACH_POLICY``: attach the specified policy to a cluster;
* ``DETACH_POLICY``: detach the specified policy from a cluster;
* ``UPDATE_POLICY``: update the specified policy on a cluster;
* ``SCALE_IN``: shrink the size of a cluster;
* ``SCALE_OUT``: inflate the size of a cluster;
* ``RESIZE``: resize a cluster;

A node object supports the following actions:

* ``CREATE``: creates a node;
* ``DELETE``: deletes a node;
* ``UPDATE``: updates the properties and/or the profile used by a node;

In future, Senlin may support user defined actions (UDAs).


Listing Actions
~~~~~~~~~~~~~~~

The following command shows the actions known by the Senlin engine::

  $ openstack cluster action list
  +----------+-------------------------+----------------+-----------+----------+------------+-------------+
  | id       | name                    | action         | status    | target   | depends_on | depended_by |
  +----------+-------------------------+----------------+-----------+----------+------------+-------------+
  | 1189f5e8 | node_create_b825fb74    | NODE_CREATE    | SUCCEEDED | b825fb74 |            |             |
  | 2454c28a | node_delete_c035c519    | NODE_DELETE    | SUCCEEDED | c035c519 |            |             |
  | 252b9491 | node_create_c035c519    | NODE_CREATE    | SUCCEEDED | c035c519 |            |             |
  | 34802f3b | cluster_create_7f37e191 | CLUSTER_CREATE | SUCCEEDED | 7f37e191 |            |             |
  | 4250bf29 | cluster_delete_7f37e191 | CLUSTER_DELETE | SUCCEEDED | 7f37e191 |            |             |
  | 67cbcfb5 | node_delete_b825fb74    | NODE_DELETE    | SUCCEEDED | b825fb74 |            |             |
  | 6e661db8 | cluster_create_44762dab | CLUSTER_CREATE | SUCCEEDED | 44762dab |            |             |
  | 7bfad7ed | node_delete_b716052d    | NODE_DELETE    | SUCCEEDED | b716052d |            |             |
  | b299cf44 | cluster_delete_44762dab | CLUSTER_DELETE | SUCCEEDED | 44762dab |            |             |
  | e973552e | node_create_b716052d    | NODE_CREATE    | SUCCEEDED | b716052d |            |             |
  +----------+-------------------------+----------------+-----------+----------+------------+-------------+

The :program:`openstack cluster` command line supports various options when
listing the actions.


Sorting the List
----------------

You can specify the sorting keys and sorting direction when list actions,
using the option :option:`--sort`. The :option:`--sort` option accepts a
string of format ``key1[:dir1],key2[:dir2],key3[:dir3]``, where the keys used
are action properties and the dirs can be one of ``asc`` and ``desc``. When
omitted, Senlin sorts a given key using ``asc`` as the default direction.

For example, the following command instructs the :program:`openstack cluster`
command to sort actions using the ``name`` property in descending order::

  $ openstack cluster action list --sort name:desc

When sorting the list of actions, you can use one of ``name``, ``target``,
``action``, ``created_at`` and ``status``.


Filtering the List
------------------

You can filter the list of actions using the :option:`--filters``. For example,
the following command filters the action list by the ``action`` property::

  $ openstack cluster action list --filters action=CLUSTER_SCALE_OUT

The option :option:`--filters` accepts a list of key-value pairs separated by
semicolon (``;``), where each pair is expected to be of format ``key=val``.
The valid keys for filtering include ``name``, ``target``, ``action`` and
``status`` or any combination of them.


Paginating the Query results
----------------------------

In case you have a huge collection of actions (which is highly likely the
case), you can limit the number of actions returned using the option
:option:`--limit <LIMIT>`. For example::

  $ openstack cluster action list --limit 1

Another option you can specify is the ID of an action after which you want to
see the returned list starts. In other words, you don't want to see those
actions with IDs that is or come before the one you specify. You can use the
option :option:`--marker <ID>` for this purpose. For example::

  $ openstack cluster action list --limit 1 \
      --marker 2959122e-11c7-4e82-b12f-f49dc5dac270

Only 1 action record is returned in this example and its UUID comes after the
the one specified from the command line.


Showing Details of an Action
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

You can use the :program:`openstack cluster` command to show the details about
an action you are interested in. When specifying the identity of the action,
you can use its name, its ID or its "short ID" . Senlin API and engine will
verify if the identifier you specified can uniquely identify an action. An
error message will be returned if there is no action matching the identifier
or if more than one action matching it.

An example is shown below::

  $ openstack cluster action show 8fac487f
  +---------------+--------------------------------------+
  | Property      | Value                                |
  +---------------+--------------------------------------+
  | action        | CLUSTER_DELETE                       |
  | cause         | RPC Request                          |
  | depended_by   | []                                   |
  | depends_on    | []                                   |
  | end_time      | 1450683904.0                         |
  | id            | 8fac487f-861a-449e-9678-478133bea8de |
  | inputs        | {}                                   |
  | interval      | -1                                   |
  | name          | cluster_delete_7deb546f              |
  | outputs       | {}                                   |
  | start_time    | 1450683904.0                         |
  | status        | SUCCEEDED                            |
  | status_reason | Action completed successfully.       |
  | target        | 7deb546f-fd1f-499a-b120-94f8f07fadfb |
  | timeout       | 3600                                 |
  +---------------+--------------------------------------+


See Also
~~~~~~~~

* :doc:`Creating Receivers <receivers>`
* :doc:`Browsing Events <events>`
