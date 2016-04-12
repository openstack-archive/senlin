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

The :program:`opentack cluster ` command line provides a sub-command
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


Creating a Receiver
~~~~~~~~~~~~~~~~~~~

1. Create a cluster named "``test_cluster``", with its desired capacity set to
   2, its minimum size set to 1 and its maximum size set to 5, e.g.

::

  $ openstack cluster create --profile $PROFILE_ID \
      --desired-capacity 2 --min-size 1 --max-size 5 \
      test-cluster

2. Attach a ScalingPolicy to the cluster:

::

  $ opentack cluster policy attach --policy $POLICY_ID test-cluster

3. Create a receiver, use the option :option:`--cluster` to specify
   "``test-cluster``" as the targeted cluster and use the option
   :option:`--action` to specify "``CLUSTER_SCALE_OUT``" or
   "``CLUSTER_SCALE_IN``" as the action name. By default, the
   :program:`openstack cluster receiver create` command line creates a
   receiver of type :term:`webhook`, for example:::

     $ openstack cluster receiver create \
         --cluster test-cluster \
         --action CLUSTER_SCALE_OUT \
         test-receiver

   Senlin service will return the receiver information with its channel ready
   to receive signals. For a webhook receiver, this means you can check the
   "``alarm_url``" field of the "``channel``" property. You can use this url
   to trigger the action you specified.

4. Trigger the receiver by sending a ``POST`` request to its URL, for example:

::

  curl -X POST <alarm_url>
