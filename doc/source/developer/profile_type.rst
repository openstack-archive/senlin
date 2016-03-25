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


=============
Profile Types
=============

In Senlin, each node is associated with a physical object created by
instantiating a :doc:`profile <profile>`. Profiles themselves are objects
instantiated from "profile types". In other words, a profile type provides the
specification for creating profiles while a profile can be used to create
multiple homogeneous objects.

Profile type implementations are managed as plugins. Users can use the
built-in profile types directly and they can provide their own implementation
of new profile types. The plan is to have Senlin engine support dynamical
loading of plugins. Currently, this can be done by adding new
``senlin.profiles`` entry in the ``entry_points`` section in the ``setup.cfg``
file followed by a reinstall (i.e. ``pip install``) operation.


The Base Class 'Profile'
~~~~~~~~~~~~~~~~~~~~~~~~

The base class ``Profile`` provides some common logics regarding the following
operations:

- the initialization of the ``spec_data`` based on the ``spec_schema``
  property and the ``spec`` input.
- the initialization of a basic request context using the Senlin service
  credentials.
- the serialization and deserialization of profile object into/from database.
- the validation of data provided through ``spec`` field of the profile;
- the north bound APIs that are provided as class methods, including:

  * ``create_object()``: create an object using logic from the profile type
    implementation, with data from the profile object as inputs;
  * ``delete_object()``: delete an object using the profile type
    implementation;
  * ``update_object()``: update an object by invoking operation provided by a
    profile type implementation, with data from a different profile object as
    inputs;
  * ``get_details()``: retrieve object details into a dictionary by invoking
    the corresponding method provided by a profile type implementation;
  * ``join_cluster()``: a hook API that will be invoked when an object is made
    into a member of a cluster; the purpose is to give the profile type
    implementation a chance to make changes to the object accordingly;
  * ``leave_cluster()``: a hook API that will be invoked when an object is
    removed from its current cluster; the purpose is to give the profile type
    implementation a chance to make changes to the object accordingly;
  * ``recover_object()``: recover an object with operation given by inputs from
    the profile object. By default, ``recreate`` is used if no operation is
    provided to to delete firstly then create the object.


Abstract Methods
----------------

In addition to the above logics, the base class ``Profile`` also defines some
abstract methods for a profile type implementation to implement. When invoked,
these methods by default return ``NotImplemented``, a special value that
indicates the method is not implemented.

- ``do_create(obj)``: an object creation method for a profile type
  implementation to override;
- ``do_delete(obj)``: an object deletion method for a profile type
  implementation to override;
- ``do_update(obj, new_profile)``: an object update method for a profile type
  implementation to override;
- ``do_check(obj)``: a method that is meant to do a health check over the
  provided object;
- ``do_get_details(obj)``: a method that can be overridden so that the caller
  can get a dict that contains properties specific to the object;
- ``do_join(obj)``: a method for implementation to override so that profile
  type specific changes can be made to the object when object joins a cluster.
- ``do_leave(obj)``: a method for implementation to override so that profile
  type specific changes can be made to the object when object leaves its
  cluster.
- ``do_recover(obj)``: an object recover method for a profile type
  implementation to override. Nova server, for example, overrides the recover
  operation by ``REBUILD``.


The ``context`` Property
------------------------

In the ``Profile`` class, there is a special property named ``context``. This
is the data structure containing all necessary information needed when the
profile type implementation wants to authenticate with a cloud platform.
Refer to :doc:`authorization <authorization>`, Senlin makes use of the trust
mechanism provided by the OpenStack Keystone service.

The dictionary in this ``context`` property by default contains the credentials
for the Senlin service account. Using the trust built between the requesting
user and the service account, a profile type implementation can authenticate
itself with the backend Keystone service and then interact with the supporting
service like Nova, Heat etc.

All profile type implementations can include a ``context`` key in their spec,
the default value is an empty dictionary. A user may customize the contents
when creating a profile object by specifying a ``region_name``, for example,
to enable a multi-region cluster deployment. They could even specify a
different ``auth_url`` so that a cluster can be built across OpenStack clouds.


Providing New Profile Types
~~~~~~~~~~~~~~~~~~~~~~~~~~~

When released, Senlin provides some built-in profile types. However,
developing new profile types for Senlin is not a difficult task.


Develop a New Profile Type
--------------------------

The first step is to create a new file containing a subclass of ``Profile``.
Then you will define the spec schema for the new profile which is a python
dictionary named ``spec_schema``, with property names as keys. For each
property, you will specify its value to be an object of one of the schema
types listed below:

- ``String``: A string property.
- ``Boolean``: A boolean property.
- ``Integer``: An integer property.
- ``List``: A property containing a list of values.
- ``Map``: A property containing a map of key-value pairs.

For example:

.. code:: python

  spec_schema = {
    'name': schema.String('name of object'),
    'capacity': schema.Integer('capacity of object', default=10),
    'shared': schema.Boolean('whether object is shared', default=True)
  }

If a profile property is a ``List``, you can further define the type of
elements in the list, which can be a ``String``, a ``Boolean``, an
``Integer`` or a ``Map``. For example:

.. code:: python

  spec_schema = {
    ...
    'addresses': schema.List(
      'address of object on each network',
      schema=schema.String('address on a network')
    ),
    ...
  }

If a profile property is a ``Map``, you can further define the "schema" of that
map, which itself is another Python dictionary containing property
definitions. For example:

.. code:: python

  spec_schema = {
    ...
    'dimension': schema.Map(
      'dimension of object',
      schema={
        'length': schema.Integer('length of object'),
        'width': schema.Integer('width of object')
      }
    )
    ...
  }


By default, a property is not required. If a property has to be provided, you
can specify ``required=True`` in the property type constructor. For example:

.. code:: python

  spec_schema = {
    ...
    'name_length': schema.Integer('length of name', required=True)
    ...
  }

A property can have a default value when no value is specified. If a property
has a default value, you don't need to specify it is required. For example:

.. code:: python

  spec_schema = {
    ...
    'min_size': schema.Integer('minimum size of object', default=0)
    ...
  }

After the properties are defined, you can continue to work on overriding the
abstract methods inherited from the base ``Profile`` type as appropriate.


Registering a New Profile Type
------------------------------

For Senlin to make use of the new profile type you have just developed, you
will register it to Senlin service. Currently, this is done through a manual
process. In future, Senlin will provide dynamical loading support to profile
type plugins.

To register a new profile type, you will add a line to the ``setup.cfg`` file
that can be found at the root directory of Senlin code base. For example:

::

  [entry_points]
  senlin.profiles =
      os.heat.stack = senlin.profiles.os.heat.stack:StackProfile
      os.nova.server = senlin.profiles.os.nova.server:ServerProfile
      my.cool.profile = <path to the profile module>:<profile class name>

Finally, save that file and do a reinstall of the Senlin service, followed by
a restart of the ``senlin-engine`` process.

::

  $ sudo pip install -e .

Now, when you do a :command:`openstack cluster profile type list`, you will
see your profile type listed along with other existing profile types.
