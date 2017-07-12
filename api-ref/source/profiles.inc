===================
Profiles (profiles)
===================

Lists all profiles and creates, shows information for, updates, and deletes a
profile.

List profiles
=============

.. rest_method::  GET /v1/profiles

Lists all profiles.

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
  - global_project: global_project
  - limit: limit
  - marker: marker
  - name: name_query
  - sort: sort
  - type: type_query

The sorting keys include ``name``, ``type``, ``created_at`` and
``updated_at``.

Response Parameters
-------------------

.. rest_parameters:: parameters.yaml

  - X-OpenStack-Request-Id: request_id
  - profiles: profiles
  - created_at: created_at
  - domain: domain
  - id: profile_id
  - metadata: metadata
  - name: name
  - project: project
  - spec: profile_spec
  - type: profile_type_name
  - updated_at: updated_at
  - user: user

Response Example
----------------

.. literalinclude:: samples/profile-list-response.json
   :language: javascript


Create profile
==============

.. rest_method::  POST /v1/profiles

Creates a profile.

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
  - profile: profile
  - name: profile_name
  - metadata: metadata_req
  - spec: profile_spec

Request Example
---------------

.. literalinclude:: samples/profile-create-request.json
   :language: javascript

Response Parameters
-------------------

.. rest_parameters:: parameters.yaml

  - X-OpenStack-Request-Id: request_id
  - profile: profile
  - created_at: created_at
  - domain: domain
  - id: profile_id
  - metadata: metadata
  - name: name
  - project: project
  - spec: profile_spec
  - type: profile_type_name
  - updated_at: updated_at
  - user: user

Response Example
----------------

.. literalinclude:: samples/profile-create-response.json
   :language: javascript


Show profile details
====================

.. rest_method::  GET /v1/profiles/{profile_id}

Shows details for a profile.

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
  - profile_id: profile_id_url


Response Parameters
-------------------

.. rest_parameters:: parameters.yaml

  - X-OpenStack-Request-Id: request_id
  - profile: profile
  - created_at: created_at
  - domain: domain
  - id: profile_id
  - metadata: metadata
  - name: name
  - project: project
  - spec: profile_spec
  - type: profile_type_name
  - updated_at: updated_at
  - user: user

Response Example
----------------

.. literalinclude:: samples/profile-show-response.json
   :language: javascript


Update profile
==============

.. rest_method::  PATCH /v1/profiles/{profile_id}

Updates a profile.

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
  - profile_id: profile_id_url
  - profile: profile
  - metadata: metadata_req
  - name: name_req

Request Example
---------------

.. literalinclude:: samples/profile-update-request.json
   :language: javascript


Response Parameters
-------------------

.. rest_parameters:: parameters.yaml

  - X-OpenStack-Request-Id: request_id
  - profile: profile
  - created_at: created_at
  - id: profile_id
  - metadata: metadata
  - name: name
  - project: project
  - spec: profile_spec
  - type: profile_type_name
  - updated_at: updated_at
  - user: user

Response Example
----------------

.. literalinclude:: samples/profile-update-response.json
   :language: javascript


Delete profile
==============

.. rest_method::  DELETE /v1/profiles/{profile_id}

Deletes a profile.

Response Codes
--------------

A profile cannot be deleted if it is still used by node or cluster. In that
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
  - profile_id: profile_id_url


Response Parameters
-------------------

.. rest_parameters:: parameters.yaml

  - X-OpenStack-Request-Id: request_id


Validate profile
================

.. rest_method::  POST /v1/profiles/validate

Validates a profile.

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
  - profile: profile
  - spec: profile_spec

Request Example
---------------

.. literalinclude:: samples/profile-validate-request.json
   :language: javascript

Response Parameters
-------------------

The response contains properties as if the profile is created.

.. rest_parameters:: parameters.yaml

  - X-OpenStack-Request-Id: request_id
  - profile: profile
  - created_at: created_at
  - domain: domain
  - id: profile_id
  - metadata: metadata
  - name: name
  - project: project
  - spec: profile_spec
  - type: profile_type_name
  - updated_at: updated_at
  - user: user

Response Example
----------------

.. literalinclude:: samples/profile-validate-response.json
   :language: javascript
