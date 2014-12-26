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

import json
import six
import yaml

from senlin.common import i18n
from senlin.openstack.common import log as logging

_LE = i18n._LE
LOG = logging.getLogger(__name__)

# Try LibYAML if available
if hasattr(yaml, 'CSafeLoader'):
    YamlLoader = yaml.CSafeLoader
else:
    YamlLoader = yaml.SafeLoader

if hasattr(yaml, 'CSafeDumper'):
    YamlDumper = yaml.CSafeDumper
else:
    YamlDumper = yaml.SafeDumper


def _construct_yaml_str(self, node):
    # Override the default string handling function
    # to always return unicode objects
    return self.construct_scalar(node)

YamlLoader.add_constructor(u'tag:yaml.org,2002:str', _construct_yaml_str)

# Unquoted dates in YAML files get loaded as objects of type datetime.date
# which may cause problems in API layer. Therefore, make unicode string
# out of timestamps until openstack.common.jsonutils can handle dates.
YamlLoader.add_constructor(u'tag:yaml.org,2002:timestamp', _construct_yaml_str)


def simple_parse(in_str):
    try:
        out_dict = json.loads(in_str)
    except ValueError:
        try:
            out_dict = yaml.load(in_str, Loader=YamlLoader)
        except yaml.YAMLError as yea:
            yea = six.text_type(yea)
            msg = _('Error parsing input: %s') % yea
            raise ValueError(msg)
        else:
            if out_dict is None:
                out_dict = {}

    if not isinstance(out_dict, dict):
        msg = _('The input is not a JSON object or YAML mapping.')
        raise ValueError(msg)

    return out_dict


def parse_profile(profile_str):
    '''
    Parse and validate the specified string as a profile.
    '''
    data = simple_parse(profile_str)

    # TODO(Qiming):
    # Construct a profile object based on the type specified

    return data


def parse_policy(policy_str):
    '''
    Parse and validate the specified string as a policy.
    '''
    data = simple_parse(policy_str)

    # TODO(Qiming):
    # Construct a policy object based on the type specified

    return data
