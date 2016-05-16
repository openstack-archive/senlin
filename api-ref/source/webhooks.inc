===================
Webhooks (webhooks)
===================

Triggers an action represented by a webhook.

Trigger webhook action
======================

.. rest_method::  POST /v1/webhooks/{webhook_id}/trigger

Triggers a webhook receiver.

Normal response codes: 202

Error response codes:

- forbidden (403)
- notFound (404)
- serviceUnavailable (503)

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

  - location: location
