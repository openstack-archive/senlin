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


Development Guide for Profile Types
===================================

Implementation Hints
--------------------

Handling Context
^^^^^^^^^^^^^^^^

In the Profile class implementation, a profile can be stored into DB and then
loaded from DB given an ID. We don't record the context used by a profile. On
the contrary, the context is assigned to a profile when it is (re)intialized.
This enables a profile to be used by different context, which is usually the
context saved into an action. There won't be security problem if we have
recorded the correct context of an action.

Abstract Methods
^^^^^^^^^^^^^^^^

The Profile class provides abstract methods such as `do_create()`,
`do_delete()` and `do_update()` for sub-classes to override.
