============
API Versions
============

Concepts
========

The Senlin API supports a ''major versions'' expressed in request URLs and
''microversions'' which can be sent in HTTP header ``OpenStack-API-Version``.

When the specified ``OpenStack-API-Version`` is not supported by the API
service, a 406 (NotAcceptable) exception will be raised. Note that this applies
to all API requests documented in this guide.

List Major Versions
===================

.. rest_method::  GET /

Lists information for all Clustering API major versions.

Response Codes
--------------

.. rest_status_code:: success status.yaml

   - 300: multi_version

.. rest_status_code:: error status.yaml

   - 503

Response Parameters
-------------------

.. rest_parameters:: parameters.yaml

  - X-OpenStack-Request-Id: request_id
  - versions: versions
  - id: version_id
  - links: version_links
  - max_version: version_max_version
  - media-types: version_media_types
  - min_version: version_min_version
  - status: version_status
  - updated: version_updated

Response Example
----------------

.. literalinclude:: samples/versions-list-response.json
   :language: javascript


Show Details of an API Version
==============================

.. rest_method:: GET /{version}/

Show details about an API major version.

Response Codes
--------------

.. rest_status_code:: success status.yaml

   - 200

.. rest_status_code:: error status.yaml

   - 404
   - 406
   - 503

Request Parameters
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
