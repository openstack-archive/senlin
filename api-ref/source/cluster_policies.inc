===================================
Cluster Policies (cluster-policies)
===================================

Lists all cluster policies and shows information for a cluster policy.

List all cluster policies
=========================

.. rest_method::  GET /v1/clusters/{cluster_id}/policies

Lists all policies attached to specific cluster

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
  - cluster_id: cluster_id_url
  - enabled: enabled_query
  - sort: sort

Response Parameters
-------------------

.. rest_parameters:: parameters.yaml

  - cluster_policies: cluster_policies
  - cluster_id: cluster_id
  - cluster_name: cluster_name
  - enabled: cluster_policy_enabled
  - id: cluster_policy_id
  - policy_id: policy_id
  - policy_name: policy_name
  - policy_type: policy_type_name

Response Example
----------------

.. literalinclude:: samples/cluster-policies-list-response.json
   :language: javascript


Show cluster_policy details
===========================

.. rest_method::  GET /v1/clusters/{cluster_id}/policies/{policy_id}

Shows details for a cluster policy.

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
  - cluster_id: cluster_id_url
  - policy_id: policy_id_url

Response Parameters
-------------------

.. rest_parameters:: parameters.yaml

  - cluster_policy: cluster_policy
  - cluster_id: cluster_id
  - cluster_name: cluster_name
  - enabled: cluster_policy_enabled
  - id: cluster_policy_id
  - policy_id: policy_id
  - policy_name: policy_name
  - policy_type: policy_type_name

Response Example
----------------

.. literalinclude:: samples/cluster-policy-show-response.json
   :language: javascript
