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
  - init_at: init_at
  - max_size: max_size
  - metadata: metadata
  - min_size: min_size
  - name: name
  - nodes: cluster_nodes
  - policies: cluster_policies_property
  - profile_id: profile_id
  - profile_name: profile_name
  - project: project
  - status: cluster_status
  - status_reason: status_reason
  - timeout: timeout
  - updated_at: updated_at
  - user: user

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
- serviceUnavailable (503)


Request Parameters
------------------

.. rest_parameters:: parameters.yaml

  - OpenStack-API-Version: microversion
  - cluster: cluster
  - name: name
  - desired_capacity: desired_capacity
  - profile_id: profile_identity_req
  - min_size: min_size_req
  - timeout: timeout_req
  - max_size: max_size_req
  - metadata: metadata_req

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
  - init_at: init_at
  - max_size: max_size
  - metadata: metadata
  - min_size: min_size
  - name: name
  - nodes: cluster_nodes
  - policies: cluster_policies_property
  - profile_id: profile_id
  - profile_name: profile_name
  - project: project
  - status: cluster_status
  - status_reason: status_reason
  - timeout: timeout
  - updated_at: updated_at
  - user: user

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
- serviceUnavailable (503)

Request Parameters
------------------

.. rest_parameters:: parameters.yaml

  - OpenStack-API-Version: microversion
  - cluster_id: cluster_id_url

Response Parameters
-------------------

.. rest_parameters:: parameters.yaml

  - cluster: cluster
  - created_at: created_at
  - data: cluster_data
  - desired_capacity: desired_capacity
  - domain: domain
  - id: cluster_id
  - init_at: init_at
  - max_size: max_size
  - metadata: metadata
  - min_size: min_size
  - name: name
  - nodes: cluster_nodes
  - policies: cluster_policies_property
  - profile_id: profile_id
  - profile_name: profile_name
  - project: project
  - status: cluster_status
  - status_reason: status_reason
  - timeout: timeout
  - updated_at: updated_at
  - user: user

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
- serviceUnavailable (503)

Request
-------

.. rest_parameters:: parameters.yaml

  - OpenStack-API-Version: microversion
  - cluster_id: cluster_id_url
  - cluster: cluster
  - name: name_req
  - profile_id: profile_identity
  - timeout: timeout_req
  - metadata: metadata_req

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
  - init_at: init_at
  - max_size: max_size
  - metadata: metadata
  - min_size: min_size
  - name: name
  - nodes: cluster_nodes
  - policies: cluster_policies_property
  - profile_id: profile_id
  - profile_name: profile_name
  - project: project
  - status: cluster_status
  - status_reason: status_reason
  - timeout: timeout
  - updated_at: updated_at
  - user: user

Response Example
----------------

.. literalinclude:: samples/cluster-update-response.json
   :language: javascript


Delete cluster
==============

.. rest_method::  DELETE /v1/clusters/{cluster_id}

Deletes a cluster.

A cluster cannot be deleted if there are still policies attached to it.
It cannot be deleted if there are still receivers associated with it. In both
cases, a 409 error will be returned.

Normal response codes: 202

Error response codes:

- unauthorized (401)
- forbidden (403)
- notFound (404)
- conflict(409)
- serviceUnavailable (503)


Request Parameters
------------------

.. rest_parameters:: parameters.yaml

  - OpenStack-API-Version: microversion
  - cluster_id: cluster_id_url

Response Parameters
-------------------

.. rest_parameters:: parameters.yaml

  - location: location


Resize a Cluster
================

.. rest_method::  POST /v1/clusters/{cluster_id}/actions

Resize a cluster.

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
  - cluster_id: cluster_id_url
  - action: action_request
  - adjustment_type: adjustment_type
  - number: adjustment_number
  - min_size: adjustment_min_size
  - max_size: adjustment_max_size
  - min_step: adjustment_min_step
  - strict: adjustment_strict


The ``action_name`` in the request body has to be ``resize``.

Request Example
---------------

.. literalinclude:: samples/cluster-resize-request.json
   :language: javascript

Response Parameters
-------------------

.. rest_parameters:: parameters.yaml

   - location: location


Scale-in a Cluster
===================

.. rest_method::  POST /v1/clusters/{cluster_id}/actions

Shrink the size of a cluster by a given number.

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
  - cluster_id: cluster_id_url
  - action: action_request
  - count: scale_count 


The ``action_name`` in the request body has to be ``scale_in``.

Request Example
---------------

.. literalinclude:: samples/cluster-scale-in-request.json
   :language: javascript

Response Parameters
-------------------

.. rest_parameters:: parameters.yaml

   - location: location


Scale-out a Cluster
===================

.. rest_method::  POST /v1/clusters/{cluster_id}/actions

Expand the size of a cluster by a given number.

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
  - cluster_id: cluster_id_url
  - action: action_request
  - count: scale_count 


The ``action_name`` in the request body has to be ``scale_out``.

Request Example
---------------

.. literalinclude:: samples/cluster-scale-out-request.json
   :language: javascript

Response Parameters
-------------------

.. rest_parameters:: parameters.yaml

   - location: location


Add nodes to a Cluster
======================

.. rest_method::  POST /v1/clusters/{cluster_id}/actions

Add the specified list of nodes to the cluster.

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
  - cluster_id: cluster_id_url
  - action: action_request
  - nodes: cluster_member_nodes


The ``action_name`` in the request body has to be ``add_nodes``.

Request Example
---------------

.. literalinclude:: samples/cluster-add-nodes-request.json
   :language: javascript

Response Parameters
-------------------

.. rest_parameters:: parameters.yaml

   - location: location


Remove nodes from a Cluster
===========================

.. rest_method::  POST /v1/clusters/{cluster_id}/actions

Remove the specified list of nodes from the cluster.

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
  - cluster_id: cluster_id_url
  - action: action_request
  - nodes: cluster_member_nodes


The ``action_name`` in the request body has to be ``del_nodes``.

Request Example
---------------

.. literalinclude:: samples/cluster-del-nodes-request.json
   :language: javascript

Response Parameters
-------------------

.. rest_parameters:: parameters.yaml

   - location: location


Attach a Policy to a Cluster
============================

.. rest_method::  POST /v1/clusters/{cluster_id}/actions

Attach the specified policy to the cluster.

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
  - cluster_id: cluster_id_url
  - action: action_request
  - policy_id: policy_identity
  - enabled: cluster_policy_enabled

The ``action_name`` in the request body has to be ``attach_policy``.

Request Example
---------------

.. literalinclude:: samples/cluster-attach-policy-request.json
   :language: javascript

Response Parameters
-------------------

.. rest_parameters:: parameters.yaml

   - location: location


Detach a Policy from a Cluster
==============================

.. rest_method::  POST /v1/clusters/{cluster_id}/actions

Detach the specified policy from the cluster.

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
  - cluster_id: cluster_id_url
  - action: action_request
  - policy_id: policy_identity

The ``action_name`` in the request body has to be ``detach_policy``.

Request Example
---------------

.. literalinclude:: samples/cluster-detach-policy-request.json
   :language: javascript

Response Parameters
-------------------

.. rest_parameters:: parameters.yaml

   - location: location


Update a Policy on a Cluster
============================

.. rest_method::  POST /v1/clusters/{cluster_id}/actions

Update the specified policy on the cluster.

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
  - cluster_id: cluster_id_url
  - action: action_request
  - policy_id: policy_identity
  - enabled: cluster_policy_enabled

The ``action_name`` in the request body has to be ``update_policy``.

Request Example
---------------

.. literalinclude:: samples/cluster-update-policy-request.json
   :language: javascript

Response Parameters
-------------------

.. rest_parameters:: parameters.yaml

  - location: location


Check a Cluster's Health Status
===============================

.. rest_method::  POST /v1/clusters/{cluster_id}/actions

CHeck the health status of all nodes in a cluster.

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
  - cluster_id: cluster_id_url
  - action: action_request
  - params: check_params

The ``action_name`` in the request body has to be ``check``.

Request Example
---------------

.. literalinclude:: samples/cluster-check-request.json
   :language: javascript

Response Parameters
-------------------

.. rest_parameters:: parameters.yaml

   - location: location


Recover a Cluster to a Healthy Status
=====================================

.. rest_method::  POST /v1/clusters/{cluster_id}/actions

Recover the health status for all nodes in a cluster.

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
  - cluster_id: cluster_id_url
  - action: action_request
  - params: recover_params

The ``action_name`` in the request body has to be ``recover``.

Request Example
---------------

.. literalinclude:: samples/cluster-recover-request.json
   :language: javascript

Response Parameters
-------------------

.. rest_parameters:: parameters.yaml

  - location: location
