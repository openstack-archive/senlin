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

import itertools
import six

from oslo_log import log as logging

from senlin.common.i18n import _LI
from senlin.common.i18n import _LW

LOG = logging.getLogger(__name__)


class PluginInfo(object):
    '''Base mapping of plugin type to implementation.'''

    def __new__(cls, registry, name, plugin, **kwargs):
        '''Create a new PluginInfo of the appropriate class.

        Placeholder for class hierarchy extensibility
        '''
        return super(PluginInfo, cls).__new__(cls)

    def __init__(self, registry, name, plugin):
        self.registry = registry
        self.name = name
        self.plugin = plugin
        self.user_provided = True

    def __eq__(self, other):
        if other is None:
            return False
        return (self.name == other.name and
                self.plugin == other.plugin and
                self.user_provided == other.user_provided)

    def __ne__(self, other):
        return not self.__eq__(other)

    def __lt__(self, other):
        if self.user_provided != other.user_provided:
            # user provided ones must be sorted above system ones.
            return self.user_provided > other.user_provided
        if len(self.name) != len(other.name):
            # more specific (longer) name must be sorted above system ones.
            return len(self.name) > len(other.name)
        return self.name < other.name

    def __gt__(self, other):
        return other.__lt__(self)

    def __str__(self):
        return '[Plugin](User:%s) %s -> %s' % (self.user_provided,
                                               self.name, str(self.plugin))


class Registry(object):
    '''A registry for managing profile or policy classes.'''

    def __init__(self, registry_name, global_registry=None):
        self.registry_name = registry_name
        self._registry = {}
        self.is_global = False if global_registry else True
        self.global_registry = global_registry

    def _register_info(self, name, info):
        '''place the new info in the correct location in the registry.

        :param path: a string of plugin name.
        :param info: reference to a PluginInfo data structure, deregister a
                     PluginInfo if specified as None.
        '''
        registry = self._registry
        if info is None:
            # delete this entry.
            LOG.warning(_LW('Removing %(item)s from registry'), {'item': name})
            registry.pop(name, None)
            return

        if name in registry and isinstance(registry[name], PluginInfo):
            if registry[name] == info:
                return
            details = {
                'name': name,
                'old': str(registry[name].plugin),
                'new': str(info.plugin)
            }
            LOG.warning(_LW('Changing %(name)s from %(old)s to %(new)s'),
                        details)
        else:
            LOG.info(_LI('Registering %(name)s -> %(value)s'), {
                'name': name, 'value': str(info.plugin)})

        info.user_provided = not self.is_global
        registry[name] = info

    def register_plugin(self, name, plugin):
        pi = PluginInfo(self, name, plugin)
        self._register_info(name, pi)

    def load(self, json_snippet):
        for k, v in iter(json_snippet.items()):
            if v is None:
                self._register_info(k, None)
            else:
                self.register_plugin(k, v)

    def iterable_by(self, name):
        plugin = self._registry.get(name)
        if plugin:
            yield plugin

    def get_plugin(self, name):
        giter = []
        if not self.is_global:
            giter = self.global_registry.iterable_by(name)

        matches = itertools.chain(self.iterable_by(name), giter)
        infoes = sorted(matches)
        return infoes[0].plugin if infoes else None

    def as_dict(self):
        return dict((k, v.plugin) for k, v in self._registry.items())

    def get_types(self):
        '''Return a list of valid plugin types.'''
        return [{'name': name} for name in six.iterkeys(self._registry)]
