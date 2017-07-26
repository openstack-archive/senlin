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

=======
Reviews
=======

About Global Requirements
~~~~~~~~~~~~~~~~~~~~~~~~~

When reviewing patches proposed by `OpenStack Proposal Bot`, we often quick
approve them if the patch successfully passed the gate jobs. However, we
should realize that these tests may contain some improvements or radical
changes to the packages senlin imports.

A more appropriate workflow should be checking the version changes proposed
in such patches and examine the git log from each particular package. If there
are significant changes that may simplify senlin code base, we should propose
at least a TODO item to write down the needed changes to senlin so we adapt
senlin code to the new package.


About Trivial Changes
~~~~~~~~~~~~~~~~~~~~~

There are always disagreements across the community about trivial changes such
as grammar fixes, mis-spelling changes in comments etc. These changes are in
general okay to get merged, BUT our core reviewers should be aware that these
behavior are not encouraged. When we notice such behavior from some
developers, it is our responsibility to guide these developers to submit more
useful patches. We are not supposed to reject such changes as a punishment or
something like that. We are about building a great software with a great team.
