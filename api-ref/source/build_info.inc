==============================
Build information (build-info)
==============================

Shows build information for a Senlin deployment.

Shows build information
=======================

.. rest_method::  GET /v1/build-info

Shows build information for a Senlin deployment.

Normal response codes: 200

Error response codes:

- unauthorized (401)
- forbidden (403)
- serviceUnavailable (503)

Request Parameters
------------------

.. rest_parameters:: parameters.yaml

  - OpenStack-API-Version: microversion

Response Parameters
-------------------

.. rest_parameters:: parameters.yaml

  - build_info: build_info
  - api: build_info_api
  - engine: build_info_engine

Response Example
----------------

.. literalinclude:: samples/build-show-response.json
   :language: javascript

This operation does not accept a request body.
