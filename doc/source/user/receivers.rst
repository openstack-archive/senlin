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

.. _guide-receivers:

========
Receiver
========

A :term:`Receiver` is used to prepare Senlin engine to react to external alarms
or events so that a specific :term:`Action` can be initiated on a senlin
cluster automatically. For example, when workload on a cluster climbs high,
a receiver can change the size of a specified cluster.

How to use
~~~~~~~~~~

1. Create a cluster named "``test_cluster``", with its desired capacity set to
   2, its minimum size set to 1 and its maximum size set to 5, e.g.

::

  senlin cluster-create -p $PROFILE_ID -c 2 -n 1 -m 5 test-cluster

2. Attach a ScalingPolicy to the cluster:

::

  senlin cluster-policy-attach -p $POLICY_ID test-cluster

3. Create a receiver, use the option :option:`-c` to specify `test-cluster` as
   the targeted cluster  and use the option :option:`-a` to specify
   `CLUSTER_SCALE_OUT` or `CLUSTER_SCALE_IN` as the action name. By default,
   the :program:`senlin` command line creates a receiver of type
   :term:`webhook`, for example:::

     senlin receiver-create -c test-cluster \
         -a CLUSTER_SCALE_OUT \
         test-receiver

   Senlin service will return the receiver information with its channel ready
   to receive signals. For a webhook receiver, this means you can check the
   ``alarm_url`` field of the ``channel`` property. You can use this url to
   trigger the action you specified.

4. Trigger the receiver by sending a ``POST`` request to its URL, for example:

::

  curl -X POST <alarm_url>
