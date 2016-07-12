..
  Licensed under the Apache License, Version 2.0 (the "License"); you may
  not use this file except in compliance with the License. You may obtain
  a copy of the License at

          http://www.apache.org/licenses/LICENSE-2.0

  Unless required by applicable law or agreed to in writing, software
  distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
  WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
  License for the specific language governing permissions and limitations
  under the License.

.. _tutorial-policies:

=====================
Working with Policies
=====================

Creating a Policy
~~~~~~~~~~~~~~~~~

A policy contains the set of rules that are checked/enforced before or
after certain cluster operations are performed. The detailed specification
of a specific policy type is provided as the ``spec`` of a policy object
when it is created. The following is a sample ``spec`` for a deletion policy:

.. literalinclude:: ../../../examples/policies/deletion_policy.yaml
   :language: yaml

.. note::
  The above source file can be found in senlin source tree at
  ``/examples/policies/deletion_policy.yaml``.

To create a policy object using this specification (``spec`` for short):

.. code-block:: console

  $ cd $SENLIN_ROOT/examples/policies
  $ senlin policy-create -s deletion_policy.yaml dp01

To verify the policy creation, you can do:

.. code-block:: console

  $ senlin policy-list
  $ senlin policy-show dp01

Attaching a Policy
~~~~~~~~~~~~~~~~~~

The enforce a policy on a cluster, attach a policy to it:

.. code-block:: console

  $ senlin cluster-policy-attach -p dp01 mycluster

To verify the policy attach operation, do the following:

.. code-block:: console

  $ senlin cluster-policy-list mycluster
  $ senlin cluster-policy-show -p dp01 mycluster

Verifying a Policy
~~~~~~~~~~~~~~~~~~

To verify the deletion policy attached to the cluster ``mycluster``, you
can try expanding the cluster, followed by shrinking it:

.. code-block:: console

  $ senlin cluster-node-list mycluster
  $ senlin cluster-scale-out mycluster
  $ senlin cluster-node-list mycluster
  $ senlin cluster-scale-in mycluster
  $ senlin cluster-node-list mycluster

After the scale-in operation is completed, you will find that the oldest
node from the cluster is removed. If you want to remove the youngest node
instead, you can create a different deletion policy with a different
specification.

For more details about policy types and policy management, check the
:doc:`Policy Types <../user/policy_types>` section and the
:doc:`Policies <../user/policies>` section in the
:doc:`User Reference <../user/index>` documentation respectively.
You may also want to check the 
:doc:`Cluster-Policy Bindings <../user/bindings>` section in the
:doc:`User Reference <../user/index>` for more details on managing
the cluster-policy relationship.
