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
- serviceUnvailable (503)

Request Parameters
------------------

.. rest_parameters:: parameters.yaml

  - OpenStack-API-Version: microversion
  - limit: limit
  - marker: marker
  - sort: sort
  - global_project: global_project
  - obj_id: obj_id_query
  - obj_type: obj_type_query
  - obj_name: obj_name_query
  - cluster_id: cluster_id
    in: query
    optional: True
  - action: action_name_query

Response Parameters
-------------------

.. rest_parameters:: parameters.yaml

  - events: events
  - action: action_name
    in: event
  - cluster_id: cluster_id
    in: event
  - id: event_id
  - level: event_level
  - obj_id: obj_id
  - obj_name: obj_name
  - obj_type: obj_type
  - project: project
    in: event
  - status: event_status
  - status_reason: status_reason
    in: event
  - timestamp: event_timestamp
  - user: user
    in: event

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
- serviceUavailable (503)

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
    in: event
  - cluster_id: cluster_id
    in: event
  - id: event_id
  - level: event_level
  - obj_id: obj_id
  - obj_name: obj_name
  - obj_type: obj_type
  - project: project
    in: event
  - status: event_status
  - status_reason: status_reason
    in: event
  - timestamp: event_timestamp
  - user: user
    in: event

Response Example
----------------

.. literalinclude:: samples/event-show-response.json
   :language: javascript
