=============================
Profile Types (profile-types)
=============================

Lists all profile types and shows details for a profile type.

List profile types
==================

.. rest_method::  GET /v1/profile-types

Lists supported profile types.

Normal response codes: 200

Error response codes:

- unauthorized (401)
- forbidden (403)
- serviceUnavailable (503)

Request Parameters
------------------

.. rest_parameters:: parameters.yaml

  - OpenStack-API-Version: microversion

Response Example
----------------

.. literalinclude:: samples/profile-types-list-response.json
   :language: javascript

Response Parameters
-------------------

.. rest_parameters:: parameters.yaml

  - profile_types: profile_types


Show profile type details
=========================

.. rest_method::  GET /v1/profile-types/{profile_type}

Shows details for a profile type.


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
  - profile_type: profile_type_url

Response Parameters
-------------------

.. rest_parameters:: parameters.yaml

  - profile_type: profile_type
  - name: profile_type_name
  - schema: profile_type_schema

Response Example
----------------

.. literalinclude:: samples/profile-type-show-response.json
   :language: javascript
