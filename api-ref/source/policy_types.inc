===========================
Policy Types (policy-types)
===========================

Lists all policy types and shows details for a policy type.

List policy types
=================

.. rest_method::  GET /v1/policy-types

Lists all supported policy types.

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

  - X-OpenStack-Request-Id: request_id
  - policy_types: policy_types

Response Example
----------------

.. literalinclude:: samples/policy-types-list-response.json
   :language: javascript


Show policy type details
========================

.. rest_method::  GET /v1/policy-types/{policy_type}

Shows details for a policy type.

Response Codes
--------------

.. rest_status_code:: success status.yaml

   - 200

.. rest_status_code:: error status.yaml

   - 401
   - 403
   - 404
   - 503

Request Parameters
------------------

.. rest_parameters:: parameters.yaml

  - OpenStack-API-Version: microversion
  - policy_type: policy_type_url

Response Parameters
-------------------

.. rest_parameters:: parameters.yaml

  - X-OpenStack-Request-Id: request_id
  - policy_type: policy_type
  - name: policy_type_name
  - schema: policy_type_schema

Response Example
----------------

.. literalinclude:: samples/policy-type-show-response.json
   :language: javascript
