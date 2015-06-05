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


Profiles
========

Concept
-------

A profile is the mould used for creating nodes to be managed by Senlin.
It can be seen as an instance of a :term:`Profile Type`, with a unique ID.
A profile encodes the information needed for node creation into a property
named `spec`. For example, below is a spec for the `os.heat.stack` profile
type::

  # spec for os.heat.stack
  template: my_stack.yaml
  parameters:
    key_name: oskey
  environment:
    - env.yaml

The primary job for a profile's implementation is to translate user provided
JSON data structure into information that can be consumed by a driver. A 
driver will create/delete/update a physical object based on the information
provided.

A profile as a `permission` string which defaults to an empty string at the
moment. In future, it will be used for access authorization checking.


How To Use
----------

(TBC)
