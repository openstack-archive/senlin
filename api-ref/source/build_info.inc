==============================
Build information (build-info)
==============================

Shows build information for a Senlin deployment.

Show build information
=======================

.. rest_method::  GET /v1/build-info

Shows build information for a Senlin deployment.

Response Codes
--------------

.. rest_status_code:: success status.yaml

   - 200

.. rest_status_code:: error status.yaml

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
  - build_info: build_info
  - api: build_info_api
  - engine: build_info_engine

Response Example
----------------

.. literalinclude:: samples/build-show-response.json
   :language: javascript

This operation does not accept a request body.
