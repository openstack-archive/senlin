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

from senlin.common.i18n import _LI
from senlin.common.i18n import _LW
from senlin.engine import environment
from senlin.openstack.common import log

LOG = log.getLogger(__name__)


class PluginInfo(object):
    '''
    Base mapping of plugin type to implementation.
    '''
    def __new__(cls, registry, name, plugin, **kwargs):
        '''
        Create a new PluginInfo of the appropriate class.
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
            return self.user_provided > other.user_provided_
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
    '''
    A registry for managing profile or policy classes.
    '''

    def __init__(self, registry_name, is_global):
        self._registry = {registry_name: {}}
        self.is_global = is_global
        global_registry = environment.global_env().registry
        self.global_registry = None if is_global else global_registry

    def _register_info(self, path, info):
        '''
        place the new info in the correct location in the registry.

        :param path: a list of keys ['profiles', 'my_stack', 'os.heat.stack'],
                     or ['policies', 'my_policy', 'ScalingPolicy']
        :param info: reference to a PluginInfo data structure, deregister a
                     PluginInfo if specified as None.
        '''
        descriptive_path = '/'.join(path)
        name = path[-1]
        # create the structure if needed
        registry = self._registry
        for key in path[:-1]:
            if key not in registry:
                registry[key] = {}
            registry = registry[key]

        if info is None:
            # delete this entry.
            LOG.warn(_LW('Removing %(item)s from %(path)s'), {
                'item': name, 'path': descriptive_path})
            registry.pop(name, None)
            return

        if name in registry and isinstance(registry[name], PluginInfo):
            if registry[name] == info:
                return
            details = {
                'path': descriptive_path,
                'old': str(registry[name].value),
                'new': str(info.value)
            }
            LOG.warn(_LW('Changing %(path)s from %(old)s to %(new)s'), details)
        else:
            LOG.info(_LI('Registering %(path)s -> %(value)s'), {
                'path': descriptive_path, 'value': str(info.value)})

        info.user_provided = self.user_env
        registry[name] = info

    def register_plugin(self, name, plugin):
        pi = PluginInfo(self, [name], plugin)
        self._register_info([name], pi)

    def _load_registry(self, path, registry):
        for k, v in iter(registry.items()):
            path = path + [k]
            if v is None:
                self._register_info(path, None)
            elif isinstance(v, dict):
                self._load_registry(path, v)
            else:
                info = PluginInfo(self, path, v)
                self._register_info(path, info)

    def load(self, json_snippet):
        self._load_registry([], json_snippet)

    def iterable_by(self, name):
        plugin = self._registry.get(name)
        if plugin:
            yield plugin

    def get_plugin(self, name):
        giter = []
        if self.user_env:
            giter = self.global_registry.iterable_by(name)

        matches = itertools.chain(self.iterable_by(name), giter)
        info = sorted(matches)
        return info.plugin if info else None

    def as_dict(self):
        """Return profiles in a dict format."""
        def _as_dict(level):
            tmp = {}
            for k, v in iter(level.items()):
                if isinstance(v, dict):
                    tmp[k] = _as_dict(v)
                elif v.user_provided:
                    tmp[k] = v.value
            return tmp

        return _as_dict(self._registry)

    def get_types(self):
        '''Return a list of valid profile types.'''
        return [name for name in six.iteritems(self._registry)]
