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

from oslo_middleware import ssl

from senlin.api.middleware import context
from senlin.api.middleware import fault
from senlin.api.middleware import trust
from senlin.api.middleware import version_negotiation as vn
from senlin.api.middleware import webhook
from senlin.api.openstack import versions


def version_negotiation_filter(app, conf, **local_conf):
    return vn.VersionNegotiationFilter(versions.Controller, app,
                                       conf, **local_conf)


def faultwrap_filter(app, conf, **local_conf):
    return fault.FaultWrapper(app)


def sslmiddleware_filter(app, conf, **local_conf):
    return ssl.SSLMiddleware(app)


def contextmiddleware_filter(app, conf, **local_conf):
    return context.ContextMiddleware(app)


def trustmiddleware_filter(app, conf, **local_conf):
    return trust.TrustMiddleware(app)


def webhookmiddleware_filter(app, conf, **local_conf):
    return webhook.WebhookMiddleware(app)
