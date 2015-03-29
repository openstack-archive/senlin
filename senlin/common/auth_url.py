#
# Copyright 2013 OpenStack Foundation
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from oslo_config import cfg
from oslo_utils import importutils

from senlin.common import wsgi


class AuthUrlFilter(wsgi.Middleware):

    def __init__(self, app, conf):
        super(AuthUrlFilter, self).__init__(app)
        self.conf = conf

        if 'auth_uri' in self.conf:
            self.auth_url = self.conf['auth_uri']
        else:
            # Import auth_token to have keystone_authtoken settings setup.
            auth_token_module = 'keystonemiddleware.auth_token'
            importutils.import_module(auth_token_module)
            self.auth_url = cfg.CONF.keystone_authtoken.auth_uri

    def process_request(self, req):
        req.headers['X-Auth-Url'] = self.auth_url
        return None


def filter_factory(global_conf, **local_conf):
    conf = global_conf.copy()
    conf.update(local_conf)

    def auth_url_filter(app):
        return AuthUrlFilter(app, conf)
    return auth_url_filter
