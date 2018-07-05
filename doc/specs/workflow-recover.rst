..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

==========================================
Support Workflow Service as Recover Action
==========================================


Nowadays, Senlin supports many different actions for the purpose of cluster
management. Especially for auto-healing use case, Senlin provides check
and recover to support customizable loop by health policy. Where three
kinds of detection types can be chosen: NODE_STATUS_POLLING, LB_STATUS_POLLING,
VM_LIFECYCLE_EVENTS. Once any failure is detected of the given type, recover
action can be executed automatically or manually. Also in the health policy,
users can define list of actions under recovery category, which can be
applied in order on a failed node.

Some simple recover actions can be embedded into the Senlin like rebuild, or
recreate. But some complex actions are a chain of simple actions. For an example,
evacuation of VM servers needs to verify if the targeted node can be evacuated,
then execute the action, and confirmation is often needed to check if the action
succeeds or not. To support these cases, this spec targets to extend Senlin
to integrate with mistral workflow service so as to trigger the user-defined
workflow for the recover options.

Problem description
===================

This spec is to extend senlin to support mistral workflow for more complex
and customizable recover actions.

Use Cases
---------

One typical use case is to allow users to introduce their own or existing
mistral workflow as an option of recover action, or special processing before
or after some given recover action.

Proposed change
===============

The proposed change will include three parts:
* driver: to add mistral support into Senlin
* profile: to add workflow support as one of recover action.
* cloud/node_action: to support chain of actions defined as recover behaviour.
* health policy: The health policy spec will be changed to support workflow as
                 the recover action and include parameters needed to execute
                 the workflow. In the health policy, the workflow can also be
                 executed before or after some defined recover action.
                 Below is an example:

  recovery:
    actions:
      - name: REBUILD
      - name: WORKFLOW
        params:
          workflow_name: node_migration
          inputs:
            host: Target_host

* example: to add sample workflow definitions and health policy for Senlin
           users to create an end2end story.

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

None in the first version

Other end user impact
---------------------

None

Performance Impact
------------------

None

Other deployer impact
---------------------

If there is mistral installed inside the same environment and the users want to leverage
the workflow functions, this spec provides support to integrate Senlin and mistral for
the auto-healing purpose.

One thing worth more attention is that the debug and trouble shooting of the user workflow
is not in the scope of this integration. This spec targets to provide a channel for users
to bring into their own trusted workflow into the Senlin auto-healing loop and work together
with all the embedded ations.

Developer impact
----------------

None

Implementation
==============

Assignee(s)
-----------

lxinhui@vmware.com

Work Items
----------

The primary work items in Senlin will focus on adding a new driver for mistral and
implements of do_recover in profile.

Dependencies
============

* Mistral: need to migrate the current APIs into the versioned.

* Openstacksdk: need to support workflow service.


Testing
=======

Unit tests will be provided. End2End test will be provided as examples for Senlin
users.


Documentation Impact
====================

None

References
==========

[1] Mistral patch about API migration:
    https://review.openstack.org/414755
[2] Openstacksdk patch about the support of mistral service:
    https://review.openstack.org/414919

History
=======

None

.. list-table:: Revisions
   :header-rows: 1

   * - Release Name
     - Description
   * - Ocata
     - Introduced
