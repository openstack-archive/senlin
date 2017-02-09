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

The design of the load-balancing policy faithfully follows the interface and
properties exposed by the LBaaS v2 service. A sample spec is shown below:

.. code-block:: yaml

  type: senlin.policy.loadbalance
  version: 1.1
  properties:
    pool:
      protocol: HTTP
      protocol_port: 80
      subnet: private_subnet
      lb_method: ROUND_ROBIN
      admin_state_up: true
      session_persistence:
        type: HTTP_COOKIE
        cookie_name: my_cookie
    vip:
      subnet: public_subnet
      address: 12.34.56.78
      connection_limit: 5000
      protocol: HTTP
      protocol_port: 80
      admin_state_up: true
    health_monitor:
      type: HTTP
      delay: 20
      timeout: 5
      max_retries: 3
      admin_state_up: true
      http_method: GET
      url_path: /health
      expected_codes: 200
    lb_status_timeout: 300

As you can see, there are many properties related to the policy. The good news
is that for most of them, there are reasonable default values. All properties
are optional except for the following few:

- ``pool.subnet``: This property provides the name or ID of the subnet for the
  port on which nodes can be connected.

- ``vip.subnet``: This property provides the name or ID of the subnet on which
  the virtual IP (VIP) is allocated.

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
for the ``vip.subnet`` property even though you don't have a preference about
the actual VIP allocated. However, if you do have a preferred VIP address to
use, you will need to provide both ``vip.subnet`` and ``vip.address`` values.
The LBaaS service will check if both values are valid.

Note that if you choose to omit the ``vip.address`` property, the LBaaS
service will allocate an address for you from the provided subnet. You will
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
