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


.. _guide-tutorial-autoscaling-heat:

=====================
Autoscaling with Heat
=====================

Goal
~~~~

There are Senlin resource types in Heat which make deployment of a full-featured
auto-scaling solution easily attainable. This document is to provide a tutorial for
users who want to use heat to create a senlin cluster.

It is often required by real deployment practices to make the cluster load-balanced
and auto-scaled. We also want the scaling action triggered based on business data
instead of infrastructure metrics. When existing cluster is not enough to afford the
throughput/workload, the cluster will be scaled-out; when low throughput or workload,
the cluster will be scaled-in.

Moreover, custom is easy to do when auto-scaling. Receivers can be created to
generate webhooks from scale_out and scale_in actions. Moreover, placement_zone.yaml
and placement_region.yaml can be attached to cluster and guide which zone/region to
place new nodes when scale_out; deletion_policy can be attached to the cluster and
guide the choice of candidates to delete when scale_in.

Sample template
~~~~~~~~~~~~~~~

There have a sample template in heat-template project under directory of senlin
for creation of Senlin elastic load-balanced cluster by Heat. Here we choose some
important parts of the sample to explain one by one.

The resource below defines a security_group for connection to created load-balanced
cluster:

.. code-block:: yaml

  security_group:
    type: OS::Neutron::SecurityGroup
    properties:
      rules:
        - protocol: icmp
        - protocol: tcp
          port_range_min: 22
          port_range_max: 22
        - protocol: tcp
          port_range_min: 80
          port_range_max: 80

The resource below defines the profile used to create the targeted cluster:

.. code-block:: yaml

  profile:
    type: OS::Senlin::Profile
    properties:
      type: os.nova.server-1.0
      properties:
        flavor: {get_param: flavor}
        image: {get_param: image}
        key_name: {get_param: key_name}
        networks:
          - network: {get_param: network}
        security_groups:
          - {get_resource: security_group}

The resource below defines to create a Senlin cluster with two nodes at least:

.. code-block:: yaml

  cluster:
    type: OS::Senlin::Cluster
    properties:
      desired_capacity: 2
      min_size: 2
      profile: {get_resource: profile}

The two resources below define scale_in_policy and scale_out_policy attached to
the created cluster. Where, the property of event is used to define the objective
action the policy works. When type of the property of adjustment is set as
CHANGE_IN_CAPACITY, the cluster will increase the number of nodes when scale_out or
decrease the number of nodes when scale_in:

.. code-block:: yaml

  scale_in_policy:
    type: OS::Senlin::Policy
    properties:
      type: senlin.policy.scaling-1.0
      bindings:
        - cluster: {get_resource: cluster}
      properties:
        event: CLUSTER_SCALE_IN
        adjustment:
          type: CHANGE_IN_CAPACITY
          number: 1

  scale_out_policy:
    type: OS::Senlin::Policy
    properties:
      type: senlin.policy.scaling-1.0
      bindings:
        - cluster: {get_resource: cluster}
      properties:
        event: CLUSTER_SCALE_OUT
        adjustment:
          type: CHANGE_IN_CAPACITY
          number: 1

The resource below defines a lb_policy to be attached to the target cluster. Once
the policy is attached to the cluster, Senlin will automatically create loadbalancer,
pool, and health_monitor by invoking neutron LBaas V2 APIs for load-balancing purpose:

.. code-block:: yaml

  lb_policy:
    type: OS::Senlin::Policy
    properties:
      type: senlin.policy.loadbalance-1.0
      bindings:
        - cluster: {get_resource: cluster}
      properties:
        pool:
          protocol: HTTP
          protocol_port: 80
          subnet: {get_param: pool_subnet}
          lb_method: ROUND_ROBIN
        vip:
          subnet: {get_param: vip_subnet}
          protocol: HTTP
          protocol_port: 80
        health_monitor:
          type: HTTP
          delay: 10
          timeout: 5
          max_retries: 4

The two resources below define the receivers to be triggered when a certain alarm or
event occurs:

.. code-block:: yaml

  receiver_scale_out:
    type: OS::Senlin::Receiver
    properties:
      cluster: {get_resource: cluster}
      action: CLUSTER_SCALE_OUT
      type: webhook

  receiver_scale_in:
    type: OS::Senlin::Receiver
    properties:
      cluster: {get_resource: cluster}
      action: CLUSTER_SCALE_IN
      type: webhook

The resource below define the policy for selecting candidate nodes for deletion when
the cluster is to be shrank:

.. code-block:: yaml

  deletion_policy:
    type: OS::Senlin::Policy
    properties:
      type: senlin.policy.deletion-1.0
      bindings:
        - cluster: {get_resource: cluster}
      properties:
        criteria: YOUNGEST_FIRST
        destroy_after_deletion: True
        grace_period: 20
        reduce_desired_capacity: False

The two resources below define the alarms to trigger the above two receivers respectively.
We use the average rate of incoming bytes at LoadBalancer as the metrics to trigger the
scaling operations:

.. code-block:: yaml

  scale_in_alarm:
    type: OS::Ceilometer::Alarm
    properties:
      description: trigger when bandwidth overflow
      meter_name: network.services.lb.incoming.bytes.rate
      statistic: avg
      period: 180
      evaluation_periods: 1
      threshold: 12000
      repeat_actions: True
      alarm_actions:
        - {get_attr: [receiver_scale_in, channel, alarm_url]}
      comparison_operator: le
      query:
        metadata.user_metadata.cluster_id: {get_resource: cluster}

  scale_out_alarm:
    type: OS::Ceilometer::Alarm
    properties:
      description: trigger when bandwidth insufficient
      meter_name: network.services.lb.incoming.bytes.rate
      statistic: avg
      period: 60
      evaluation_periods: 1
      threshold: 28000
      repeat_actions: True
      alarm_actions:
        - {get_attr: [receiver_scale_out, channel, alarm_url]}
      comparison_operator: ge
      query:
        metadata.user_metadata.cluster_id: {get_resource: cluster}

Deployment Steps
~~~~~~~~~~~~~~~~

Before the deployment, please ensure that neutron LBaas v2 and
ceilometer/Aodh has been installed and configured in your environment.

Step one is to generate key-pair using the followed command:

.. code-block:: console

  $ openstack keypair create heat_key

Step two is to create a heat template as by downloading the template file
from `heat template`_.

Step three is to create a heat stack using the followed command:

.. code-block:: console

  $ openstack stack create test -t ./ex_aslb.yaml --parameter "key_name=heat_key"

The steps and samples introduced in this tutorial can also work
well together with composition of ceilometer, Aodh, and Gnocchi
without any change.

.. _heat template: https://opendev.org/openstack/senlin/src/branch/master/doc/source/scenarios/ex_lbas.yaml
