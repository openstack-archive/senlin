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

.. _guide-webhooks:

Webhook
=======

A :term:`Webhook` is used to trigger a specific :term:`Action` on a senlin
object, for instance the actions that change the size of a specified cluster.

How to use
----------

1. Create a cluster, e.g.

::

  senlin cluster-create -p $PROFILE_ID -c 2 -i 1 -a 5 test-cluster

2. Attach a ScalingPolicy to the cluster:

::

  senlin cluster-policy-attach -p $POLICY_ID test-cluster

3. Create a webhook and specify `test-cluster` as the `obj_id`, `cluster` as
   the `obj_type` and `CLUSTER_SCALE_OUT` or `CLUSTER_SCALE_IN` as the action.
   Senlin service will return the webhook information with its webhook_url.
   User can use this url to trigger cluster scale_out or scale_in action.

::

  senlin webhook-create -t cluster -i test-cluster \
      -a CLUSTER_SCALE_OUT \
      -c 'user=$USER_ID;password=$PASSWORD' \
      test-webhook

4. Trigger the webhook by sending a POST request to its URL, for example:

::

  curl http://<webhook_url>

The webhook url can be used in two different ways:

- Sending a simple `POST` request to the url (no headers or body).
  For example:

::

  curl -i -X 'POST' $WEBHOOK_URL.

This will directly trigger a cluster scaling operation and the scaling
behavior is determined by the ScalingPolicy attached to the cluster. If no
ScalingPolicy is attached to the cluster, by default 1 node will be
added/deleted;

- Pass extra parameters in the request body for the action execution
  when triggering the webhook. e.g.

::

  curl -i -X 'POST' $WEBHOOK_URL \
      -H 'Content-type: application/json' \
      --data '{"params": {"count": 2}}'

Using this approach, users can specify more details for controlling the
scaling behavior. If a ScalingPolicy has been attached to this cluster,
parameters passed in from the request will override the outcome from the
scaling policy.

Note: The webhook_url can only be got at the first time the webhook is created.
Anyone who has the webhook_url can trigger the cluster scaling action.
