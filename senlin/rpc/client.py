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

'''
Client side of the senlin engine RPC API.
'''

from oslo_config import cfg

from senlin.common import consts
from senlin.common import messaging
from senlin.objects import base as object_base


class EngineClient(object):
    """Client side of the senlin engine rpc API.

    Version History:

      1.0 - Initial version (Mitaka 1.0 release)
      1.1 - Add cluster-collect call.
    """

    def __init__(self):
        serializer = object_base.VersionedObjectSerializer()
        self._client = messaging.get_rpc_client(consts.ENGINE_TOPIC,
                                                cfg.CONF.host,
                                                serializer=serializer)

    @staticmethod
    def make_msg(method, **kwargs):
        return method, kwargs

    def call(self, ctxt, method, req, version=None):
        """The main entry for invoking engine service.

        :param ctxt: The request context object.
        :param method: The name of the method to be invoked.
        :param req: A dict containing a request object.
        :param version: The engine RPC API version requested.
        """
        if version is not None:
            client = self._client.prepare(version=version)
        else:
            client = self._client

        return client.call(ctxt, method, req=req)

    def cast(self, ctxt, msg, version=None):
        method, kwargs = msg
        if version is not None:
            client = self._client.prepare(version=version)
        else:
            client = self._client
        return client.cast(ctxt, method, **kwargs)
