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

.. _ref-lb-policy:

=====================
Load-Balancing Policy
=====================

The load-balancing policy is an encapsulation of the LBaaS v2 service that
distributes the network load evenly among members in a pool. Users are in
general not interested in the implementation details although they have a
strong requirement of the features provided by a load-balancer, such as
load-balancing, health-monitoring etc.

The load-balancing policy is designed to be applicable to a cluster of virtual
machines or some variants or extensions of basic virtual machines. Currently,
Senlin only supports the load balancing for Nova servers. Future revisions may
extend this to more types of clusters.

Before using this policy, you will have to make sure the LBaaS v2 service is
installed and configured properly.


Properties
~~~~~~~~~~

.. schemaprops::
  :package: senlin.policies.lb_policy.LoadBalancingPolicy

Sample
~~~~~~

The design of the load-balancing policy faithfully follows the interface and
properties exposed by the LBaaS v2 service. A sample spec is shown below:

.. literalinclude :: /../../examples/policies/lb_policy.yaml
  :language: yaml

As you can see, there are many properties related to the policy. The good news
is that for most of them, there are reasonable default values. All properties
are optional except for the following few:

- ``vip.subnet`` or ``vip.network``: These properties provides the name or ID
  of the subnet or network on which the virtual IP (VIP) is allocated. At least
  one (or both) of them must be specified.

The following subsections describe each and every group of properties and the
general rules on using them.

Note that you can create and configure load-balancers all by yourself when you
have a good reason to do so. However, by using the load-balancing policy, you
no longer have to manage the load-balancer's lifecycle manually and you don't
have to update the load-balancer manually when cluster membership changes.


Load Balancer Pools
~~~~~~~~~~~~~~~~~~~

The load balancer pool is managed automatically when you have a load-balancing
policy attached to a cluster. The policy automatically adds existing nodes to
the load balancer pool when attaching the policy. Later on, when new nodes are
added to the cluster (e.g. by cluster scaling) or existing nodes are removed
from the cluster, the policy will update the pool's status to reflect the
change in membership.

Each pool is supposed to use the same protocol and the same port number for
load sharing. By default, the protocol (i.e. ``pool.protocol``) is set to
"``HTTP``" which can be customized to "``HTTPS``" or "``TCP``" in your setup.
The default port number is 80, which also can be modified to suit your service
configuration.

All nodes in a pool are supposed to reside on the same subnet, and the subnet
specified in the ``pool.subnet`` property must be compatible to the subnets of
existing nodes.

The LBaaS service is capable of load balance among nodes in different ways
which are collectively called the ``lb_method``. Valid values for this
property are:

- ``ROUND_ROBIN``: The load balancer will select a node for workload handling
  on a round-robin basis. Each node gets an equal pressure to handle workloads.

- ``LEAST_CONNECTIONS``: The load balancer will choose a node based on the
  number of established connections from client. The node will the lowest
  number of connections will be chosen.

- ``SOURCE_IP``: The load balancer will compute hash values based on the IP
  addresses of the clients and the server and then use the hash value for
  routing. This ensures the requests from the same client always go to the
  same server even in the face of broken connections.

The ``pool.admin_state_up`` property for the most time can be safely ignored.
It is useful only when you want to debug the details of a load-balancer.

The last property that needs some attention is ``pool.session_persistence``
which is used to persist client sessions even if the connections may break now
and then. There are three types of session persistence supported:

- ``SOURCE_IP``: The load balancer will try resume a broken connection based
  on the client's IP address. You don't have to configure the ``cookie_name``
  property in this case.

- ``HTTP_COOKIE``: The load balancer will check a named, general HTTP cookie
  using the name specified in the ``cookie_name`` property and then resume the
  connection based on the cookie contents.

- ``APP_COOKIE``: The load balancer will check the application specific cookie
  using the name specified in the ``cookie_name`` and resume connection based
  on the cookie contents.


Virtual IP
~~~~~~~~~~

The Virtual IP (or "VIP" for short) refers to the IP address visible from the
client side. It is the single IP address used by all clients to access the
application or service running on the pool nodes. You have to specify a value
for either the ``vip.subnet`` or ``vip.network`` property even though you don't
have a preference about the actual VIP allocated. However, if you do have a
preferred VIP address to use, you will need to provide both a
``vip.subnet``/``vip.network`` and a ``vip.address`` value.
The LBaaS service will check if both values are valid.

Note that if you choose to omit the ``vip.address`` property, the LBaaS
service will allocate an address for you from the either the provided subnet,
or a subnet automatically chosen from the provided network. You will
have to check the cluster's ``data`` property after the load-balancing policy
has been successfully attached to your cluster. For example:

.. code-block:: console

  $ openstack cluster show my_cluster

  +------------------+------------------------------------------------+
  | Field            | Value                                          |
  +------------------+------------------------------------------------+
  | created_at       | 2017-01-21T06:25:42Z                           |
  | data             | {                                              |
  |                  |   "loadbalancers": {                           |
  |                  |     "1040ad51-87e8-4579-873b-0f420aa0d273": {  |
  |                  |       "vip_address": "11.22.33.44"             |
  |                  |     }                                          |
  |                  |   }                                            |
  |                  | }                                              |
  | dependents       | {}                                             |
  | desired_capacity | 10                                             |
  | domain_id        | None                                           |
  | id               | 30d7ef94-114f-4163-9120-412b78ba38bb           |
  | ...              | ...                                            |

The output above shows you that the cluster has a load-balancer created for
you and the VIP used to access that cluster is "11.22.33.44".

Similar to the pool properties discussed in previous subsection, for the
virtual IP address, you can also specify the expected network protocol and
port number to use where clients will be accessing it. The default value for
``vip.protocol`` is "``HTTP``" and the default port number is 80. Both can be
customized to suit your needs.

Another useful feature provided by the LBaaS service is the cap of maximum
number of connections per second. This is a limit set on a per-VIP basis. By
default, Senlin sets the ``vip.connection_limit`` to -1 which means there is
no upper bound for connection numbers. You may want to customize this value
to restrict the number of connection requests per second for your service.

The last property in the ``vip`` group is ``admin_state_up`` which is default
to "``True``". In some rare cases, you may want to set it to "``False``" for
the purpose of debugging.


Health Monitor
~~~~~~~~~~~~~~

Since a load-balancer sits in front of all nodes in a pool, it has to be aware
of the health status of all member nodes so as to properly and reliably route
client requests to the active nodes for processing. The problem is that there
are so many different applications or web services each exhibit a different
runtime behavior. It is hard to come up with an approach generic and powerful
enough to detect all kinds of node failures.

The LBaaS that backs the Senlin load-balancing policy supports four types of
node failure detections, all generic enough to serve a wide range of
applications.

- ``PING``: The load-balancer pings every pool members to detect if they are
  still reachable.

- ``TCP``: The load-balancer attempts a telnet connection to the protocol port
  configured for the pool thus determines if a node is still alive.

- ``HTTP``: The load-balancer attempts a HTTP request (specified in the
  ``health_monitor.http_method`` property) to specific URL (configured in the
  ``health_monitor.url_path`` property) and then determines if a node is still
  active by comparing the result code to the expected value (configured in the
  ``health_monitor.expected_codes``.

- ``HTTPS``: The load-balancer checks nodes' aliveness by sending a HTTPS
  request using the same values as those in the case of ``HTTP``.

The ``health_monitor.expected_codes`` field accepts a string value, but you
can specify multiple HTTP status codes that can be treated as an indicator of
node's aliveness:

- A single value, such as ``200``;

- A list of values separated by commas, such as ``200, 202``;

- A range of values, such as ``200-204``.

To make the failure detection reliable, you may want to check and customize
the following properties in the ``health_monitor`` group.

- ``timeout``: The maximum time in milliseconds that a monitor waits for a
  response from a node before it claims the node unreachable. The default is
  5.

- ``max_retries``: The number of allowed connection failures before the monitor
  concludes that node inactive. The default is 3.

- ``delay``: The time in milliseconds between sending two consecutive requests
  (probes) to pool members. The default is 10.

A careful experimentation is usually warranted to come up with reasonable
values for these fields in a specific environment.


LB Status Timeout
~~~~~~~~~~~~~~~~~

Due to the way the LBaaS service is implemented, creating load balancers and
health monitors, updating load balancer pools all take considerable time. In
some deployment scenarios, it make take the load balancer several minutes to
become operative again after an update operation.

The ``lb_status_timeout`` option is provided since version 1.1 of the
load-balancing policy to mitigate this effect. In real production environment,
you are expected to set this value based on some careful dry-runs.


Availability Zone
~~~~~~~~~~~~~~~~~

Load balancers have their own availability zones, similar to the compute
service.

The ``availability_zone`` option is provided since version 1.2 of the
load-balancing policy, to allow the user to choose which availability zone to
use when provisioning the load balancer.

Validation
~~~~~~~~~~

When creating a new load-balancing policy object, Senlin checks if the subnet
and/or network provided are actually known to the Neutron network service. If
they are not, the policy creation will fail.


Updates to the Cluster and Nodes
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

When a load-balancing policy has been successfully attached to a cluster, you
can observe the VIP address from the ``data`` property of the cluster, as
described above.

You can also check the ``data`` property of nodes in the cluster. Each node
will have a ``lb_member`` key in its data property indicating the ID of the
said node in the load-balancer pool.

When the load-balancing policy is detached from a cluster successfully. These
data will be automatically removed, and the related resources created at the
LBaaS side are deleted transparently.


Node Deletion
~~~~~~~~~~~~~

In the case where there is a :ref:`ref-deletion-policy` attached to the same
cluster, the deletion policy will elect the victims to be removed from a
cluster before the load-balancing policy gets a chance to remove those nodes
from the load-balancing pool.

However, when there is no such a deletion policy in place, the load-balancing
policy will try to figure out the number of nodes to delete (if needed) and
randomly choose the victim nodes for deletion.
