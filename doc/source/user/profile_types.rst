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

.. _ref-profile-types:

=============
Profile Types
=============

Concept
~~~~~~~

A :term:`Profile Type` can be treated as the meta-type of a :term:`Profile`
object. A registry of profile types is built in memory when Senlin engine
(:program:`senlin-engine`) is started. In future, Senlin will allow users to
provide additional profile type implementations as plug-ins to be loaded
dynamically.

A profile type implementation dictates which fields are required. When a
profile is created by referencing this profile type, the fields are assigned
with concrete values. For example, a profile type can be ``os.heat.stack``
that conceptually specifies the properties required:

::

  context: Map
  template: Map
  parameters: Map
  files: Map
  timeout: Integer
  disable_rollback: Boolean
  environment: Map

A profile of type ``os.heat.stack`` may look like:

::

  # a spec for os.heat.stack
  type: os.heat.stack
  version: 1.0
  properties:
    context:
      region_name: RegionOne
    template:
      heat_template_version: 2014-10-16
      parameters:
        length: Integer
      resources:
        rand:
          type: OS::Heat::RandomString
          properties:
            len: {get_param: length}
      outputs:
        rand_val:
          value: {get_attr: [rand, value]}
    parameters:
      length: 32
    files: {}
    timeout: 60
    disable_rollback: True
    environment: {}


Listing Profile Types
~~~~~~~~~~~~~~~~~~~~~

Senlin server comes with some built-in profile types. You can check the list
of profile types using the following command::

  $ openstack cluster profile type list
  +--------------------+
  | name               |
  +--------------------+
  | os.heat.stack-1.0  |
  | os.nova.server-1.0 |
  +--------------------+

The output is a list of profile types supported by the Senlin server.


Showing Profile Details
~~~~~~~~~~~~~~~~~~~~~~~

Each :term:`Profile Type` has a schema for its *spec* (i.e. specification)
that describes the names and the types of properties that can be accepted. To
show the schema of a specific profile type along with other properties, you
can use the following command::

  $ openstack cluster profile type show os.heat.stack
  name: os.heat.stack
  schema:
    context:
      default: {}
      description: A dictionary for specifying the customized context for
        stack operations
      readonly: false
      required: false
      type: Map
    disable_rollback:
      default: true
      description: A boolean specifying whether a stack operation can be
        rolled back.
      readonly: false
      required: false
      type: Boolean
    <... omitted ...>
    timeout:
      description: A integer that specifies the number of minutes that a
        stack operation times out.
      readonly: false
      required: false
      type: Integer

Here, each property has the following attributes:

- ``default``: the default value for a property when not explicitly specified;
- ``description``: a textual description of the use of a property;
- ``readonly``: a boolean indicating whether a property is read only for
  reasons like being part of the outputs of an object;
- ``required``: whether the property must be specified. Such kind of a
  property usually doesn't have a ``default`` value.
- ``type``: one of ``String``, ``Integer``, ``Boolean``, ``Map`` or ``List``.

The default output from the :command:`openstack cluster profile type show`
command is in YAML format. You can choose to show the spec schema in JSON
format by specifying the :option:`-f json` option as exemplified below::

  $ openstack cluster profile type show -f json os.heat.stack
  {
    "name": "os.heat.stack",
    "schema": {
      "files": {
        "default": {},
        "readonly": false,
        "required": false,
        "type": "Map",
        "description": "Contents of files referenced by the template, if any."
      },
      <... omitted ...>
      "context": {
        "default": {},
        "readonly": false,
        "required": false,
        "type": "Map",
        "description": "A dictionary for specifying the customized context for stack operations"
      }
    },
  }


See Also
~~~~~~~~

Below is a list of links to the documents related to profile types:

* :doc:`Managing Profile Objects <profiles>`
* :doc:`Creating and Managing Clusters <clusters>`
* :doc:`Creating and Managing Nodes <nodes>`
* :doc:`Managing Cluster Membership <membership>`
* :doc:`Browsing Events <events>`
