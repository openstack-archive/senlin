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

from oslo_config import cfg
from oslo_utils import timeutils
from senlin.api.common import util
from senlin.api.common import wsgi
from senlin.common import exception
from senlin.objects import service as service_obj

CONF = cfg.CONF


class ServiceController(wsgi.Controller):
    """WSGI controller for Services in Senlin v1 API."""

    REQUEST_SCOPE = 'services'

    @util.policy_enforce
    def index(self, req):
        if not req.context.is_admin:
            raise exception.Forbidden()
        now = timeutils.utcnow(with_timezone=True)
        _services = service_obj.Service.get_all(req.context)
        svcs = []
        for svc in _services:
            updated_at = svc.updated_at
            delta = now - (svc.updated_at or svc.created_at)
            delta_sec = delta.total_seconds()
            alive = abs(delta_sec) <= CONF.service_down_time
            art = (alive and "up") or "down"
            active = 'enabled'
            if svc.disabled:
                active = 'disabled'
            if updated_at:
                updated_at = timeutils.normalize_time(updated_at)
            ret_fields = {'id': svc.id, 'host': svc.host,
                          'binary': svc.binary, 'topic': svc.topic,
                          'disabled_reason': svc.disabled_reason,
                          'status': active, 'state': art,
                          'updated_at': updated_at}
            svcs.append(ret_fields)
        return {'services': svcs}
