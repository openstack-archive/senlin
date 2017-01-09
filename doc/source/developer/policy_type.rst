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


============
Policy Types
============

A :doc:`policy <policy>` policy is a set of rules that are checked
and enforced. The checking can be done before or after an action's execution
or both. Policies are of different policy types, each of which is designed to
make sure that a cluster's behavior follows certain patterns or complies with
certain restrictions.

When released, Senlin comes with some built-in policy types to meet the
requirements found in some typical use cases. However, the distributors or the
users can always augment their collection of policy types by implementing
their own ones.

Policy type implementations are managed as Senlin plugins. The plan is to have
Senlin engine support dynamical loading of plugins from user specified modules
and classes. Currently, this can be achieved by adding new ``senlin.policies``
entries in the ``entry_points`` section in the ``setup.cfg`` file, followed by
a reinstall of the Senlin service, i.e. ``sudo pip install`` command.


The Base Class ``Policy``
~~~~~~~~~~~~~~~~~~~~~~~~~

The base class ``Policy`` provides some common logics regarding the following
operations:

- The initialization of the ``spec_data`` property, based on the
  ``spec_schema`` definition and the ``spec`` input.
- The serialization and deserialization of a policy object into/from database.
- The serialization and deserialization of a policy object into/from a dict.
- The default validation operation for the ``spec_data`` property.
- Default implementations for the following methods which are to be overridden
  by a policy type implementation:

  * ``attach(cluster_id, action)``: a method that will be invoked when a policy
    object of this type is attached to a cluster.
  * ``detach(cluster_id, action)``: a method that will be invoked when a policy
    object of this type is detached from a cluster.
  * ``pre_op(cluster_id, action)``: a method that will be invoked before an
    action is executed;
  * ``post_op(cluster_id, action)``: a method that will be invoked after an
    action is executed.


The ``VERSIONS`` Property
-------------------------

Each policy type class has a ``VERSIONS`` class property that documents the
changes to the policy type. This information is returned when users request
to list all policy types supported.

The ``VERSIONS`` property is a dict with version numbers as keys. For each
specific version, the value is list of support status changes made to the
policy type. Each change record contains a ``status`` key whose value is one
of ``EXPERIMENTAL``, ``SUPPORTED``, ``DEPRECATED`` or ``UNSUPPORTED``, and a
``since`` key whose value is of format ``yyyy.mm`` where ``yyyy`` and ``mm``
are the year and month of the release that bears the change to the support
status. For example, the following record indicates that the specific policy 
type was introduced in April, 2016 (i.e. version 1.0 release of Senlin) as
an experimental feature; later, in October, 2016 (i.e. version 2.0 release of
Senlin) it has graduated into a mature feature supported by the developer
team.

.. code:: python

  VERSIONS = {
    '1.0': [
        {
            "status": "EXPERIMENTAL",
            "since": "2016.04"
        },
        {
            "status": "SUPPORTED",
            "since": "2016.10"
        }
    ]
  }


Providing New Policy Types
~~~~~~~~~~~~~~~~~~~~~~~~~~

Adding new policy type implementations is an easy task with only a few steps
to follow.


Develop A New Policy Type
-------------------------

The first step for adding a new policy type is to create a new file containing
a subclass of ``Policy``. Then you will define the spec schema for the new
policy type in a Python dictionary named ``spec_schema``.


Defining Spec Schema
--------------------

Each key in this dictionary represents a property name; the value of it is an
object of one of the schema types listed below:

- ``String``: A string property.
- ``Boolean``: A boolean property.
- ``Integer``: An integer property.
- ``List``: A property containing a list of values.
- ``Map``: A property containing a map of key-value pairs.

For example:

.. code:: python

  spec_schema = {
    'destroy_after_delete': schema.Boolean(
      'Boolean indicating whether object will be destroyed after deletion.',
      default=True,
    ),
    ...
  }


If a property value will be a list, you can further define the type of items
the list can accept. For example:

.. code:: python

  spec_schema = {
    'criteria': schema.List(
      'Criteria for object selection that will be evaluated in order.',
      schema=schema.String('Name of a criterion'),
    ),
    ...
  }

If a property value will be a map of key-value pairs, you can define the
schema of the map, which is another Python dictionary containing definitions
of properties. For example:

.. code:: python

  spec_schema = {
    'strategy': schema.Map(
      'Strategy for dealing with servers with different states.',
      schema={
        'inactive': 'boot',
        'deleted': 'create',
        'suspended': 'resume',
      },
    ),
    ...
  }

When creating a schema type object, you can specify the following keyword
arguments to gain a better control of the property:

- ``default``: a default value of the expected data type;
- ``required``: a boolean value indicating whether a missing of the property
  is acceptable when validating the policy spec;
- ``constraints``: a list of ``Constraint`` objects each of which defines a
  constraint to be checked. Senlin currently only support ``AllowedValues``
  constraint.


Applicable Profile Types
------------------------

Not all policy types can be used on all profile types. For example, a policy
about load-balancing is only meaningful for objects that can handle workloads,
or more specifically, objects that expose service access point on an IP port.

You can define what are the profile types your new policy type can handle by
specifying the ``PROFILE_TYPE`` property of your policy type class. The value
of ``PROFILE_TYPE`` is a list of profile type names. If a policy type is
designed to handle all profile types, you can specify a single entry ``ANY``
as the value. See :doc:`profile types <profile_type>` for profile type related
operations.


Policy Targets
--------------

A policy type is usually defined to handle certain operations. The rules
embedded in the implementation may need to be checked before the execution of
an :doc:`action <action>` or they may need to be enforced after the execution
of the action. When an action is about to be executed or an action has
finished execution, the Senlin engine will check if any policy objects
attached to a cluster is interested in the action. If the answer is yes, the
engine will invoke the ``pre_op`` function or the ``post_op`` function
respectively, thus giving the policy object a chance to adjust the action's
behavior.

You can define a ``TARGET`` property for the policy type implementation to
indicate the actions your policy type want to subscribe to. The ``TARGET``
property is a list of tuple (``WHEN``, ``ACTION``). For example, the following
property definition indicates that the policy type is interested in the action
``CLUSTER_SCALE_IN`` and ``CLUSTER_DEL_NODES``. The policy type wants itself
be consulted *before* these actions are performed.

.. code:: python

  class MyPolicyType(Policy):
    ...
    TARGET = [
      (BEFORE, consts.CLUSTER_SCALE_IN),
      (BEFORE, consts.CLUSTER_DEL_NODES),
    ]
    ...

When the corresponding actions are about to be executed, the ``pre_op``
function of this policy object will be invoked.


Passing Data Between Policies
-----------------------------

Each policy type may decide to send some data as additional inputs or
constraints for the action to consume. This is done by modifying the ``data``
property of an ``Action`` object (see :doc:`action <action>`).

A policy type may want to check if there are other policy objects leaving some
policy decisions in the ``data`` property of an action object.

Senlin allows for more than one policy to be attached to the same cluster.
Each policy, when enabled, is supposed to check a specific subset of cluster
actions. In other words, different policies may get checked before/after the
engine executes a specific cluster action. This design is effectively forming
a chain of policies for checking. The decisions (outcomes) from one policy
sometimes impact other policies that are checked later.

To help other developers to understand how a specific policy type is designed
to work in concert with others, we require all policy type implementations
shipped with Senlin accompanied by a documentation about:

* the ``action data`` items the policy type will consume, including how these
  data will impact the policy decisions.
* the ``action.data`` items the policy type will produce, thus consumable by
  any policies downstream.

For built-in policy types, the protocol is documented below:

.. toctree::
   :maxdepth: 1

   policies/affinity_v1
   policies/deletion_v1
   policies/load_balance_v1
   policies/region_v1
   policies/scaling_v1
   policies/zone_v1


Registering The New Policy Type
-------------------------------

For Senlin service to be aware of and thus to make use of the new policy type
you have just developed, you will register it to the Senlin service.
Currently, this is done through a manual process shown below. In future,
Senlin will provide dynamical loading support to policy type plugins.

To register a new plugin type, you will add a line to the ``setup.cfg`` file
that can be found at the root directory of Senlin code base. For example:

::

  [entry_points]
  senlin.policies =
      ScalingPolicy = senlin.policies.scaling_policy:ScalingPolicy
      MyCoolPolicy = <path to the policy module>:<policy class name>

Finally, save that file and do a reinstall of the Senlin service, followed
by a restart of the ``senlin-engine`` process.

::

  $ sudo pip install -e .


Now, when you do a :command:`openstack cluster policy type list`, you will see
your policy type listed along with other existing policy types.
