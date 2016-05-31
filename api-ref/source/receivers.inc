=====================
Receivers (receivers)
=====================

Lists all receivers and creates, shows information for, and deletes a receiver.


List receivers
==============

.. rest_method::  GET /v1/receivers

Lists all receivers.


Normal response codes: 200

Error response codes:

- badRequest (400)
- unauthorized (401)
- forbidden (403)
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
  - type: receiver_type_query
  - user: user_query
  - cluster_id: cluster_identity_query
  - action: receiver_action_query

Response Parameters
-------------------

.. rest_parameters:: parameters.yaml

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

Normal response codes: 201

Error response codes:

- badRequest (400)
- unauthorized (401)
- forbidden (403)
- internalError(500)
- serviceUnavailable (503)


Request Parameters
------------------

.. rest_parameters:: parameters.yaml

  - OpenStack-API-Version: microversion
  - receiver: receiver
  - name: name
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

Normal response codes: 200

Error response codes:

- badRequest (400)
- unauthorized (401)
- forbidden (403)
- notFound(404)
- serviceUnavailable (503)

Request Parameters
------------------

.. rest_parameters:: parameters.yaml

  - OpenStack-API-Version: microversion
  - receiver_id: receiver_id_url

Response Parameters
-------------------

.. rest_parameters:: parameters.yaml

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


Delete receiver
===============

.. rest_method::  DELETE /v1/receivers/{receiver_id}

Deletes a receiver.

Normal response codes: 204

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
  - receiver_id: receiver_id_url


This operation does not accept a request body and does not return a response
body.
