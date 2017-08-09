=====================
Receivers (receivers)
=====================

Lists all receivers and creates, shows information for, and deletes a receiver.


List receivers
==============

.. rest_method::  GET /v1/receivers

Lists all receivers.

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
  - marker: marker
  - sort: sort
  - global_project: global_project
  - name: name_query
  - type: receiver_type_query
  - cluster_id: cluster_identity_query
  - action: receiver_action_query
  - user: receiver_user_query

The sorting keys include ``name``, ``type``, ``action``, ``cluster_id``,
``created_at`` and ``user``.

Response Parameters
-------------------

.. rest_parameters:: parameters.yaml

  - X-OpenStack-Request-Id: request_id
  - receivers: receivers
  - action: receiver_action
  - actor: receiver_actor
  - channel: receiver_channel
  - cluster_id: cluster_id
  - created_at: created_at
  - domain: domain
  - id: receiver_id
  - name: name
  - params: receiver_params
  - project: project
  - type: receiver_type
  - updated_at: updated_at
  - user: user

Response Example
----------------

.. literalinclude:: samples/receivers-list-response.json
   :language: javascript


Create receiver
===============

.. rest_method::  POST /v1/receivers

Creates a receiver.

Response Codes
--------------

.. rest_status_code:: success status.yaml

   - 201

.. rest_status_code:: error status.yaml

   - 400
   - 401
   - 403
   - 500
   - 503

Request Parameters
------------------

.. rest_parameters:: parameters.yaml

  - OpenStack-API-Version: microversion
  - receiver: receiver
  - name: receiver_name
  - cluster_id: receiver_cluster_identity
  - type: receiver_type_req
  - action: receiver_action
  - actor: receiver_actor
  - params: receiver_params_req

Request Example
---------------

.. literalinclude:: samples/receiver-create-request.json
   :language: javascript


Response Parameters
-------------------

.. rest_parameters:: parameters.yaml

  - X-OpenStack-Request-Id: request_id
  - receiver: receiver
  - action: receiver_action
  - actor: receiver_actor
  - channel: receiver_channel
  - cluster_id: cluster_id
  - created_at: created_at
  - domain: domain
  - id: receiver_id
  - name: name
  - params: receiver_params
  - project: project
  - type: receiver_type
  - updated_at: updated_at
  - user: user

Response Example
----------------

.. literalinclude:: samples/receiver-create-response.json
   :language: javascript


Show receiver details
=====================

.. rest_method::  GET /v1/receivers/{receiver_id}

Shows details for a receiver.

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
  - receiver_id: receiver_id_url

Response Parameters
-------------------

.. rest_parameters:: parameters.yaml

  - X-OpenStack-Request-Id: request_id
  - receiver: receiver
  - action: receiver_action
  - actor: receiver_actor
  - channel: receiver_channel
  - cluster_id: cluster_id
  - created_at: created_at
  - domain: domain
  - id: receiver_id
  - name: name
  - params: receiver_params
  - project: project
  - type: receiver_type
  - updated_at: updated_at
  - user: user

Response Example
----------------

.. literalinclude:: samples/receiver-show-response.json
   :language: javascript


Update receiver
==================

.. rest_method::  PATCH /v1/receivers/{receiver_id}

   min_version: 1.7

Updates a receiver.

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
  - receiver_id: receiver_id_url
  - receiver: receiver
  - name: name_req
  - action: receiver_action_req
  - params: receiver_params_req


Request Example
---------------

.. literalinclude:: samples/receiver-update-request.json
   :language: javascript


Response Parameters
-------------------

.. rest_parameters:: parameters.yaml

  - X-OpenStack-Request-Id: request_id
  - receiver: receiver
  - action: receiver_action
  - actor: receiver_actor
  - channel: receiver_channel
  - cluster_id: cluster_id
  - created_at: created_at
  - domain: domain
  - id: receiver_id
  - name: name
  - params: receiver_params
  - project: project
  - type: receiver_type
  - updated_at: updated_at
  - user: user

Response Example
----------------

.. literalinclude:: samples/receiver-update-response.json
   :language: javascript


Delete receiver
===============

.. rest_method::  DELETE /v1/receivers/{receiver_id}

Deletes a receiver.

Response Codes
--------------

.. rest_status_code:: success status.yaml

   - 204

.. rest_status_code:: error status.yaml

   - 400
   - 401
   - 403
   - 404
   - 503

Request Parameters
------------------

This operation does not accept a request body.

.. rest_parameters:: parameters.yaml

  - OpenStack-API-Version: microversion
  - receiver_id: receiver_id_url


Response Parameters
-------------------

.. rest_parameters:: parameters.yaml

  - X-OpenStack-Request-Id: request_id

This operation does not return a response body.


Notify receiver
===============

.. rest_method::  POST /v1/receivers/{receiver_id}/notify

Notifies message type receiver.

Response Codes
--------------

.. rest_status_code:: success status.yaml

   - 202

.. rest_status_code:: error status.yaml

   - 400
   - 401
   - 403
   - 404
   - 503

Request Parameters
------------------

This operation does not accept a request body.

.. rest_parameters:: parameters.yaml

  - OpenStack-API-Version: microversion
  - receiver_id: receiver_id_url


Response Parameters
-------------------

.. rest_parameters:: parameters.yaml

  - X-OpenStack-Request-Id: request_id

This operation does not return a response body.
