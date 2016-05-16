.. -*- rst -*-

=====
Nodes
=====

Lists all nodes, and creates, shows information for, updates, deletes a node.


List nodes
==========

.. rest_method::  GET /v1/nodes

Lists all nodes.


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
  - cluster_id: cluster_id
    in: query
    optional: true
  - name: name_query
  - status: status_query

Response Parameters
-------------------

.. rest_parameters:: parameters.yaml

  - nodes: nodes
  - cluster_id: cluster_id
    in: node
  - created_at: created_at
    in: node
  - data: node_data
  - domain: domain
    in: node
  - id: node_id
  - index: index
  - init_at: init_at
    in: node
  - metadata: metadata
    in: node
  - name: name
    in: node
  - physical_id: physical_id
  - profile_id: node_profile_id
  - profile_name: node_profile_name
  - project: project
    in: node
  - role: role
  - status: node_status
  - status_reason: status_reason
    in: node
  - updated_at: updated_at
    in: node
  - user: user
    in: node

Response Example
----------------

.. literalinclude:: samples/node-list-response.json
   :language: javascript


Create node
===========

.. rest_method::  POST /v1/nodes

Creates a node.

Normal response codes: 202

Error response codes:

- badRequest (400)
- unauthorized (401)
- forbidden (403)
- serviceUnavailable (503)

Request Parameters
------------------

.. rest_parameters:: parameters.yaml

  - OpenStack-API-Version: microversion
  - node: node
  - role: role
    optional: true
  - profile_id: profile_id_url
    in: node
  - cluster_id: cluster_id_url
    in: node
    optional: true
  - name: name
    in: node
    optional: true
  - metadata: metadata
    in: node
    optional: true

Request Example
---------------

.. literalinclude:: samples/node-create-request.json
   :language: javascript

Response Parameters
-------------------

.. rest_parameters:: parameters.yaml

  - location: location
  - node: node
  - cluster_id: cluster_id
    in: node
  - created_at: created_at
    in: node
  - data: node_data
  - domain: domain
    in: node
  - id: node_id
  - index: index
  - init_at: init_at
    in: node
  - metadata: metadata
    in: node
  - name: name
    in: node
  - physical_id: physical_id
  - profile_id: node_profile_id
  - profile_name: node_profile_name
  - project: project
    in: node
  - role: role
  - status: node_status
  - status_reason: status_reason
    in: node
  - updated_at: updated_at
    in: node
  - user: user
    in: node

Response Example
----------------

.. literalinclude:: samples/node-create-response.json
   :language: javascript


Show node details
=================

.. rest_method::  GET /v1/nodes/{node_id}

Shows details about a node.


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
  - node_id: node_id_url
  - show_details: show_details
    optional: true

Response Example
----------------

.. literalinclude:: samples/node-show-response.json
   :language: javascript


Update node
===========

.. rest_method::  PATCH /v1/nodes/{node_id}

Updates a node.

Normal response codes: 202

Error response codes:

- badRequest (400)
- unauthorized (401)
- forbidden (403)
- notFound (404)
- serviceUnavailable (503)


Request
-------

.. rest_parameters:: parameters.yaml

  - OpenStack-API-Version: microversion
  - node_id: node_id_url
  - node: node
  - name: name
    in: node
    optional: true
  - profile_id: profile_id_url
    in: node
    optional: true
  - role: role
    optional: true
  - metadata: metadata
    in: node
    optional: true

Request Example
---------------

.. literalinclude:: samples/node-update-request.json
   :language: javascript

Response Parameters
-------------------

.. rest_parameters:: parameters.yaml

  - location: location
  - node: node
  - cluster_id: cluster_id
    in: node
  - created_at: created_at
    in: node
  - data: node_data
  - domain: domain
    in: node
  - id: node_id
  - index: index
  - init_at: init_at
    in: node
  - metadata: metadata
    in: node
  - name: name
    in: node
  - physical_id: physical_id
  - profile_id: node_profile_id
  - profile_name: node_profile_name
  - project: project
    in: node
  - role: role
  - status: node_status
  - status_reason: status_reason
    in: node
  - updated_at: updated_at
    in: node
  - user: user
    in: node

Response Example
----------------

.. literalinclude:: samples/node-show-response.json
   :language: javascript


Delete node
===========

.. rest_method::  DELETE /v1/nodes/{node_id}

Deletes a node.

Normal response codes: 202

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
  - node_id: node_id_url


Response Parameters
-------------------

.. rest_parameters:: parameters.yaml

   - location: location


Check a Node's Health
=====================

.. rest_method::  POST /v1/nodes/{node_id}/actions

Check the health status of the specified node.

Normal response codes: 202

Error response codes:

- badRequest (400)
- unauthorized (401)
- forbidden (403)
- notFound (404)
- serviceUnavailable (503)

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

   - location: location


Recover a Node to Healthy Status
================================

.. rest_method::  POST /v1/nodes/{node_id}/actions

Recover the specified node to its healthy status.

Normal response codes: 202

Error response codes:

- badRequest (400)
- unauthorized (401)
- forbidden (403)
- notFound (404)
- serviceUnavailable (503)

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

   - location: location
