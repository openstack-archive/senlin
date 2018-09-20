..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

=================================================
Multiple polling detection modes in Health Policy
=================================================

The health policy allows a user specify a detection mode to use for checking
node health. In the current implementation only one of the following detection
modes is allowed:

* NODE_STATUS_POLLING
* NODE_STATUS_POLL_URL
* LIFECYCLE_EVENTS

This spec proposes to let the user specify multiple polling detection modes in
the same health policy. E.g. the user can specify both NODE_STATUS_POLLING and
NODE_STATUS_POLL_URL detection modes in the same health policy.


Problem description
===================

The current implementation only allows a health policy to specify a single
detection mode to use for verifying the node health. However, there are
situations in which the user would want to have two detection modes checked and
only rebuild a node if both modes failed. Using multiple detection modes has the
benefit of fault tolerant health checks where one detection mode takes over in
case the other detection mode cannot be completed.


Use Cases
---------

As a user, I want to specify multiple polling detection modes for a given health
policy. The order of the polling detection modes used when creating the health
policy specifies the order of evaluation for the health checks. As a user, I also
want to be able to specify if a single detection mode failure triggers a node
rebuild or if all detection modes have to fail before a node is considered
unhealthy.


Proposed change
===============


1. **Health Policy**

   Increment health policy version to 1.1 and implement the following schema:

::

  name: senlin.policy.health-1.1
  schema:
    detection:
      description: Policy aspect for node failure detection.
      required: true
      schema:
        detection_modes:
          description: List of node failure detection modes.
          required: false
          schema:
            '*':
              description: Node failure detection mode to try
              required: false
              schema:
                options:
                  default: {}
                  required: false
                  schema:
                    poll_url:
                      default: ''
                      description: URL to poll for node status. See documentation for
                        valid expansion parameters. Only required when type is 'NODE_STATUS_POLL_URL'.
                      required: false
                      type: String
                      updatable: false
                    poll_url_conn_error_as_unhealthy:
                      default: true
                      description: Whether to treat URL connection errors as an indication
                        of an unhealthy node. Only required when type is 'NODE_STATUS_POLL_URL'.
                      required: false
                      type: Boolean
                      updatable: false
                    poll_url_healthy_response:
                      default: ''
                      description: String pattern in the poll URL response body that
                        indicates a healthy node. Required when type is 'NODE_STATUS_POLL_URL'.
                      required: false
                      type: String
                      updatable: false
                    poll_url_retry_interval:
                      default: 3
                      description: Number of seconds between URL polling retries before
                        a node is considered down. Required when type is 'NODE_STATUS_POLL_URL'.
                      required: false
                      type: Integer
                      updatable: false
                    poll_url_retry_limit:
                      default: 3
                      description: Number of times to retry URL polling when its return
                        body is missing POLL_URL_HEALTHY_RESPONSE string before a node
                        is considered down. Required when type is 'NODE_STATUS_POLL_URL'.
                      required: false
                      type: Integer
                      updatable: false
                    poll_url_ssl_verify:
                      default: true
                      description: Whether to verify SSL when calling URL to poll for
                        node status. Only required when type is 'NODE_STATUS_POLL_URL'.
                      required: false
                      type: Boolean
                      updatable: false
                  type: Map
                  updatable: false
                type:
                  constraints:
                  - constraint:
                    - LIFECYCLE_EVENTS
                    - NODE_STATUS_POLLING
                    - NODE_STATUS_POLL_URL
                    type: AllowedValues
                  description: Type of node failure detection.
                  required: true
                  type: String
                  updatable: false
              type: Map
              updatable: false
          type: List
          updatable: false
        interval:
          default: 60
          description: Number of seconds between pollings. Only required when type is
            'NODE_STATUS_POLLING' or 'NODE_STATUS_POLL_URL'.
          required: false
          type: Integer
          updatable: false
        node_update_timeout:
          default: 300
          description: Number of seconds since last node update to wait before checking
            node health.
          required: false
          type: Integer
          updatable: false
        recovery_conditional:
          constraints:
          - constraint:
            - ALL_FAILED
            - ANY_FAILED
            type: AllowedValues
          default: ANY_FAILED
          description: The conditional that determines when recovery should be performed
            in case multiple detection modes are specified. 'ALL_FAILED'
            means that all detection modes have to return failed health checks before
            a node is recovered. 'ANY_FAILED' means that a failed health
            check with a single detection mode triggers a node recovery.
          required: false
          type: String
          updatable: false
      type: Map
      updatable: false
    recovery:
      description: Policy aspect for node failure recovery.
      required: true
      schema:
        actions:
          description: List of actions to try for node recovery.
          required: false
          schema:
            '*':
              description: Action to try for node recovery.
              required: false
              schema:
                name:
                  constraints:
                  - constraint:
                    - REBOOT
                    - REBUILD
                    - RECREATE
                    type: AllowedValues
                  description: Name of action to execute.
                  required: true
                  type: String
                  updatable: false
                params:
                  description: Parameters for the action
                  required: false
                  type: Map
                  updatable: false
              type: Map
              updatable: false
          type: List
          updatable: false
        fencing:
          description: List of services to be fenced.
          required: false
          schema:
            '*':
              constraints:
              - constraint:
                - COMPUTE
                type: AllowedValues
              description: Service to be fenced.
              required: true
              type: String
              updatable: false
          type: List
          updatable: false
        node_delete_timeout:
          default: 20
          description: Number of seconds to wait for node deletion to finish and start
            node creation for recreate recovery option. Required when type is 'NODE_STATUS_POLL_URL
            and recovery action is RECREATE'.
          required: false
          type: Integer
          updatable: false
        node_force_recreate:
          default: false
          description: Whether to create node even if node deletion failed. Required
            when type is 'NODE_STATUS_POLL_URL' and action recovery action is RECREATE.
          required: false
          type: Boolean
          updatable: false
      type: Map
      updatable: false



Alternatives
------------

None


Data model impact
-----------------

None

REST API impact
---------------

None

Security impact
---------------

None

Notifications impact
--------------------

None

Other end user impact
---------------------

None

Performance Impact
------------------

None

Other deployer impact
---------------------

None

Developer impact
----------------

None


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

Unit tests and tempest tests are needed to test multiple detection modes.

Documentation Impact
====================

End User Guide needs to be updated to describe how multiple detection modes can
be set.

References
==========

None

History
=======

None
