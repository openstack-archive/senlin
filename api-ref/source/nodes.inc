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

The sorting keys include ``name``, ``index``, ``status``, ``init_at``,
``created_at`` and ``updated_at``.

Response Parameters
-------------------

.. rest_parameters:: parameters.yaml

  - X-OpenStack-Request-ID: request_id
  - nodes: nodes
  - cluster_id: cluster_id
  - created_at: created_at
  - data: node_data
  - dependents: dependents
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
  - tainted: tainted
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
  - name: node_name
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
  - dependents: dependents
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
  - tainted: tainted
  - updated_at: updated_at
  - user: user

Response Example
----------------

.. literalinclude:: samples/node-create-response.json
   :language: javascript


Adopt node
==========

.. rest_method::  POST /v1/nodes/adopt

   min_version: 1.7

Adopts a node.

This API is only available since API microversion 1.7.

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
  - identity: identity
  - metadata: metadata_req
  - name: node_name_adopt
  - overrides: overrides
  - role: role_req
  - snapshot: snapshot
  - type: profile_type_name

Request Example
---------------

.. literalinclude:: samples/node-adopt-request.json
   :language: javascript

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
  - tainted: tainted
  - updated_at: updated_at
  - user: user

Response Example
----------------

.. literalinclude:: samples/node-adopt-response.json
   :language: javascript


Adopt node (preview)
====================

.. rest_method::  POST /v1/nodes/adopt-preview

   min_version: 1.7

Preview a node adoption.

This API is only available since API microversion 1.7.

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
  - identity: identity
  - overrides: overrides
  - snapshot: snapshot
  - type: profile_type_name

Request Example
---------------

.. literalinclude:: samples/node-adopt-preview-request.json
   :language: javascript

Response Parameters
-------------------

.. rest_parameters:: parameters.yaml

  - X-OpenStack-Request-ID: request_id
  - node_preview: node_preview
  - cluster_id: cluster_id
  - type: profile_type_name
  - version: profile_type_version
  - properties: profile_spec

Response Example
----------------

.. literalinclude:: samples/node-adopt-preview-response.json
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
  - dependents: dependents
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
  - tainted: tainted
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
  - tainted: tainted_req

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
  - dependents: dependents
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
  - tainted: tainted
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
  - action: action_action

Response Example
----------------

.. literalinclude:: samples/node-action-response.json
   :language: javascript



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

The ``action_name`` in the body must be ``recover``. The valid parameters
include:

- ``operation``: A string specifying the action to be performed for node
  recovery.

- ``operation_params``: An optional dictionary specifying the key-value
  arguments for the specific node recovery action.

- ``check``: A boolean specifying whether the engine should check the node's
  actual status before performing the recovery action. This parameter is added
  since microversion 1.6.


Request Example
---------------

.. literalinclude:: samples/node-recover-request.json
   :language: javascript

Response Parameters
-------------------

.. rest_parameters:: parameters.yaml

  - X-OpenStack-Request-ID: request_id
  - Location: location
  - action: action_action

Response Example
----------------

.. literalinclude:: samples/node-action-response.json
   :language: javascript


Perform an Operation on a Node
==============================

.. rest_method::  POST /v1/nodes/{node_id}/ops

   min_version: 1.4

Perform the specified operation on the specified node.

This API is only available since API microversion 1.4.

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
  - action: action_action

Response Example
----------------

.. literalinclude:: samples/node-action-response.json
   :language: javascript
