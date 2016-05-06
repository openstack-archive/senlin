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
- serviceUnvailable (503)

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
  - type: profile_type_property
  - updated_at: updated_at
  - user: user

Response Example
----------------

.. literalinclude:: samples/profile-list-response.json
   :language: javascript
