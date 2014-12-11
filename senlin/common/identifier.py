#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

import collections
import re

from oslo.utils import encodeutils
from six.moves.urllib import parse as urlparse

from senlin.common.i18n import _


class SenlinIdentifier(collections.Mapping):

    FIELDS = (
        TENANT, CLUSTER_NAME, CLUSTER_ID, PATH
    ) = (
        'tenant', 'cluster_name', 'cluster_id', 'path'
    )
    path_re = re.compile(r'clusters/([^/]+)/([^/]+)(.*)')

    def __init__(self, tenant, cluster_name, cluster_id, path=''):
        """Initialise a SenlinIdentifier.

        Identifier is initialized from a Tenant ID, Cluster name, Cluster ID
        and optional path. If a path is supplied and it does not begin with
        "/", a "/" will be prepended.
        """
        if path and not path.startswith('/'):
            path = '/' + path

        if '/' in cluster_name:
            raise ValueError(_('Cluster name may not contain "/"'))

        self.identity = {
            self.TENANT: tenant,
            self.CLUSTER_NAME: cluster_name,
            self.CLUSTER_ID: str(cluster_id),
            self.PATH: path,
        }

    @classmethod
    def from_arn(cls, arn):
        """Generate a new SenlinIdentifier by parsing the supplied ARN."""
        fields = arn.split(':')
        if len(fields) < 6 or fields[0].lower() != 'arn':
            raise ValueError(_('"%s" is not a valid ARN') % arn)

        id_fragment = ':'.join(fields[5:])
        path = cls.path_re.match(id_fragment)

        if fields[1] != 'openstack' or fields[2] != 'senlin' or not path:
            raise ValueError(_('"%s" is not a valid Senlin ARN') % arn)

        return cls(urlparse.unquote(fields[4]),
                   urlparse.unquote(path.group(1)),
                   urlparse.unquote(path.group(2)),
                   urlparse.unquote(path.group(3)))

    @classmethod
    def from_arn_url(cls, url):
        """Generate a new SenlinIdentifier by parsing the supplied URL.

        The URL is expected to contain a valid arn as part of the path.
        """
        # Sanity check the URL
        urlp = urlparse.urlparse(url)
        if (urlp.scheme not in ('http', 'https') or
                not urlp.netloc or not urlp.path):
            raise ValueError(_('"%s" is not a valid URL') % url)

        # Remove any query-string and extract the ARN
        arn_url_prefix = '/arn%3Aopenstack%3Asenlin%3A%3A'
        match = re.search(arn_url_prefix, urlp.path, re.IGNORECASE)
        if match is None:
            raise ValueError(_('"%s" is not a valid ARN URL') % url)
        # the +1 is to skip the leading /
        url_arn = urlp.path[match.start() + 1:]
        arn = urlparse.unquote(url_arn)
        return cls.from_arn(arn)

    def arn(self):
        """Return as an ARN.

        Returned in the form:
            arn:openstack:senlin::<tenant>:clusters/<cluster_name>/<cluster_id><path>
        """
        return 'arn:openstack:senlin::%s:%s' % (urlparse.quote(self.tenant, ''),
                                              self._tenant_path())

    def arn_url_path(self):
        """Return an ARN quoted correctly for use in a URL."""
        return '/' + urlparse.quote(self.arn(), '')

    def url_path(self):
        """Return a URL-encoded path segment of a URL.

        Returned in the form:
            <tenant>/clusters/<cluster_name>/<cluster_id><path>
        """
        return '/'.join((urlparse.quote(self.tenant, ''), self._tenant_path()))

    def _tenant_path(self):
        """URL-encoded path segment of a URL within a particular tenant.

        Returned in the form:
            clusters/<cluster_name>/<cluster_id><path>
        """
        return 'clusters/%s%s' % (self.cluster_path(),
                                urlparse.quote(encodeutils.safe_encode(
                                    self.path)))

    def cluster_path(self):
        """Return a URL-encoded path segment of a URL without a tenant.

        Returned in the form:
            <cluster_name>/<cluster_id>
        """
        return '%s/%s' % (urlparse.quote(self.cluster_name, ''),
                          urlparse.quote(self.cluster_id, ''))

    def _path_components(self):
        """Return a list of the path components."""
        return self.path.lstrip('/').split('/')

    def __getattr__(self, attr):
        """Return a component of the identity when accessed as an attribute."""
        if attr not in self.FIELDS:
            raise AttributeError(_('Unknown attribute "%s"') % attr)

        return self.identity[attr]

    def __getitem__(self, key):
        """Return one of the components of the identity."""
        if key not in self.FIELDS:
            raise KeyError(_('Unknown attribute "%s"') % key)

        return self.identity[key]

    def __len__(self):
        """Return the number of components in an identity."""
        return len(self.FIELDS)

    def __contains__(self, key):
        return key in self.FIELDS

    def __iter__(self):
        return iter(self.FIELDS)

    def __repr__(self):
        return repr(dict(self))
