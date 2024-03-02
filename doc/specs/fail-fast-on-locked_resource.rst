..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

=============================
Fail fast on locked resources
=============================


When an operation on a locked resource (e.g. cluster or node) is requested,
Senlin creates a corresponding action and calls on the engine dispatcher to
asynchronously process it. If the targeted resource is locked by another
operation, the action will fail to process it and the engine will ask the
dispatcher to retry the action up to three times. If the resource is still
locked after three retries, the action is considered failed. The user making
the operation request will not know that an action has failed until the
retries have been exhausted and it queries the action state from Senlin.

This spec proposes to check the lock status of the targeted resource and fail
immediately if it is locked during the synchronous API call by the user. The
failed action is not automatically retried.  Instead it is up to the user to
retry the API call as desired.


Problem description
===================

The current implementation where failed actions are automatically retried can
lead to starvation situations when a large number of actions on the same target
cluster or node are requested. E.g. if a user requests a 100 scale-in operations
on a cluster, the Senlin engine will take a long time to process the retries and
will not be able to respond to other commands in the meantime.

Another problem with the current implementation is encountered when health
checks are running against a cluster and the user is simultaneously performing
operations on it. When the health check thread determines that a node is
unhealthy (1), the user could request a cluster scale-out (2) before the health
check thread had a chance to call node recovery (4). In that case the first node
recovery will fail because the cluster is already locked and the node recovery
action will be retried in the background.  However after the scale-out
completes and the next iteration of the health check runs, it might still see
the node as unhealthy and request another node recovery.  In that case the node
will be unnecessarily recovered twice.

::

  +---------------+                                   +---------------+                +-------+
  | HealthManager |                                   | SenlinEngine  |                | User  |
  +---------------+                                   +---------------+                +-------+
          | -----------------\                                |                            |
          |-| Health check   |                                |                            |
          | | thread starts. |                                |                            |
          | |----------------|                                |                            |
          |                                                   |                            |
          | (1) Is Node healthy? No.                          |                            |
          |-------------------------                          |                            |
          |                        |                          |                            |
          |<------------------------                          |                            |
          |                                                   |                            |
          |                                                   |     (2) Scale Out Cluster. |
          |                                                   |<---------------------------|
          |                                                   |                            |
          |                                                   | (3) Lock cluster.          |
          |                                                   |------------------          |
          |                                                   |                 |          |
          |                                                   |<-----------------          |
          |                                                   |                            |
          | (4) Recover node.                                 |                            |
          |-------------------------------------------------->|                            |
          |                                                   |                            |
          |                  (5) Recover node action created. |                            |
          |<--------------------------------------------------|                            |
          |                                                   |                            |
          |                                                   | (6) Cluster is locked.     |
          |                                                   | Retry node recover.        |
          |                                                   |-----------------------     |
          |                                                   |                      |     |
          |                                                   |<----------------------     |
          |                                                   |                            |
          | (7) Get node recover action status.               |                            |
          |-------------------------------------------------->|                            |
          |                                                   |                            |
          |         (8) Node recover action status is failed. |                            |
          |<--------------------------------------------------|                            |
          | ---------------\                                  |                            |
          |-| Health check |                                  |                            |
          | | thread ends. |                                  |                            |
          | |--------------|                                  |                            |
          |                                                   |                            |

Finally, there are other operations that can lead to locked clusters that are
never released as indicated in this bug:
https://bugs.launchpad.net/senlin/+bug/1725883

Use Cases
---------

As a user, I want to know right away if an operation on a cluster or node fails
because the cluster or node is locked by another operation. By being able to
receive immediate feedback when an operation fails due to a locked resource, the
Senlin engine will adhere to the fail-fast software design principle [1] and
thereby reducing the software complexity and potential bugs due to
locked resources.

Proposed change
===============


1. **All actions**

   Before an action is created, check if the targeted cluster or node is
   already locked in the cluster_lock or node_lock tables.

      * If the target cluster or node is locked, throw a ResourceIsLocked
        exception.
      * If the action table already has an active action operating on the
        target cluster or node, throw a ActionConflict exception. An action
        is defined as active if its status is one of the following:
        READY, WAITING, RUNNING OR WAITING_LIFECYCLE_COMPLETION.
      * If the target cluster or node is not locked, proceed to create the
        action.

2. **ResourceIsLocked**

   New exception type that corresponds to a 409 HTTP error code.

3. **ActionConflict**

   New exception type that corresponds to a 409 HTTP error code.


Alternatives
------------

None


Data model impact
-----------------

None

REST API impact
---------------

* Alls Action (changed in **bold**)

  ::

    POST /v1/clusters/{cluster_id}/actions


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
    **409 - Conflict**         **The requested resource is locked by**
                               **another action**
    503 - Service Unavailable  Service unavailable. This is mostly
                               caused by service configuration errors which
                               prevents the service from successful start up.
    ========================== ===============================================



Security impact
---------------

None

Notifications impact
--------------------


Other end user impact
---------------------

The python-senlinclient requires modification to return the 409 HTTP error code
to the user.

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

Unit tests and tempest tests are needed for the new action request behavior when
a resource is locked.

Documentation Impact
====================

End User Guide needs to updated to describe the new behavior of action
requests when a target resource is locked.  The End User Guide should also
describe that the user can retry an action if they receive 409 HTTP error code.

References
==========

[1] https://www.martinfowler.com/ieeeSoftware/failFast.pdf


History
=======

None
