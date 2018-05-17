..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

=======================================
Add lifecycle hooks for scale in action
=======================================


The AWS autoscaling service provides a 'lifecycle hook' feature that Senlin
currently lacks. Lifecycle hooks during scaling operations allow the user or
an application to perform custom setup or clean-up of instances.

This spec proposes to add lifecycle hook specific properties to the deletion
policy applied during node removal operations (i.e. scale-in, cluster-resize,
cluster-node-del and node-delete actions). The lifecycle hook properties specify
a timeout and a Zaqar queue as the notification target. If the node removal
operation detects that a deletion policy with lifecycle hook properties is
attached, it will send a lifecycle hook message to the notification target
for each node identified for deletion. The lifecycle hook message contains the
node ID of the instance to be deleted and a lifecycle action token. In
addition, the node removal operation will defer the actual deletion of those
nodes until the timeout in the deletion policy has been reached.

This spec also adds a new 'complete lifecycle' API endpoint. When this API
endpoint is called with the lifecycle action token from the lifecycle hook
message, Senlin immediately deletes the node that was identified by the
node removal operation for deletion. Calling the 'complete lifecycle' API
endpoint also cancels the deferred node deletion initiated by the node removal
operation.

Problem description
===================

When performing a scale-in operation with Senlin, an instance might require
custom cleanup. A lifecycle hook sends a notification that lets the receiving
application perform those custom clean-up steps on an instance before the node
is deleted.

After the clean-up has finished, the application can wait for an expired
lifecycle hook timeout that automatically triggers the deletion of the nodes.
Alternatively, the application can send a 'complete lifecycle' message to
Senlin to proceed with the node deletion without waiting for the lifecycle
hook timeout to expire.

Use Cases
---------

The typical use case occurs when a node must move its in-progress workload off
to another node before it can be terminated. During auto scale-in events, an
application must receive a Zaqar message to start those custom cleanups on
the termination-pending nodes. If the application does not complete the
lifecycle by a specified timeout, Senlin automatically deletes the node. If
the application finishes the cleanup before the specified timeout expires,
the application notifies Senlin to complete the lifecycle for a specified
node. This triggers the immediate deletion of the node.

Proposed change
===============

1. **Deletion policy**

   New lifecycle hook specific properties:

   * timeout
   * target type
   * target name

2. **New action status**

   WAITING_LIFECYCLE_COMPLETION

3. **Scale-in, cluster-resize, cluster-node-del, node-delete actions**

   If deletion policy with lifecycle hook properties is attached, the above
   actions differ from current implementation as follows:

   * For each node identified to be deleted:

     * DEL_NODE action is created with status as WAITING_LIFECYCLE_COMPLETION.
     * Send a message to the target name from deletion policy.
       The message contains:

       * lifecycle_action_token: same as DEL_NODE action ID
       * node_id

   * Create dependencies between the DEL_NODE actions and the original action

   * Wait for dependent actions to complete or lifecycle timeout specified in
     deletion policy to expire

   * If lifecycle timeout is reached:

    * For each DEL_NODE action:

      * If DEL_NODE action status is WAITING_LIFECYCLE_COMPLETION, then change
        action status to READY

    * Call dispatcher.start_action

4. **'Complete lifecycle' API endpoint**

   The new API endpoint to signal completion of lifecycle.  It expects
   lifecycle_action_token as a parameter.

   * Use lifecycle_action_token to load DEL_NODE action
   * If DEL_NODE action status is WAITING_LIFECYCLE_COMPLETION, then change
     action state to READY and call dispatcher.start_action

Alternatives
------------

Alternatively, attach a deletion policy with a grace period.  The grace
period allows an application to perform clean-up of instances.  However,
Senlin must implement event notifications in form of a HTTP sink or a Zaqar
queue so that the third party application knows which nodes are selected for
deletion.

This solution lacks the 'complete lifecycle' action allowing an application to
request the node deletion before the timeout expires. This is undesirable
because the scale-in action locks the cluster while it is sleeping for the
grace period value. This will not work if the application finishes the
clean-up of the instances before the grace period expires and it wants to
perform another cluster action such as scale-out.


Data model impact
-----------------

None

REST API impact
---------------

* Complete Lifecycle Action

  ::

    POST /v1/clusters/{cluster_id}/actions

  Complete lifecycle action and trigger deletion of nodes.

  - Normal HTTP response code(s):

    =============== ===========================================================
    Code            Reason
    =============== ===========================================================
    202 - Accepted  Request was accepted for processing, but the processing has
                    not been completed. A 'location' header is included in the
                    response which contains a link to check the progress of the
                    request.
    =============== ===========================================================

  - Expected error HTTP response code(s):

    ========================== ===============================================
    Code                       Reason
    ========================== ===============================================
    400 - Bad Request          Some content in the request was invalid.
    401 - Unauthorized         User must authenticate before making a request.
    403 - Forbidden            Policy does not allow current user to do this
                               operation.
    404 - Not Found            The requested resource could not be found.
    503 - Service Unavailable  Service unavailable. This is mostly
                               caused by service configuration errors which
                               prevents the service from successful start up.
    ========================== ===============================================

  - Request Parameters:

    =================================  =======  ======= =======================
    Name                                In      Type    Description
    =================================  =======  ======= =======================
    OpenStack-API-Version (Optional)   header   string  API microversion
                                                        request.
                                                        Takes the form of
                                                        OpenStack-API-Version:
                                                        clustering 1.0, where
                                                        1.0 is the requested
                                                        API version.
    cluster_id                         path     string  The name, UUID or
                                                        short-UUID of a cluster
                                                        object.
    action                             body     object  A structured definition
                                                        of an action to be
                                                        executed. The object is
                                                        usually expressed as:
                                                         <action_name>: {
                                                          <param_1>: <value_1>

                                                          <param_2>: <value_2>

                                                          ...
                                                         }

                                                        The <action_name>
                                                        indicates the requested
                                                        action while the
                                                        <param> keys provide
                                                        the associated
                                                        parameters to the
                                                        action. Each
                                                        individual action
                                                        has its own set of
                                                        parameters.

                                                        The action_name in the
                                                        request body has to be
                                                        complete_lifecycle.
    lifecycle_action_token             body     UUID    The UUID of the
                                                        lifecycle action to be
                                                        completed.
    =================================  =======  ======= =======================

  - Request example::

      {
        "complete_lifecycle": {
          "lifecycle_action_token": "ffbb9175-d510-4bc1-b676-c6aba2a4ca81"
        }
      }

  - Response parameters:

    =================================  =======  ======= =======================
    Name                               In       Type    Description
    =================================  =======  ======= =======================
    X-OpenStack-Request-ID (Optional)  header   string  A unique ID for
                                                        tracking service
                                                        request. The request
                                                        ID associated with
                                                        the request by default
                                                        appears in the service
                                                        logs
    Location                           header   string  For asynchronous object
                                                        operations, the
                                                        location header
                                                        contains a string
                                                        that can be interpreted
                                                        as a relative URI
                                                        from where users can
                                                        track the progress
                                                        of the action triggered
    action                             body     string  A string
                                                        representation of
                                                        the action for
                                                        execution.
    =================================  =======  ======= =======================

* Deletion Policy

  Additional properties specific to the lifecycle hook are added to the Deletion
  policy.  The existing properties from senlin.policy.deletion-1.0 are carried
  over into senlin.policy.deletion-1.1 and not listed below.

  ::

    name: senlin.policy.deletion-1.1
    schema:
      hooks:
        description: Lifecycle hook properties
        required: false
        type: Map
        updatable: false
        schema:
          type:
            constraints:
            - constraint:
              - zaqar
              - webhook
              type: AllowedValues
            default: zaqar
            description: The type of lifecycle hook
            required: false
            type: String
            updatable: false
          params:
            description: Specific parameters for the hook type
            required: false
            type: Map
            updatable: false
            schema:
                queue:
                  description: Zaqar queue to receive lifecycle hook message
                  required: false
                  type: String
                  updatable: false
                url:
                  description: Url sink to which to send lifecycle hook message
                  required: false
                  type: String
                  updatable: false
          timeout:
            description: Number of seconds before actual deletion happens
            required: false
            type: Integer
            updatable: false


* Lifecycle Hook Message

  The lifecycle hook message is sent to the Zaqar queue when a scale_in
  request is received and the cluster has the deletion policy with lifecycle
  hook properties attached. It includes:

  ==========================  ======= =======================================
  Name                        Type    Description
  ==========================  ======= =======================================
  lifecycle_action_token      UUID    The action ID of the 'complete lifecycle'
                                      action.
  node_id                     UUID    The cluster node ID to be terminated
  lifecycle_transition_type   string  The type of lifecycle transition
  ==========================  ======= =======================================

Security impact
---------------

None

Notifications impact
--------------------

A new notification is sent to a specified Zaqar queue.

Other end user impact
---------------------

The python-senlinclient requires modification to allow the user to perform
'complete lifecycle' action.

Performance Impact
------------------

None

Other deployer impact
---------------------

None

Developer impact
----------------

The openstacksdk requires modification to add the new 'complete
lifecycle' API endpoint.


Implementation
==============

Assignee(s)
-----------

dtruong@blizzard.com

Work Items
----------

None

Dependencies
============

None


Testing
=======

Tempest tests for the new API endpoint and policy will be added.

Documentation Impact
====================

End User Guide needs to updated for new API endpoint, deletion policy changes
and behavior changes to scale-in, cluster-resize, cluster-node-del and
node-delete actions.

References
==========

None


History
=======

None
