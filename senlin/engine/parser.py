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

import six
import yaml

from senlin.common import i18n
from senlin.openstack.common import log as logging

_LE = i18n._LE
LOG = logging.getLogger(__name__)


# Try LibYAML if available
try:
    Loader = yaml.CLoader
    Dumper = yaml.CDumper
except ImportError as err:
    Loader = yaml.Loader
    Dumper = yaml.Dumper


def parse_profile(profile):
    '''
    Parse and validate the specified string as a profile.
    '''
    if not isinstance(profile, six.string_types):
        # TODO(Qiming): Throw exception
        return None

    data = {}
    try:
        data = yaml.load(profile, Loader=Loader)
    except Exception as ex:
        # TODO(Qiming): Throw exception
        LOG.error(_LE('Failed parsing given data as YAML: %s'),
                  six.text_type(ex))
        return None

    # TODO(Qiming): Construct a profile object based on the type specified

    return data


def parse_policy(policy):
    '''
    Parse and validate the specified string as a policy.
    '''
    if not isinstance(policy, six.string_types):
        # TODO(Qiming): Throw exception
        return None

    data = {}
    try:
        data = yaml.load(policy, Loader=Loader)
    except Exception as ex:
        # TODO(Qiming): Throw exception
        LOG.error(_LE('Failed parsing given data as YAML: %s'),
                  six.text_type(ex))
        return None

    # TODO(Qiming): Construct a policy object based on the type specified

    return data


def parse_action(action):
    '''
    Parse and validate the specified string as a action.
    '''
    if not isinstance(action, six.string_types):
        # TODO(Qiming): Throw exception
        return None

    data = {}
    try:
        data = yaml.load(action, Loader=Loader)
    except Exception as ex:
        # TODO(Qiming): Throw exception
        LOG.error(_LE('Failed parsing given data as YAML: %s'),
                  six.text_type(ex))
        return None

    # TODO(Qiming): Construct a action object based on the type specified

    return data
