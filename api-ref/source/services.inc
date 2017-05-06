===================
Services (services)
===================

Lists all services for senlin engine.


List services
===================

.. rest_method::  GET /v1/services

   min_version: 1.7

This API is only available since API microversion 1.7.

Lists all services.

Response codes
--------------

.. rest_status_code:: success status.yaml

   - 200

.. rest_status_code:: error status.yaml

   - 400
   - 401
   - 403
   - 503

Request Parameters
------------------

.. rest_parameters:: parameters.yaml

  - OpenStack-API-Version: microversion

Response Parameters
-------------------

.. rest_parameters:: parameters.yaml

  - X-OpenStack-Request-ID: request_id
  - services: services
  - binary: binary
  - disabled_reason: disabled_reason
  - host: host
  - id: service_id
  - state: service_state
  - status: service_status
  - topic: topic
  - updated_at: updated_at

Response Example
----------------

.. literalinclude:: samples/services-list-response.json
   :language: javascript
