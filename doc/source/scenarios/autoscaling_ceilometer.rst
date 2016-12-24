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

.. _ref-scenario-autoscaling-ceilometer:


=================================
Autoscaling using Ceilometer/Aodh
=================================

As a telemetry service, the ceilometer project consists of several sub-projects
which provide metering, monitoring and alarming services in the telemetry
space. This section walks you through the steps to build an auto-scaling
solution by integrating senlin with ceilometer/aodh.

Step 1: Create a VM cluster
~~~~~~~~~~~~~~~~~~~~~~~~~~~

The first step is to create a profile using a spec file like the following one
and save it to a file, e.g. :file:`sample_server.yaml`:

.. code-block:: yaml

  type: os.nova.server
  version: 1.0
  properties:
    name: cirros_server
    flavor: m1.tiny
    image: cirros-0.3.4-x86_64-uec
    key_name: oskey
    networks:
      - network: private

Note this spec file assumes that you have a working nova key-pair named
"``oskey``" and there is a network named "``private``". You may need to change
these values based your environment settings. To create a profile using this
spec:

.. code-block:: console

  $ senlin profile-create -s sample_server.yaml pserver

Then you can create a cluster using the profile named "``pserver``":

.. code-block:: console

  $ senlin cluster-create -p pserver -c 2 mycluster
  +------------------+--------------------------------------+
  | Property         | Value                                |
  +------------------+--------------------------------------+
  | created_at       | 2016-06-07T02:26:33Z                 |
  | data             | {}                                   |
  | desired_capacity | 2                                    |
  | domain_id        | None                                 |
  | id               | 10c80bfe-41af-41f7-b9b1-9c81c9e5d21f |
  | init_at          | 2016-06-07T02:26:17Z                 |
  | max_size         | -1                                   |
  | metadata         | {}                                   |
  | min_size         | 0                                    |
  | name             | mycluster                            |
  | node_ids         | 14936837-1459-416b-a1f3-dea026f6cffc |
  |                  | 99ab3862-a230-4c09-af73-076dc0dec39b |
  | profile_id       | 1de5686a-09bb-4fb0-9502-34fa38833010 |
  | profile_name     | pserver                              |
  | project_id       | 99185bcde62c478e8d05b702e52d8b8d     |
  | status           | ACTIVE                               |
  | status_reason    | Cluster creation succeeded.          |
  | timeout          | 3600                                 |
  | updated_at       | 2016-06-13T02:42:47Z                 |
  | user_id          | 6c369aec78b74a4da413f86dadb0255e     |
  +------------------+--------------------------------------+

This creates a cluster with 2 nodes created at the beginning. We export the
cluster ID into an environment variable for convenience:

.. code-block:: console

  $ export MYCLUSTER_ID=10c80bfe-41af-41f7-b9b1-9c81c9e5d21f

You may want to check the IP addresses assigned to each node. In the output
from the following command, you will find the IP address for the specific node:

.. code-block:: console

  $ senlin node-show -D 14936837-1459-416b-a1f3-dea026f6cffc
  ...
  | details | +-----------+--------------------------------------+ |
  |         | | property  | value                                | |
  |         | +-----------+--------------------------------------+ |
  |         | | addresses | {                                    | |
  |         | |           |   "private": [                       | |
  |         | |           |     {                                | |
  |         | |           |       "OS-EXT-IPS-MAC:mac-addr": ... | |
  |         | |           |       "OS-EXT-IPS:type": "fixed",    | |
  |         | |           |       "addr": "10.0.0.9",            | |
  |         | |           |       "version": 4                   | |
  |         | |           |     }                                | |
  |         | |           |   ]                                  | |
  |         | |           | }                                    | |
  |         | | flavor    | 1                                    | |
  |         | | id        | 362f57b2-c089-4aab-bab3-1a7ffd4e1834 | |
  ...

We will use these IP addresses later to generate workloads on each nova
server.

Step 2: Create Receivers
~~~~~~~~~~~~~~~~~~~~~~~~

The next step is to create receivers for the cluster for triggering actions on
the cluster. Each receiver is usually created for a specific purpose, so for
different purposes you may need to create more than receivers.

The following command creates a receiver for scaling out the specified cluster
by two nodes every time it is triggered:

.. code-block:: console

  $ senlin receiver-create -a CLUSTER_SCALE_OUT -P count=2 -c mycluster r_01
  +------------+----------------------------------------------------------------------------+
  | Property   | Value                                                                      |
  +------------+----------------------------------------------------------------------------+
  | action     | CLUSTER_SCALE_OUT                                                          |
  | actor      | {                                                                          |
  |            |   "trust_id": "432f81d339444cac959bab2fd9ba92fa"                           |
  |            | }                                                                          |
  | channel    | {                                                                          |
  |            |   "alarm_url": "http://node1:8778/v1/webhooks/ba...5a/trigger?V=1&count=2" |
  |            | }                                                                          |
  | cluster_id | b75d25e7-e84d-4742-abf7-d8a3001e25a9                                       |
  | created_at | 2016-08-01T02:17:14Z                                                       |
  | domain_id  | -                                                                          |
  | id         | ba13f7cd-7a95-4545-b646-6a833ba6505a                                       |
  | location   | -                                                                          |
  | name       | r_01                                                                       |
  | params     | {                                                                          |
  |            |   "count": "2"                                                             |
  |            | }                                                                          |
  | project_id | 99185bcde62c478e8d05b702e52d8b8d                                           |
  | type       | webhook                                                                    |
  | updated_at | -                                                                          |
  | user_id    | 6c369aec78b74a4da413f86dadb0255e                                           |
  +------------+----------------------------------------------------------------------------+

At present, all property values shown for a receiver are read only. You cannot
change their values once the receiver is created. The only type of receivers
senlin understands is "``webhook``". For the "``action``" parameter, there are
many choices:

- ``CLUSTER_SCALE_OUT``
- ``CLUSTER_SCALE_IN``
- ``CLUSTER_RESIZE``
- ``CLUSTER_CHECK``
- ``CLUSTER_UPDATE``
- ``CLUSTER_DELETE``
- ``CLUSTER_ADD_NODES``
- ``CLUSTER_DEL_NODES``
- ``NODE_CREATE``
- ``NODE_DELETE``
- ``NODE_UPDATE``
- ``NODE_CHECK``
- ``NODE_RECOVER``

Senlin may add supports to more action types in future.

After a receiver is created, you can check its "``channel``" property value to
find out how to trigger that receiver. For a receiver of type "``webhook``"
(the default and the only supported type as for now), this means you will
check the "``alarm_url``" value. We will use that value later for action
triggering. For convenience, we export that value to an environment variable:

.. code-block:: console

  $ export ALRM_URL01=http://node1:8778/v1/webhooks/ba...5a/trigger?V=1&count=2

Similar to the example above, you can create other receivers for different
kinds of cluster operations or the same cluster operation with different
parameter values.

Step 3: Creating Aodh Alarms
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Once we have the cluster created and prepared to receive external signals, we
can proceed to create alarms using the software/service you deployed. The
following command creates a threshold alarm using aodh alarm service so that:

- aodh will evaluate the CPU utilization (i.e. ``cpu_util``) metric across the
  specified cluster;
- aodh will compute the CPU utilization using the average value during a given
  period (i.e. 60 seconds here);
- aodh will perform evaluation at the end of every single period;
- aodh won't trigger alarm actions repeatedly;
- aodh will do metric aggregation based on the specified metadata.

.. code-block:: console

  $ aodh alarm create \
    -t threshold --statistic avg --name cpu-high \
    -m cpu_util --threshold 70 --comparison-operator gt \
    --period 60 --evaluation-periods 1 \
    --alarm-action $ALRM_URL01 \
    --repeat-actions False \
    --query metadata.user_metadata.cluster_id=$MYCLUSTER_ID

Note that we are referencing the two environment variables ``MYCLUSTER_ID``
and ``ALRM_URL01`` in this command.

.. note::
  To make aodh aware of the ``cluster_id`` metadata senlin injects into each
  and every VM server created, you may need to add the following line into
  your :file:`/etc/ceilometer/ceilometer.conf` file::

    reserved_metadata_keys = cluster_id

  Also note that to make sure your CPU utilization driven metrics are
  evaluated at least once per 60 seconds, you will need to change the
  ``interval`` value for the ``cpu_source`` in the file
  :file:`/etc/ceilometer/pipeline.yaml`. For example, you can change it from
  the default value ``600`` to ``60``::

    sources:
      <other stuff ...>
      - name: cpu_source
        interval: 600   <- change this to 60
        meters:
          - "cpu"
      <other stuff ...>

Step 4: Run Workloads on Cluster Nodes
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

To examine the effect of cluster scaling under high CPU workload. You can now
log into each cluster nodes and run some CPU burning workloads there to drive
the CPU utilization high. For example:

.. code-block:: console

  $ ssh cirros@10.0.0.9
  $ cat /dev/zero > /dev/null
  < Guest system "hang" here... >

When all nodes in the cluster have their CPU pressure boosted, you can check
the CPU utilization on each node and finally proceed to the next step.

Step 5: Verify Cluster Scaling
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

After a while after the CPU workloads on cluster nodes are started, you will
notice that the cluster has been automatically scaled. Two new nodes are
created and added to the cluster. This can be verified by running the
following command:

.. code-block:: console

  $ senlin cluster-show $MYCLUSTER_ID

Optionally, you can use the following command to check if the anticipated
action was triggered and executed:

.. code-block:: console

  $ senlin action-list -f target=$MYCLUSTER_ID
