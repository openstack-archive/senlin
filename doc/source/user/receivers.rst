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

.. _ref-receivers:

========
Receiver
========

A :term:`Receiver` is used to prepare Senlin engine to react to external alarms
or events so that a specific :term:`Action` can be initiated on a senlin
cluster automatically. For example, when workload on a cluster climbs high,
a receiver can change the size of a specified cluster.


Listing Receivers
~~~~~~~~~~~~~~~~~

The :program:`openstack cluster` command line provides a sub-command
:command:`receiver list` that can be used to enumerate receiver objects known
to the service. For example::

  $ openstack cluster receiver list


Sorting the List
----------------

You can specify the sorting keys and sorting direction when list receivers,
using the option :option:`--sort`. The :option:`--sort` option accepts a
string of format ``key1[:dir1],key2[:dir2],key3[:dir3]``, where the keys used
are receiver properties and the dirs can be one of ``asc`` and ``desc``. When
omitted, Senlin sorts a given key using ``asc`` as the default direction.

For example, the following command sorts the receivers using the ``name``
property in descending order::

  $ openstack cluster receiver list --sort name:desc

When sorting the list of receivers, you can use one of ``type``, ``name``,
``action``, ``cluster_id``, ``created_at``.


Paginating the List
-------------------

In case you have a huge collection of receiver objects, you can limit the
number of receivers returned from Senlin server, using the option
:option:`--limit`. For example::

  $ openstack cluster receiver list --limit 1

Yet another option you can specify is the ID of a receiver object after which
you want to see the list starts. In other words, you don't want to see those
receivers with IDs that is or come before the one you specify. You can use the
option :option:`--marker <ID>` for this purpose. For example::

  $ openstack cluster receiver list \
      --limit 1 --marker 239d7212-6196-4a89-9446-44d28717d7de

Combining the :option:`--marker` option and the :option:`--limit` option
enables you to do pagination on the results returned from the server.


Creating and Using a Receiver
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Currently, Senlin supports two receiver types: "``webhook``" and "``message``".
For the former one, a permanent webhook url is generated for users to trigger
a specific action on a given cluster by sending a HTTP POST request. For the
latter one, a Zaqar message queue is created for users to post a message.
Such a message is used to notify the Senlin service to initiate an action on a
specific cluster.

Webhook Receiver
----------------

When creating a webhook receiver, you are expected to use the option
:option:`--cluster` to specify the target cluster and the option
:option:`--action` to specify the action name. By default, the
:program:`openstack cluster receiver create` command line creates a receiver
of type "``webhook``". User can also explicitly specify the receiver type
using the option :option:`--type`, for example:

.. code-block:: console

  $ openstack cluster receiver create \
     --cluster test-cluster \
     --action CLUSTER_SCALE_OUT \
     --type webhook \
     test-receiver
  +------------+-----------------------------------------------------------+
  | Field      | Value                                                     |
  +------------+-----------------------------------------------------------+
  | action     | CLUSTER_SCALE_OUT                                         |
  | actor      | {                                                         |
  |            |   "trust_id": "2e76547947954e6ea62b61a658ffb8e5"          |
  |            | }                                                         |
  | channel    | {                                                         |
  |            |   "alarm_url": "http://10.20.10.17:8777/v1/webhooks/...." |
  |            | }                                                         |
  | cluster_id | 9f1883a7-6837-4fe4-b621-6ec6ba6c3668                      |
  | created_at | 2018-02-24T09:23:48Z                                      |
  | domain_id  | None                                                      |
  | id         | 2a5a266d-0c3a-456c-bbb7-f8b26ef3b7f3                      |
  | location   | None                                                      |
  | name       | test-receiver                                             |
  | params     | {}                                                        |
  | project_id | bdeecc1b58004bb19302da77ac056b44                          |
  | type       | webhook                                                   |
  | updated_at | None                                                      |
  | user_id    | e1ddb7e7538845968789fd3a863de928                          |
  +------------+-----------------------------------------------------------+

Senlin service will return the receiver information with its channel ready to
receive HTTP POST requests. For a webhook receiver, this means you can check
the "``alarm_url``" field of the "``channel``" property. You can use this URL
to trigger the action you specified.

The following command triggers the receiver by sending a ``POST`` request to
the URL obtained from its ``channel`` property, for example:

.. code-block:: console

  $ curl -X POST <alarm_url>


Message Receiver
----------------

A message receiver is different from a webhook receiver in that it can trigger
different actions on different clusters. Therefore, option :option:`--cluster`
and option :option:`--action` can be omitted when creating a message receiver.
Senlin will check if the incoming message contains such properties.

You will need to specify the receiver type "``message``" using the option
:option:`--type` when creating a message receiver, for example:

.. code-block:: console

  $ openstack cluster receiver create \
      --type message \
      test-receiver

Senlin service will return the receiver information with its channel ready to
receive messages. For a message receiver, this means you can check the
"``queue_name``" field of the "``channel``" property.

Once a message receiver is created, you (or some software) can send messages
with the following format to the named Zaqar queue to request Senlin service:

.. code-block:: python

    {
      "messages": [
        {
          "ttl": 300,
          "body": {
            "cluster": "test-cluster",
            "action": "CLUSTER_SCALE_OUT",
            "params": {"count": 2}
          }
        }
      ]
    }

More examples on sending message to a Zaqar queue can be found here:

https://opendev.org/openstack/python-zaqarclient/src/branch/master/examples

.. note::

  Users are permitted to trigger multiple actions at the same time by sending
  more than one message to a Zaqar queue in the same request. In that case,
  the order of actions generated depends on how Zaqar sorts those messages.
