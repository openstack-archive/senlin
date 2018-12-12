=======
Actions
=======

Lists all actions and shows details for an action.


List actions
============

.. rest_method::  GET /v1/actions

Lists all actions.

Response codes
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
  - marker: marker
  - sort: sort
  - global_project: global_project
  - name: name_query
  - target: target_query
  - action: action_action_query
  - status: action_status_query

The sorting keys include ``name``, ``target``, ``action``, ``created_at``
and ``status``.

Response Parameters
-------------------

.. rest_parameters:: parameters.yaml

  - X-OpenStack-Request-ID: request_id
  - actions: actions
  - action: action_action
  - cause: cause
  - created_at: created_at
  - data: action_data
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
  - project: project
  - status: action_status
  - status_reason: status_reason
  - target: action_target
  - timeout: action_timeout
  - updated_at: updated_at
  - user: user

Response Example
----------------

.. literalinclude:: samples/actions-list-response.json
   :language: javascript


Show action details
===================

.. rest_method::  GET /v1/actions/{action_id}

Shows details for an action.

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
  - action_id: action_id_url

Response Parameters:

.. rest_parameters:: parameters.yaml

  - X-OpenStack-Request-ID: request_id
  - action: action_action
  - cause: cause
  - created_at: created_at
  - data: action_data
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
  - project: project
  - status: action_status
  - status_reason: status_reason
  - target: action_target
  - timeout: action_timeout
  - updated_at: updated_at
  - user: user

Response Example
----------------

.. literalinclude:: samples/action-get-response.json
   :language: javascript

Update action
=============

.. rest_method::  PATCH /v1/actions/{action_id}

    min_version: 1.12

Update status of an action.

This API is only available since API microversion 1.12.

Request Parameters
------------------

.. rest_parameters:: parameters.yaml

  - OpenStack-API-Version: microversion
  - action_id: action_id_url
  - action: action
  - status: action_status_update
  - force: action_update_force_query

Request Example
---------------

.. literalinclude:: samples/action-get-request.json
   :language: javascript

Response Codes
--------------

.. rest_status_code:: success status.yaml

   - 202

.. rest_status_code:: error status.yaml

   - 400
   - 401
   - 403
   - 404
   - 409
   - 503
