===========================
Policy Types (policy-types)
===========================

Lists all policy types and shows details for a policy type.

List policy types
=================

.. rest_method::  GET /v1/policy-types

Lists all supported policy types.


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

  - policy_types: policy_types

Response Example
----------------

.. literalinclude:: samples/policy-types-list-response.json
   :language: javascript


Show policy type details
========================

.. rest_method::  GET /v1/policy-types/{policy_type}

Shows details for a policy type.

Normal response codes: 200

Error response codes:

- unauthorized (401)
- forbidden (403)
- notFound (404)
- serviceUnavailable (503)

Request Parameters
------------------

.. rest_parameters:: parameters.yaml

  - OpenStack-API-Version: microversion
  - policy_type: policy_type_url

Response Parameters
-------------------

.. rest_parameters:: parameters.yaml

  - policy_type: policy_type
  - name: policy_type_name
  - schema: policy_type_schema

Response Example
----------------

.. literalinclude:: samples/policy-type-show-response.json
   :language: javascript
