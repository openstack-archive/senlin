===============
Events (events)
===============

Lists all events and shows information for an event.

List events
===========

.. rest_method::  GET /v1/events

Lists all events.

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
  - limit: limit
  - marker: marker
  - sort: sort
  - global_project: global_project
  - oid: oid_query
  - otype: otype_query
  - oname: oname_query
  - cluster_id: cluster_identity_query
  - action: action_name_query

Response Parameters
-------------------

.. rest_parameters:: parameters.yaml

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

Normal response codes: 200

Error response codes:

- badRequest (400)
- unauthorized (401)
- forbidden (403)
- notFound (404)
- serviceUnavailable (503)

Request Parameters
------------------

.. rest_parameters:: parameters.yaml

  - OpenStack-API-Version: microversion
  - event_id: event_id_url

Response Parameters
-------------------

.. rest_parameters:: parameters.yaml

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
