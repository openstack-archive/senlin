===============
Events (events)
===============

Lists all events and shows information for an event.

List events
===========

.. rest_method::  GET /v1/events

Lists all events.

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
  - level: event_level_req
  - marker: marker
  - sort: sort
  - global_project: global_project
  - oid: oid_query
  - otype: otype_query
  - oname: oname_query
  - cluster_id: cluster_identity_query
  - action: action_name_query

The sorting keys include ``timestamp``, ``level``, ``otype``, ``oname``,
``action``, ``status``, ``oid`` and ``cluster_id``.

Response Parameters
-------------------

.. rest_parameters:: parameters.yaml

  - X-OpenStack-Request-ID: request_id
  - events: events
  - action: action_name
  - cluster_id: cluster_id
  - id: event_id
  - level: event_level
  - oid: oid
  - oname: oname
  - otype: otype
  - project: project
  - status: event_status
  - status_reason: status_reason
  - timestamp: event_timestamp
  - user: user

Response Example
----------------

.. literalinclude:: samples/events-list-response.json
   :language: javascript


Shows event details
===================

.. rest_method::  GET /v1/events/{event_id}

Shows details for an event.

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
  - event_id: event_id_url

Response Parameters
-------------------

.. rest_parameters:: parameters.yaml

  - X-OpenStack-Request-ID: request_id
  - event: event
  - action: action_name
  - cluster_id: cluster_id
  - id: event_id
  - level: event_level
  - oid: oid
  - oname: oname
  - otype: otype
  - project: project
  - status: event_status
  - status_reason: status_reason
  - timestamp: event_timestamp
  - user: user

Response Example
----------------

.. literalinclude:: samples/event-show-response.json
   :language: javascript
