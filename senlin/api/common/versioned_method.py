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


class VersionedMethod(object):

    def __init__(self, name, min_version, max_version, func):
        """Versioning information for a single method

        Minimums and maximums are inclusive
        :param name: Name of the method
        :param min_version: Minimum acceptable version
        :param max_version: Maximum acceptable_version
        :param func: Method to call

        """
        self.name = name
        self.min_version = min_version
        self.max_version = max_version
        self.func = func

    def __str__(self):
        return ("Version Method %(name)s: min: %(min)s, max: %(max)s" %
                {"name": self.name, "min": self.min_version,
                 "max": self.max_version})
