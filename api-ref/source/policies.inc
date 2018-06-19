===================
Policies (policies)
===================

Lists all policies and creates, shows information for, updates, and deletes a
policy.


List policies
=============

.. rest_method::  GET /v1/policies

Lists all policies.

Response Codes
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
  - limit: limit
  - marker: marker
  - sort: sort
  - global_project: global_project
  - name: name_query
  - type: type_query

The sorting keys include ``name``, ``type``, ``created_at`` and
``udpated_at``.

Response Parameters
-------------------

.. rest_parameters:: parameters.yaml

  - X-OpenStack-Request-ID: request_id
  - policies: policies
  - created_at: created_at
  - data: policy_data
  - domain: domain
  - id: policy_id
  - name: name
  - project: project
  - spec: policy_spec
  - type: policy_type_name
  - updated_at: updated_at
  - user: user

Response Example
----------------

.. literalinclude:: samples/policy-list-response.json
   :language: javascript


Create policy
=============

.. rest_method::  POST /v1/policies

Creates a policy.

Response Codes
--------------

.. rest_status_code:: success status.yaml

   - 201

.. rest_status_code:: error status.yaml

   - 400
   - 401
   - 403
   - 503

Request Parameters
------------------

.. rest_parameters:: parameters.yaml

  - OpenStack-API-Version: microversion
  - policy: policy
  - name: policy_name
  - spec: policy_spec

Request Example
---------------

.. literalinclude:: samples/policy-create-request.json
   :language: javascript

Response Parameters
-------------------

.. rest_parameters:: parameters.yaml

  - X-OpenStack-Request-ID: request_id
  - policy: policy
  - created_at: created_at
  - data: policy_data
  - domain: domain
  - id: policy_id
  - name: name
  - project: project
  - spec: policy_spec
  - type: policy_type_name
  - updated_at: updated_at
  - user: user

Response Example
----------------

.. literalinclude:: samples/policy-create-response.json
   :language: javascript


Show policy details
===================

.. rest_method::  GET /v1/policies/{policy_id}

Shows details for a policy.

Response Codes
--------------

.. rest_status_code:: success status.yaml

   - 200

.. rest_status_code:: error status.yaml

   - 400
   - 401
   - 403
   - 404
   - 503

Request Parameters
------------------

.. rest_parameters:: parameters.yaml

  - OpenStack-API-Version: microversion
  - policy_id: policy_id_url

Response Parameters
-------------------

.. rest_parameters:: parameters.yaml

  - X-OpenStack-Request-ID: request_id
  - policy: policy
  - created_at: created_at
  - data: policy_data
  - domain: domain
  - id: policy_id
  - name: name
  - project: project
  - spec: policy_spec
  - type: policy_type_name
  - updated_at: updated_at
  - user: user

Response Example
----------------

.. literalinclude:: samples/policy-show-response.json
   :language: javascript


Update policy
=============

.. rest_method::  PATCH /v1/policies/{policy_id}

Updates a policy.

Response Codes
--------------

.. rest_status_code:: success status.yaml

   - 200

.. rest_status_code:: error status.yaml

   - 400
   - 401
   - 403
   - 404
   - 503

Request Parameters
------------------

.. rest_parameters:: parameters.yaml

  - OpenStack-API-Version: microversion
  - policy_id: policy_id_url
  - policy: policy
  - name: name

Note that the only property that can be updated on a policy object after
creation is ``name``.

Request Example
---------------

.. literalinclude:: samples/policy-update-request.json
   :language: javascript


Response Parameters
-------------------

.. rest_parameters:: parameters.yaml

  - X-OpenStack-Request-ID: request_id
  - policy: policy
  - created_at: created_at
  - data: policy_data
  - domain: domain
  - id: policy_id
  - name: name
  - project: project
  - spec: policy_spec
  - type: policy_type_name
  - updated_at: updated_at
  - user: user

Response Example
----------------

.. literalinclude:: samples/policy-update-response.json
   :language: javascript


Delete policy
=============

.. rest_method::  DELETE /v1/policies/{policy_id}

Deletes a policy.

Response Codes
--------------

A policy cannot be deleted if it is still attached to cluster(s). In that
case, a 409 error will be returned.

.. rest_status_code:: success status.yaml

   - 204

.. rest_status_code:: error status.yaml

   - 400
   - 401
   - 403
   - 404
   - 409
   - 503

Request Parameters
------------------

.. rest_parameters:: parameters.yaml

  - OpenStack-API-Version: microversion
  - policy_id: policy_id_url

Response Parameters
-------------------

.. rest_parameters:: parameters.yaml

  - X-OpenStack-Request-ID: request_id


Validate policy
===============

.. rest_method::  POST /v1/policies/validate

Validates a policy.

This API is only available since API microversion 1.2.

Response Codes
--------------

.. rest_status_code:: success status.yaml

   - 200

.. rest_status_code:: error status.yaml

   - 400
   - 401
   - 503

Request Parameters
------------------

.. rest_parameters:: parameters.yaml

  - OpenStack-API-Version: microversion
  - policy: policy
  - spec: policy_spec

Request Example
---------------

.. literalinclude:: samples/policy-validate-request.json
   :language: javascript

Response Parameters
-------------------

The response contains properties as if the policy has been created.

.. rest_parameters:: parameters.yaml

  - X-OpenStack-Request-Id: request_id
  - policy: policy
  - created_at: created_at
  - data: policy_data
  - domain: domain
  - id: policy_id
  - name: name
  - project: project
  - spec: policy_spec
  - type: policy_type_name
  - updated_at: updated_at
  - user: user

Response Example
----------------

.. literalinclude:: samples/policy-validate-response.json
   :language: javascript
