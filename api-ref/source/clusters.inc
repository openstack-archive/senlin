========
Clusters
========

Lists all clusters and creates, shows information for, updates, deletes, and
triggers an action on a cluster.


List clusters
=============

.. rest_method::  GET /v1/clusters

Lists clusters.

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
  - status: status_query

The sorting keys include ``name``, ``status``, ``init_at``, ``created_at``
and ``updated_at``.

Response Parameters
-------------------

.. rest_parameters:: parameters.yaml

  - X-OpenStack-Request-ID: request_id
  - clusters: clusters
  - created_at: created_at
  - config: cluster_config
  - data: cluster_data
  - dependents: dependents
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
  - config: cluster_config_req
  - cluster: cluster
  - name: cluster_name
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

  - X-OpenStack-Request-ID: request_id
  - Location: location
  - cluster: cluster
  - config: cluster_config
  - created_at: created_at
  - data: cluster_data
  - dependents: dependents
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
  - cluster_id: cluster_id_url

Response Parameters
-------------------

.. rest_parameters:: parameters.yaml

  - X-OpenStack-Request-ID: request_id
  - cluster: cluster
  - config: cluster_config
  - created_at: created_at
  - data: cluster_data
  - dependents: dependents
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
  - cluster_id: cluster_id_url
  - cluster: cluster
  - config: cluster_config_req
  - name: name_req
  - profile_id: profile_identity
  - timeout: timeout_req
  - metadata: metadata_req
  - profile_only: profile_only

Request Example
---------------

.. literalinclude:: samples/cluster-update-request.json
   :language: javascript


Response Parameters
-------------------

.. rest_parameters:: parameters.yaml

  - X-OpenStack-Request-ID: request_id
  - Location: location
  - cluster: cluster
  - config: cluster_config
  - created_at: created_at
  - data: cluster_data
  - dependents: dependents
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

Response Codes
--------------

.. rest_status_code:: success status.yaml

   - 202

.. rest_status_code:: error status.yaml

   - 401
   - 403
   - 404
   - 409
   - 503

Request Parameters
------------------

.. rest_parameters:: parameters.yaml

  - OpenStack-API-Version: microversion
  - cluster_id: cluster_id_url

Response Parameters
-------------------

.. rest_parameters:: parameters.yaml

  - X-OpenStack-Request-ID: request_id
  - Location: location


Resize a Cluster
================

.. rest_method::  POST /v1/clusters/{cluster_id}/actions

Resize a cluster.

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

  - X-OpenStack-Request-ID: request_id
  - Location: location
  - action: action_action

Response Example
----------------

.. literalinclude:: samples/cluster-action-response.json
   :language: javascript


Scale-in a Cluster
===================

.. rest_method::  POST /v1/clusters/{cluster_id}/actions

Shrink the size of a cluster by a given number.

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

  - X-OpenStack-Request-ID: request_id
  - Location: location
  - action: action_action

Response Example
----------------

.. literalinclude:: samples/cluster-action-response.json
   :language: javascript


Scale-out a Cluster
===================

.. rest_method::  POST /v1/clusters/{cluster_id}/actions

Expand the size of a cluster by a given number.

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

  - X-OpenStack-Request-ID: request_id
  - Location: location
  - action: action_action

Response Example
----------------

.. literalinclude:: samples/cluster-action-response.json
   :language: javascript


Add nodes to a Cluster
======================

.. rest_method::  POST /v1/clusters/{cluster_id}/actions

Add the specified list of nodes to the cluster.

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

  - X-OpenStack-Request-ID: request_id
  - Location: location
  - action: action_action

Response Example
----------------

.. literalinclude:: samples/cluster-action-response.json
   :language: javascript


Remove nodes from a Cluster
===========================

.. rest_method::  POST /v1/clusters/{cluster_id}/actions

Remove the specified list of nodes from the cluster.

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
  - cluster_id: cluster_id_url
  - action: action_request
  - nodes: cluster_member_nodes
  - destroy_after_deletion: destroy_after_deletion


The ``action_name`` in the request body has to be ``del_nodes``.

Request Example
---------------

.. literalinclude:: samples/cluster-del-nodes-request.json
   :language: javascript

Response Parameters
-------------------

.. rest_parameters:: parameters.yaml

  - X-OpenStack-Request-ID: request_id
  - Location: location
  - action: action_action

Response Example
----------------

.. literalinclude:: samples/cluster-action-response.json
   :language: javascript


Replace nodes in a Cluster
===========================

.. rest_method::  POST /v1/clusters/{cluster_id}/actions

Replace the specified nodes in a cluster.

This API is only available since API microversion 1.3.

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
  - cluster_id: cluster_id_url
  - action: action_request
  - nodes: cluster_replace_nodes


The ``action_name`` in the request body has to be ``replace_nodes``.

Request Example
---------------

.. literalinclude:: samples/cluster-replace-nodes-request.json
   :language: javascript

Response Parameters
-------------------

.. rest_parameters:: parameters.yaml

  - X-OpenStack-Request-ID: request_id
  - Location: location
  - action: action_action

Response Example
----------------

.. literalinclude:: samples/cluster-action-response.json
   :language: javascript


Attach a Policy to a Cluster
============================

.. rest_method::  POST /v1/clusters/{cluster_id}/actions

Attach the specified policy to the cluster.

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
  - cluster_id: cluster_id_url
  - action: action_request
  - policy_id: policy_identity
  - enabled: cluster_policy_enabled

The ``action_name`` in the request body has to be ``policy_attach``.

Request Example
---------------

.. literalinclude:: samples/cluster-attach-policy-request.json
   :language: javascript

Response Parameters
-------------------

.. rest_parameters:: parameters.yaml

  - X-OpenStack-Request-ID: request_id
  - Location: location
  - action: action_action

Response Example
----------------

.. literalinclude:: samples/cluster-action-response.json
   :language: javascript


Detach a Policy from a Cluster
==============================

.. rest_method::  POST /v1/clusters/{cluster_id}/actions

Detach the specified policy from the cluster.

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
  - cluster_id: cluster_id_url
  - action: action_request
  - policy_id: policy_identity

The ``action_name`` in the request body has to be ``policy_detach``.

Request Example
---------------

.. literalinclude:: samples/cluster-detach-policy-request.json
   :language: javascript

Response Parameters
-------------------

.. rest_parameters:: parameters.yaml

  - X-OpenStack-Request-ID: request_id
  - Location: location
  - action: action_action

Response Example
----------------

.. literalinclude:: samples/cluster-action-response.json
   :language: javascript


Update a Policy on a Cluster
============================

.. rest_method::  POST /v1/clusters/{cluster_id}/actions

Update the specified policy on the cluster.

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

  - X-OpenStack-Request-ID: request_id
  - Location: location
  - action: action_action

Response Example
----------------

.. literalinclude:: samples/cluster-action-response.json
   :language: javascript


Collect Attributes Across a Cluster
===================================

.. rest_method::  GET /v1/clusters/{cluster_id}/attrs/{path}

Aggregate an attribute value across all nodes in a cluster.

This API is only available since API microversion 1.2.

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
  - cluster_id: cluster_id_url
  - path: path_url

Response Parameters
-------------------

.. rest_parameters:: parameters.yaml

  - X-OpenStack-Request-ID: request_id
  - cluster_attributes: cluster_attributes
  - id: node_id
  - value: attr_value

Check a Cluster's Health Status
===============================

.. rest_method::  POST /v1/clusters/{cluster_id}/actions

Check the health status of all nodes in a cluster.

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

  - X-OpenStack-Request-ID: request_id
  - Location: location
  - action: action_action

Response Example
----------------

.. literalinclude:: samples/cluster-action-response.json
   :language: javascript


Recover a Cluster to a Healthy Status
=====================================

.. rest_method::  POST /v1/clusters/{cluster_id}/actions

Recover the health status for all nodes in a cluster.

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
  - cluster_id: cluster_id_url
  - action: action_request
  - params: recover_params

The ``action_name`` in the body must be ``recover``. The valid parameters
include:

- ``operation``: A string specifying the action to be performed for node
  recovery.

- ``operation_params``: An optional dictionary specifying the key-value
  arguments for the specific node recovery action.

- ``check``: A boolean specifying whether the engine should check the actual
  statuses of cluster nodes before performing the recovery action. This
  parameter is added since microversion 1.6 and it defaults to False.

- ``check_capacity``: A boolean specifying whether check the current number of
  nodes and the ``desired_capacity`` field. Will delete nodes if the number of
  nodes is larger than ``desired_capacity``, otherwise, create nodes. This
  parameter is added since microversion 1.7 and it defaults to False.

Request Example
---------------

.. literalinclude:: samples/cluster-recover-request.json
   :language: javascript

Response Parameters
-------------------

.. rest_parameters:: parameters.yaml

  - X-OpenStack-Request-ID: request_id
  - Location: location
  - action: action_action

Response Example
----------------

.. literalinclude:: samples/cluster-action-response.json
   :language: javascript


Perform an Operation on a Cluster
=================================

.. rest_method::  POST /v1/clusters/{cluster_id}/ops

Perform an operation on the specified cluster. The specified operation and its
associated parameters must validate against the profile type of the cluster.

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

  - OpenStack-API-Version: microversion
  - cluster_id: cluster_id_url
  - operation: cluster_operation_request

Request Example
---------------

.. literalinclude:: samples/cluster-operation-request.json
   :language: javascript

Response Parameters
-------------------

.. rest_parameters:: parameters.yaml

  - X-OpenStack-Request-ID: request_id
  - Location: location
  - action: action_action

Response Example
----------------

.. literalinclude:: samples/cluster-action-response.json
   :language: javascript


Complete Lifecycle on a Cluster action
======================================

.. rest_method::  POST /v1/clusters/{cluster_id}/actions

Complete lifecycle action and trigger deletion of nodes.

This API is only available since API microversion 1.9.

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
  - cluster_id: cluster_id_url
  - action: action_request
  - lifecycle_action_token: lifecycle_token_id

The ``action_name`` in the body must be ``complete_lifecycle``.

Request Example
---------------

.. literalinclude:: samples/cluster-complete-lifecycle-request.json
   :language: javascript

Response Parameters
-------------------

.. rest_parameters:: parameters.yaml

  - X-OpenStack-Request-ID: request_id
  - Location: location
  - action: action_action

Response Example
----------------

.. literalinclude:: samples/cluster-action-response.json
   :language: javascript
