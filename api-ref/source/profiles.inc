===================
Profiles (profiles)
===================

Lists all profiles and creates, shows information for, updates, and deletes a
profile.

List profiles
=============

.. rest_method::  GET /v1/profiles

Lists all profiles.

Normal response codes: 200

Error response codes:

- badRequest (400)
- unauthorized (401)
- forbidden (403)
- serviceUnavailable (503)

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

Response Parameters
-------------------

.. rest_parameters:: parameters.yaml

  - profiles: profiles
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

.. literalinclude:: samples/profile-list-response.json
   :language: javascript


Create profile
==============

.. rest_method::  POST /v1/profiles

Creates a profile.

Normal response codes: 201

Error response codes:

- badRequest (400)
- unauthorized (401)
- forbidden (403)
- serviceUnavailable (503)

Request Parameters
------------------

.. rest_parameters:: parameters.yaml

  - OpenStack-API-Version: microversion
  - profile: profile
  - name: name
  - metadata: metadata_req
  - spec: profile_spec

Request Example
---------------

.. literalinclude:: samples/profile-create-request.json
   :language: javascript

Response Parameters
-------------------

.. rest_parameters:: parameters.yaml

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

Normal response codes: 200

Error response codes:

- badRequest (400)
- unauthorized (401)
- forbidden (403)
- notFound(404)
- serviceUnavailable (503)

Request Parameters
------------------

.. rest_parameters:: parameters.yaml

  - OpenStack-API-Version: microversion
  - profile_id: profile_id_url


Response Parameters
-------------------

.. rest_parameters:: parameters.yaml

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

Normal response codes: 200

Error response codes:

- badRequest (400)
- unauthorized (401)
- forbidden (403)
- notFound(404)
- serviceUnavailable (503)

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

A profile cannot be deleted if it is still used by node or cluster. In that
case, a 409 error will be returned.

Normal response codes: 204

Error response codes:

- badRequest (400)
- unauthorized (401)
- forbidden (403)
- notFound(404)
- conflict(409)
- serviceUnavailable (503)

Request Parameters
------------------

.. rest_parameters:: parameters.yaml

  - OpenStack-API-Version: microversion
  - profile_id: profile_id_url
