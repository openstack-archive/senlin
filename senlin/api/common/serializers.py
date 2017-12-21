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

"""
Utility methods for serializing responses
"""

import datetime

from oslo_config import cfg
from oslo_log import log as logging
from oslo_serialization import jsonutils
from oslo_utils import encodeutils
import six
import webob

from senlin.common import exception
from senlin.common.i18n import _

LOG = logging.getLogger(__name__)


def is_json_content_type(request):

    content_type = request.content_type
    if not content_type or content_type.startswith('text/plain'):
        content_type = 'application/json'

    if (content_type in ('JSON', 'application/json') and
            request.body.startswith(b'{')):
        return True
    return False


class JSONRequestDeserializer(object):

    def has_body(self, request):
        """Return whether a Webob.Request object will possess an entity body.

        :param request: A Webob.Request object
        """
        if request is None or request.content_length is None:
            return False

        if request.content_length > 0 and is_json_content_type(request):
            return True

        return False

    def from_json(self, datastring):
        try:
            if len(datastring) > cfg.CONF.senlin_api.max_json_body_size:
                msg = _('JSON body size (%(len)s bytes) exceeds maximum '
                        'allowed size (%(limit)s bytes).'
                        ) % {'len': len(datastring),
                             'limit': cfg.CONF.senlin_api.max_json_body_size}
                raise exception.RequestLimitExceeded(message=msg)
            return jsonutils.loads(datastring)
        except ValueError as ex:
            raise webob.exc.HTTPBadRequest(six.text_type(ex))

    def default(self, request):
        if self.has_body(request):
            return {'body': self.from_json(request.body)}
        else:
            return {}


class JSONResponseSerializer(object):

    def to_json(self, data):
        def sanitizer(obj):
            if isinstance(obj, datetime.datetime):
                return obj.isoformat()
            return six.text_type(obj)

        response = jsonutils.dumps(data, default=sanitizer, sort_keys=True)
        LOG.debug("JSON response : %s", response)
        return response

    def default(self, response, result):
        response.content_type = 'application/json'
        response.body = encodeutils.safe_encode(self.to_json(result))
