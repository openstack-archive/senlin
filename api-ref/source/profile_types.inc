=============================
Profile Types (profile-types)
=============================

Lists all profile types and shows details for a profile type.

List profile types
==================

.. rest_method::  GET /v1/profile-types

Lists supported profile types.

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
  - profile_types: profile_types

Response Example
----------------

.. literalinclude:: samples/profile-types-list-response.json
   :language: javascript


Show profile type details
=========================

.. rest_method::  GET /v1/profile-types/{profile_type}

Shows details for a profile type.

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
  - profile_type: profile_type_url

Response Parameters
-------------------

.. rest_parameters:: parameters.yaml

  - X-OpenStack-Request-Id: request_id
  - profile_type: profile_type
  - name: profile_type_name
  - schema: profile_type_schema

Response Example
----------------

.. literalinclude:: samples/profile-type-show-response.json
   :language: javascript
