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


Profile Types
=============

Basic Concept
-------------

A Profile Type can be treated as a meta-type of a profile. A registry of
profile typess is built in memory when Senlin engine is started. In future,
Senlin will allow user to provide additional profile type implementations
as plug-ins.

A profile type only dictates which fields are required. When a profile is
created out of such a profile type, the fields are assigned with concrete
values. For example, a profile type can be `aws.autoscaling.launchconfig`
that conceptually specifies the properties required::

  properties:
    UserData: string
    ImageId: string
    InstanceId: string
    KeyName: string
    InstanceType: string

A profile of type `aws.autoscaling.launchconfig` may look like::

  # spec for aws.autoscaling.launchconfig
  UserData: |
    #!/bin/sh
    echo 'Script running'
  ImageId: 23
  KeyName: oskey
  InstanceType: m1.small


How To Use
----------

(TBC)
