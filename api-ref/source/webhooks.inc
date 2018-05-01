===================
Webhooks (webhooks)
===================

Triggers an action represented by a webhook. For API microversion less than
1.10, optional params in the query are sent as inputs to be used by the
targeted action. For API microversion equal or greater than 1.10, any
key-value pairs in the request body are sent as inputs to be used by the
targeted action.

Trigger webhook action
======================

.. rest_method::  POST /v1/webhooks/{webhook_id}/trigger

Triggers a webhook receiver.

Response Codes
--------------

.. rest_status_code:: success status.yaml

   - 202

.. rest_status_code:: error status.yaml

   - 400
   - 403
   - 404
   - 503

Request Parameters
------------------

.. rest_parameters:: parameters.yaml

  - OpenStack-API-Version: microversion
  - webhook_id: webhook_id_url
  - V: webhook_version
  - params: webhook_params

Response Parameters
-------------------

.. rest_parameters:: parameters.yaml

  - X-OpenStack-Request-Id: request_id
  - Location: location
  - action: action_action

Response Example
----------------

.. literalinclude:: samples/webhook-action-response.json
   :language: javascript
