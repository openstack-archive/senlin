=======
Actions
=======

Lists all actions and shows details for an action.


List actions
============

.. rest_method::  GET /v1/actions

Lists all actions.

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
  - name: name_query
  - target: target_query
  - action: action_action_query
  - status: action_status_query

Reponse Parameters
------------------

.. rest_parameters:: parameters.yaml

  - actions: actions
  - action: action_action
  - cause: cause
  - context: action_context
  - created_at: created_at
  - depended_by: depended_by
  - depends_on: depends_on
  - start_time: start_time
  - end_time: end_time
  - id: action_id
  - inputs: inputs
  - interval: interval
  - name: name
  - outputs: outputs
  - owner: action_owner
  - status: action_status
  - status_reason: status_reason
  - target: action_target
  - timeout: action_timeout
  - updated_at: updated_at

Response Example
----------------

.. literalinclude:: samples/actions-list-response.json
   :language: javascript


Show action details
===================

.. rest_method::  GET /v1/actions/{action_id}

Shows details for an action.


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
  - action_id: action_id_url

Response Parameters:

.. rest_parameters:: parameters.yaml

  - action: action_action
  - cause: cause
  - context: action_context
  - created_at: created_at
  - depended_by: depended_by
  - depends_on: depends_on
  - start_time: start_time
  - end_time: end_time
  - id: action_id
  - inputs: inputs
  - interval: interval
  - name: name
  - outputs: outputs
  - owner: action_owner
  - status: action_status
  - status_reason: status_reason
  - target: action_target
  - timeout: action_timeout
  - updated_at: updated_at

Response Example
----------------

.. literalinclude:: samples/action-get-response.json
   :language: javascript
