=====
Nodes
=====

Lists all nodes, and creates, shows information for, updates, deletes a node.


List nodes
==========

.. rest_method::  GET /v1/nodes

Lists all nodes.

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
  - cluster_id: cluster_identity_query
  - name: name_query
  - status: status_query

Response Parameters
-------------------

.. rest_parameters:: parameters.yaml

  - X-OpenStack-Request-ID: request_id
  - nodes: nodes
  - cluster_id: cluster_id
  - created_at: created_at
  - data: node_data
  - domain: domain
  - id: node_id
  - index: index
  - init_at: init_at
  - metadata: metadata
  - name: name
  - physical_id: physical_id
  - profile_id: profile_id
  - profile_name: profile_name
  - project: project
  - role: role
  - status: node_status
  - status_reason: status_reason
  - updated_at: updated_at
  - user: user

Response Example
----------------

.. literalinclude:: samples/node-list-response.json
   :language: javascript


Create node
===========

.. rest_method::  POST /v1/nodes

Creates a node.

Response Codes
--------------

.. rest_status_code:: success status.yaml

   - 202

.. rest_status_code:: error status.yaml

   - 400
   - 401
   - 403
   - 503

Request Parameters
------------------

.. rest_parameters:: parameters.yaml

  - OpenStack-API-Version: microversion
  - node: node
  - role: role_req
  - profile_id: profile_identity_req
  - cluster_id: node_cluster_identity
  - name: name
  - metadata: metadata_req

Request Example
---------------

.. literalinclude:: samples/node-create-request.json
   :language: javascript

Response Parameters
-------------------

.. rest_parameters:: parameters.yaml

  - X-OpenStack-Request-ID: request_id
  - Location: location
  - node: node
  - cluster_id: cluster_id
  - created_at: created_at
  - data: node_data
  - domain: domain
  - id: node_id
  - index: index
  - init_at: init_at
  - metadata: metadata
  - name: name
  - physical_id: physical_id
  - profile_id: profile_id
  - profile_name: profile_name
  - project: project
  - role: role
  - status: node_status
  - status_reason: status_reason
  - updated_at: updated_at
  - user: user

Response Example
----------------

.. literalinclude:: samples/node-create-response.json
   :language: javascript


Show node details
=================

.. rest_method::  GET /v1/nodes/{node_id}

Shows details about a node.

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
  - node_id: node_id_url
  - show_details: show_details

Response Parameters
-------------------

.. rest_parameters:: parameters.yaml

  - X-OpenStack-Request-ID: request_id
  - node: node
  - cluster_id: cluster_id
  - created_at: created_at
  - data: node_data
  - domain: domain
  - id: node_id
  - index: index
  - init_at: init_at
  - metadata: metadata
  - name: name
  - physical_id: physical_id
  - profile_id: profile_id
  - profile_name: profile_name
  - project: project
  - role: role
  - status: node_status
  - status_reason: status_reason
  - updated_at: updated_at
  - user: user

Response Example
----------------

.. literalinclude:: samples/node-show-response.json
   :language: javascript


Update node
===========

.. rest_method::  PATCH /v1/nodes/{node_id}

Updates a node.

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

.. rest_parameters:: parameters.yaml

  - OpenStack-API-Version: microversion
  - node_id: node_id_url
  - node: node
  - name: name_req
  - profile_id: profile_identity
  - role: role_req
  - metadata: metadata_req

Request Example
---------------

.. literalinclude:: samples/node-update-request.json
   :language: javascript

Response Parameters
-------------------

.. rest_parameters:: parameters.yaml

  - X-OpenStack-Request-ID: request_id
  - Location: location
  - node: node
  - cluster_id: cluster_id
  - created_at: created_at
  - data: node_data
  - domain: domain
  - id: node_id
  - index: index
  - init_at: init_at
  - metadata: metadata
  - name: name
  - physical_id: physical_id
  - profile_id: profile_id
  - profile_name: profile_name
  - project: project
  - role: role
  - status: node_status
  - status_reason: status_reason
  - updated_at: updated_at
  - user: user

Response Example
----------------

.. literalinclude:: samples/node-show-response.json
   :language: javascript


Delete node
===========

.. rest_method::  DELETE /v1/nodes/{node_id}

Deletes a node.

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

.. rest_parameters:: parameters.yaml

  - OpenStack-API-Version: microversion
  - node_id: node_id_url

Response Parameters
-------------------

.. rest_parameters:: parameters.yaml

  - X-OpenStack-Request-ID: request_id
  - Location: location


Check a Node's Health
=====================

.. rest_method::  POST /v1/nodes/{node_id}/actions

Check the health status of the specified node.

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

.. rest_parameters:: parameters.yaml

  - node_id: node_id_url
  - action: action_request

The ``action_name`` in the body must be ``check``.

Request Example
---------------

.. literalinclude:: samples/node-check-request.json
   :language: javascript

Response Parameters
-------------------

.. rest_parameters:: parameters.yaml

  - X-OpenStack-Request-ID: request_id
  - Location: location


Recover a Node to Healthy Status
================================

.. rest_method::  POST /v1/nodes/{node_id}/actions

Recover the specified node to its healthy status.

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

.. rest_parameters:: parameters.yaml

  - node_id: node_id_url
  - action: action_request

The ``action_name`` in the body must be ``recover``.

Request Example
---------------

.. literalinclude:: samples/node-recover-request.json
   :language: javascript

Response Parameters
-------------------

.. rest_parameters:: parameters.yaml

  - X-OpenStack-Request-ID: request_id
  - Location: location


Perform an Operation on a Node
==============================

.. rest_method::  POST /v1/nodes/{node_id}/ops

   min_version: 1.4

Perform the specified operation on the specified node.

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

.. rest_parameters:: parameters.yaml

  - node_id: node_id_url
  - operation: operation_request

Request Example
---------------

.. literalinclude:: samples/node-operation-request.json
   :language: javascript

Response Parameters
-------------------

.. rest_parameters:: parameters.yaml

  - X-OpenStack-Request-ID: request_id
  - Location: location
