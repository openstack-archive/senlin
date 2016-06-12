============
API Versions
============

Concepts
========

The Senlin API supports a ''major versions'' expressed in request URLs and
''microversions'' which can be sent in HTTP header ``OpenStack-API-Version``.


List Major Versions
===================

.. rest_method::  GET /

Lists information for all Clustering API major versions.


Normal response codes: 300
Error response codes: serviceUnavailable (503)

Response Parameters
-------------------

.. rest_parameters:: parameters.yaml

  - versions: versions

Response Example
----------------

.. literalinclude:: samples/versions-list-response.json
   :language: javascript


Show Details of an API Version
==============================

.. rest_method:: GET /{version}/

Show details about an API major version.

Normal response codes: 200

Error response codes:

- notFound (404)
- serviceUnavailable (503)

Response Parameters
-------------------

.. rest_parameters:: parameters.yaml

  - version: version_url


Response Parameters
-------------------

.. rest_parameters:: parameters.yaml

  - X-OpenStack-Request-ID: request_id
  - version: version
  - id: version_id
  - links: version_links
  - max_version: version_max_version
  - media-types: version_media_types
  - min_version: version_min_version
  - status: version_status
  - updated: version_updated

Response Example
----------------

.. literalinclude:: samples/version-show-response.json
   :language: javascript
