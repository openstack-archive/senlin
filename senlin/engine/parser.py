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

import os

from oslo_serialization import jsonutils
import six
from six.moves import urllib
import yaml

from senlin.common.i18n import _


# Try LibYAML if available
if hasattr(yaml, 'CSafeLoader'):
    Loader = yaml.CSafeLoader
else:
    Loader = yaml.SafeLoader

if hasattr(yaml, 'CSafeDumper'):
    Dumper = yaml.CSafeDumper
else:
    Dumper = yaml.SafeDumper


class YamlLoader(Loader):
    def normalise_file_path_to_url(self, path):
        if urllib.parse.urlparse(path).scheme:
            return path
        path = os.path.abspath(path)
        return urllib.parse.urljoin('file:',
                                    urllib.request.pathname2url(path))

    def include(self, node):
        try:
            url = self.normalise_file_path_to_url(self.construct_scalar(node))
            tmpl = urllib.request.urlopen(url).read()
            return yaml.safe_load(tmpl)
        except urllib.error.URLError as ex:
            raise IOError('Failed retrieving file %s: %s' %
                          (url, six.text_type(ex)))

    def process_unicode(self, node):
        # Override the default string handling function to always return
        # unicode objects
        return self.construct_scalar(node)


YamlLoader.add_constructor('!include', YamlLoader.include)
YamlLoader.add_constructor(u'tag:yaml.org,2002:str',
                           YamlLoader.process_unicode)
YamlLoader.add_constructor(u'tag:yaml.org,2002:timestamp',
                           YamlLoader.process_unicode)


def simple_parse(in_str):
    try:
        out_dict = jsonutils.loads(in_str)
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
