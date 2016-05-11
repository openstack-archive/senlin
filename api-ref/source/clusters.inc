.. -*- rst -*-

========
Clusters
========

Lists all clusters and creates, shows information for, updates, deletes, and
triggers an action on a cluster.


List clusters
=============

.. rest_method::  GET /v1/clusters

Lists clusters.


Normal response codes: 200

Error response codes:

- badRequest (400)
- unauthorized (401)
- forbidden (403)
- serviceUnvailable (503)

Request Parameters
------------------

.. rest_parameters:: parameters.yaml

  - OpenStack-API-Version: microversion
  - limit: limit
  - marker: marker
  - sort: sort
  - global_project: global_project
  - name: name_query
  - status: status_query

Response Parameters
-------------------

.. rest_parameters:: parameters.yaml

  - clusters: clusters
  - created_at: created_at
  - data: cluster_data
  - desired_capacity: desired_capacity
  - domain: domain
  - id: cluster_id
  - init_at: cluster_init_at
  - max_size: max_size
  - metadata: metadata
    in: cluster
  - min_size: min_size
  - name: cluster_name
    in: cluster
  - nodes: cluster_nodes
  - policies: cluster_policies_property
  - profile_id: cluster_profile_id
  - profile_name: profile_name
  - project: project
  - status: cluster_status
  - status_reason: cluster_status_reason
    in: cluster
  - timeout: timeout
  - updated_at: updated_at
    in: cluster
  - user: user
    in: cluster

Response Example
----------------

.. literalinclude:: samples/clusters-list-response.json
   :language: javascript


Create cluster
==============

.. rest_method::  POST /v1/clusters

Creates a cluster.

Error response codes: 201

- badRequest (400)
- unauthorized (401)
- forbidden (403)
- internalError(500)
- serviceUnvailable (503)


Request Parameters
------------------

.. rest_parameters:: parameters.yaml

  - OpenStack-API-Version: microversion
  - cluster: cluster
  - name: name
  - desired_capacity: desired_capacity
    optional: true
  - profile_id: profile_id_url
    in: cluster
  - min_size: min_size
    optional: true
  - timeout: timeout
    optional: true
  - max_size: max_size
    optional: true
  - metadata: metadata
    optional: true


Request Example
---------------

.. literalinclude:: samples/cluster-create-request.json
   :language: javascript


Response Parameters
-------------------

.. rest_parameters:: parameters.yaml

  - location: location
  - cluster: cluster
  - created_at: created_at
  - data: cluster_data
  - desired_capacity: desired_capacity
  - domain: domain
  - id: cluster_id
  - init_at: cluster_init_at
  - max_size: max_size
  - metadata: metadata
    in: cluster
  - min_size: min_size
  - name: cluster_name
    in: cluster
  - nodes: cluster_nodes
  - policies: cluster_policies_property
  - profile_id: cluster_profile_id
  - profile_name: profile_name
  - project: project
  - status: cluster_status
  - status_reason: cluster_status_reason
    in: cluster
  - timeout: timeout
  - updated_at: updated_at
    in: cluster
  - user: user
    in: cluster

Response Example
----------------

.. literalinclude:: samples/cluster-create-response.json
   :language: javascript


Show cluster details
====================

.. rest_method::  GET /v1/clusters/{cluster_id}

Shows details for a cluster.

Normal response codes: 200

Error response codes:

- badRequest (400)
- unauthorized (401)
- forbidden (403)
- notFound(404)
- serviceUnvailable (503)

Request Parameters
------------------

.. rest_parameters:: parameters.yaml

  - OpenStack-API-Version: microversion
  - cluster_id: cluster_id_url


Response Example
----------------

.. literalinclude:: samples/cluster-show-response.json
   :language: javascript


Update cluster
==============

.. rest_method::  PATCH /v1/clusters/{cluster_id}

Updates a cluster.

Normal response codes: 202

Error response codes:

- badRequest (400)
- unauthorized (401)
- forbidden (403)
- notFound (404)
- serviceUnvailable (503)

Request
-------

.. rest_parameters:: parameters.yaml

  - OpenStack-API-Version: microversion
  - cluster_id: cluster_id_url
  - cluster: cluster
  - name: cluster_name
    optional: true
  - profile_id: profile_id_url
    in: cluster
    optional: true
  - timeout: timeout
    optional: true
  - metadata: metadata
    optional: true

Request Example
---------------

.. literalinclude:: samples/cluster-update-request.json
   :language: javascript


Response Parameters
-------------------

.. rest_parameters:: parameters.yaml

  - location: location
  - cluster: cluster
  - created_at: created_at
  - data: cluster_data
  - desired_capacity: desired_capacity
  - domain: domain
  - id: cluster_id
  - init_at: cluster_init_at
  - max_size: max_size
  - metadata: metadata
    in: cluster
  - min_size: min_size
  - name: cluster_name
    in: cluster
  - nodes: cluster_nodes
  - policies: cluster_policies_property
  - profile_id: cluster_profile_id
  - profile_name: profile_name
  - project: project
  - status: cluster_status
  - status_reason: cluster_status_reason
    in: cluster
  - timeout: timeout
  - updated_at: updated_at
    in: cluster
  - user: user
    in: cluster

Response Example
----------------

.. literalinclude:: samples/cluster-update-response.json
   :language: javascript


Delete cluster
==============

.. rest_method::  DELETE /v1/clusters/{cluster_id}

Deletes a cluster.

Normal response codes: 202


Request Parameters
------------------

.. rest_parameters:: parameters.yaml

  - OpenStack-API-Version: microversion
  - cluster_id: cluster_id_url

Response Parameters
-------------------

.. rest_parameters:: parameters.yaml

  - location: location
