# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

"""Senlin common internal object model"""

from oslo_versionedobjects import base


class SenlinObject(base.VersionedObject):
    """Base class for senlin objects.

    This is the base class for all objects that can be remoted or instantiated
    via RPC. Simply defining a sub-class of this class would make it remotely
    instantiatable. Objects should implement the "get" class method and the
    "save" object method.
    """

    OBJ_PROJECT_NAMESPACE = 'senlin'
    VERSION = '1.0'
