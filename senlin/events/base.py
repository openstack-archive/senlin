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

from oslo_utils import reflection


class EventBackend(object):

    @classmethod
    def _check_entity(cls, e):
        e_type = reflection.get_class_name(e, fully_qualified=False)
        return e_type.upper()

    @classmethod
    def _get_action_name(cls, action):
        """Get action name by inference.

        :param action: An action object.
        :returns: A string containing the inferred action name.
        """
        name = action.action.split('_', 1)
        if len(name) == 1:
            return name[0].lower()

        name = name[1].lower()
        if name == "operation":
            name = action.inputs.get("operation", name)
        return name

    @classmethod
    def dump(cls, level, action, **kwargs):
        """A method for sub-class to override.

        :param level: An integer as defined by python logging module.
        :param action: The action that triggered this dump.
        :param dict kwargs: Additional parameters such as ``phase``,
                            ``timestamp`` or ``extra``.
        :returns: None
        """
        raise NotImplementedError
