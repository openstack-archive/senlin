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

For API microversion lower than 1.5, the response only contains the name for
each policy type:

.. literalinclude:: samples/policy-types-list-response.json
   :language: javascript

Since API microversion 1.5, the response contains the support status of each
policy type and the version is provided using a separate key:

.. literalinclude:: samples/policy-types-list-response-v1.5.json
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

For API microversion lower than 1.5, the response only contains the name and
schema of the specified policy type:

.. literalinclude:: samples/policy-type-show-response.json
   :language: javascript

Since API microversion 1.5, the response contains the support status of the
specified policy type:

.. literalinclude:: samples/policy-type-show-response-v1.5.json
   :language: javascript

