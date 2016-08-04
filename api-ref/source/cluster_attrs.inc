==================================
Cluster Attributes (cluster_attrs)
==================================

Lists attribute values across all nodes in a cluster.

List cluster attributes
=======================

.. rest_method::  GET /v1/clusters/{cluster_id}/attrs/{path}

  - min_version: 1.2

Collect the specified node attribute across a specific cluster.

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
  - path: path_url

Response Parameters
-------------------

.. rest_parameters:: parameters.yaml

  - attr_value: attr_value
  - cluster_attributes: cluster_attributes
  - id: node_id

Response Example
----------------

.. literalinclude:: samples/cluster-attrs-list-response.json
   :language: javascript
