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

Policies
========

A policy is a wrapper of a collection of rules that will be checked/enforced
when Senlin performs some operations on the objects it manages. The design
goals of policy support in Senlin are flexibility and customizability. We
strive to make the policies flexible so that we can accommodate diverse types
of policies for various usage scenarios. We also want to make policy type
developement an easier task for developers to introduce new policies and/or
customize existing ones for their needs.


-----------------
Policy Properties
-----------------

A policy object has the following properties:

- ``id``: a string containing the globally unique ID for the object;
- ``name``: a string containing the name of the policy object;
- ``type``: a string containing the name of the policy type;
- ``spec``: a map containing the validated specification for the object;
- ``cooldown``: an integer representing the default policy cooldown in
  seconds.
- ``level``: an integer that specifies default enforcement level of the policy
  when it is checked/enforced;
- ``created_time``: timestamp of the object creation;
- ``updated_time``: timestamp of last update to the object;
- ``deleted_time``: timestamp of the object deletion; a non-empty value
  indicates that the object has been deleted;
- ``data``: a map containing some private data for the policy object;

The policy enforcement levels are defined as an integer. Some predefined
values for the levels are:

- ``MUST`` (50): the policy must be enforced. A violation may render the
  cluster not functional and Senlin has no known way of recovery.
- ``SHOULD`` (40): the policy should be enforced. A violation of a policy at
  this level will render the cluster into an ``ERROR`` status. Manual
  intervention to recover the cluster might be possible.
- ``WOULD`` (30): the policy would be enforced, but a violation of this policy
  may or may not cause negative impact on the cluster. A cluster will be put
  into a ``WARNING`` status so that operators will notice this.
- ``MIGHT`` (20): the policy might be enforced but it is not a requirement.
  A violation of a policy at this level will not cause any negative impact to
  the related cluster. There would be some ``INFO`` or ``DEBUG`` level events
  generated when this policy is enforced.


-----------------
Creating A Policy
-----------------

When the Senlin API receives a request to create a policy object, it first
checks if the JSON body contains a map named ``policy`` that has the ``name``,
``type`` and ``spec`` keys and values associated with them. If any of these
keys are missing, the request will be treated as an invalid one and rejected.

After the preliminary request validation done at the Senlin API layer, Senlin
engine will further check whether the specified policy type does exist and
whether the specified ``spec`` can pass the validation logic in the policy
type implementation. If this phase of validation is successful, a policy
object will be created and saved into the database, then a map containing the
details of the object will be returned to the requester. If any of these
validations fail, an error message will be returned to the requester instead.


----------------
Listing Policies
----------------

Policy objects can be listed using the Senlin API. When querying the policy
objects, a user can specify the following query parameters, individually or
combined:

- ``filters``: a map containing key-value pairs that will be used for matching
  policy records. Records that fail to match this criteria will be filtered
  out. The following strings are valid keys:

  * ``name``: name of policies to list, can be a string or a list of strings;
  * ``type``: type name of policies, can be a string or a list of strings;
  * ``level``: enforcement level of policies, can be an integer of a list of
    integers;
  * ``cooldown``: cooldown value of policies, can be an integer of a list of
    integers;
  * ``created_time``: timestamp when the object was created;
  * ``updated_time``: timestamp when the policy object was last updated;
  * ``deleted_time``: timestamp when the policy object was deleted;

- ``limit``: a number that restricts the maximum number of records to be
  returned from the query. It is useful for displaying the records in pages
  where the page size can be specified as the limit.
- ``marker``: A string that represents the last seen UUID of policies in
  previous queries. This query will only return results appearing after the
  specified UUID. This is useful for displaying records in pages.
- ``sort_dir``: A string to enforce sorting of the results. It can accept
  either ``asc`` or ``desc`` as its value.
- ``sort_keys``: A string or a list of strings where each string gives a
  policy property name used for sorting.
- ``show_deleted``: A boolean indicating whether deleted policies should be
  included in the results. The default is False.

The Senlin API performs some basic checks on the data type and values of the
provided parameters and then passes the request to Senlin engine. When there
are policy objects matching the query criteria, a list of policy objects is
returned to the requester. If there is no matching record, the result will be
an empty list.


----------------
Getting A Policy
----------------

A user can provide one of the UUID, the name or the short ID of policy object
to the Senlin API ``policy_show`` to retrieve the details about a policy.

If a policy object matching the criteria is found, Senlin API returns the
object details in a map; if more than one object is found, Senlin API returns
an error message telling users that there are multiple choices; if no object
is found matching the criteria, a different error message will be returned to
the requester.


-----------------
Updating A Policy
-----------------

After a policy is created, a user can send requests to the Senlin API for
changing some of its properties. To avoid potential state conflicts inside the
Senlin engine, we currently don't allow changes to the ``type`` or the ``spec``
property of a policy. However, changing the ``name``, ``cooldown`` or
``level`` property is permitted.

When validating the requester provided parameters, Senlin API will check if
the values are of valid data types and whether the values fall in allowed
ranges. After this validation, the request is forwarded to Senlin engine for
processing.

Senlin engine will try to find the policy using the specified policy identity
as the UUID, the name or a short ID of the policy object. When no matching
object is found or more than one object is found, an error message is returned
to the user. Otherwise, the engine updates the object property and returns the
object details in a map.


-----------------
Deleting A Policy
-----------------

A user can specify the UUID, the name or the short ID of a policy object when
sending a ``policy_delete`` request to the Senlin API.

Senlin engine will try to find the matching policy object using the specified
identity as the UUID, the name or a short ID of the policy object. When no
matching object is found or more than one object is found, an error message is
returned. Otherwise, the API returns a 204 status to the requester indicating
that the deletion was successful.

To prevent deletion of policies that are still in use by any clusters, the
Senlin engine will try to find if any bindings exist between the specified
policy and a cluster. An error message will be returned to the requester if
such a binding is found.
