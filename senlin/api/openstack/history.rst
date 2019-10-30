
API Version History
~~~~~~~~~~~~~~~~~~~

This document summarizes the changes made to the REST API with every bump of
API microversion. The description for each version should be verbose so that
it can be used by both users and developers.


1.1
---

- This is the initial version of the v1 API which supports microversions.
  The v1.1 API is identical to that of v1.0 except for the new supports to
  microversion checking.

  A user can specify a header in the API request::

   OpenStack-API-Version: clustering <version>

  where the ``<version>`` is any valid API version supported. If such a
  header is not provided, the API behaves as if a version request of v1.0
  is received.

1.2
---

- Added ``cluster_collect`` API. This API takes a single parameter ``path``
  and interprets it as a JSON path for extracting node properties. Properties
  values from all nodes are aggregated into a list and returned to users.

- Added ``profile_validate`` API. This API is provided to validate the spec
  of a profile without really creating a profile object.

- Added ``policy_validate`` API. This API validates the spec of a policy
  without creating a policy object.

1.3
---

- Added ``cluster_replace_nodes`` API. This API enables users to replace the
  specified existing nodes with ones that were not members of any clusters.

1.4
---

- Added ``profile_type_ops`` API. This API returns a dictionary containing
  the operations and parameters supported by a specific profile type.

- Added ``node_operation`` API. This API enables users to trigger an
  operation on a node. The operation and its parameters are determined by the
  profile type.

- Added ``cluster_operation`` API. This API enables users to trigger an
  operation on a cluster. The operation and its parameters are determined by
  the profile type.

- Added ``user`` query parameter for listing receivers.

- Added ``destroy_after_deletion`` parameter for deleting cluster members.

1.5
---

- Added ``support_status`` to profile type list.

- Added ``support_status`` to policy type list.

- Added ``support_status`` to profile type show.

- Added ``support_status`` to policy type show.

1.6
---

- Added ``profile_only`` parameter to cluster update request.

- Added ``check`` parameter to node recover request. When this parameter is
  specified, the engine will check if the node is active before performing
  a recover operation.

- Added ``check`` parameter to cluster recover request. When this parameter
  is specified, the engine will check if the nodes are active before
  performing a recover operation.

1.7
---

- Added ``node_adopt`` operation to node.

- Added ``node_adopt_preview`` operation to node.

- Added ``receiver_update`` operation to receiver.

- Added ``service_list`` API.

1.8
---
- Added ``force`` parameter to cluster delete request.
- Added ``force`` parameter to node delete request.

1.9
---
- Added ``cluster_complete_lifecycle`` API.  This API enables users to
  trigger the immediate deletion of the nodes identified for deferred
  deletion during scale-in operation.

1.10
----
- Modified the ``webhook_trigger`` API. Inputs for the targeted action
  are now sent directly in the query body rather than in the params
  field.

1.11
----
- Modified the ``cluster_action`` API. The API now responds with
  response code 409 when a scaling action conflicts with one already
  being processed or a cooldown for a scaling action is encountered.

1.12
----
- Added ``action_update`` API. This API enables users to update the status of
  an action (only CANCELLED is supported). An action that spawns dependent
  actions will attempt to cancel all dependent actions.

1.13
----
- Added ``tainted`` to responses returned by node APIs.

1.14
----
- Added ``cluster_id`` to filters result returned action APIs.
