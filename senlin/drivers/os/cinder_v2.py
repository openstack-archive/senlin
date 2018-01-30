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

from senlin.drivers import base
from senlin.drivers import sdk


class CinderClient(base.DriverBase):
    """Cinder V2 driver."""

    def __init__(self, params):
        super(CinderClient, self).__init__(params)
        self.conn = sdk.create_connection(params)
        self.session = self.conn.session

    @sdk.translate_exception
    def volume_get(self, volume):
        res = self.conn.block_store.get_volume(volume)
        return res

    @sdk.translate_exception
    def volume_create(self, **attr):
        return self.conn.block_store.create_volume(**attr)

    @sdk.translate_exception
    def volume_delete(self, volume, ignore_missing=True):
        self.conn.block_store.delete_volume(volume,
                                            ignore_missing=ignore_missing)

    @sdk.translate_exception
    def snapshot_create(self, **attr):
        return self.conn.block_store.create_snapshot(**attr)

    @sdk.translate_exception
    def snapshot_delete(self, snapshot, ignore_missing=True):
        self.conn.block_store.delete_snapshot(snapshot,
                                              ignore_missing=ignore_missing)

    @sdk.translate_exception
    def snapshot_get(self, snapshot):
        return self.conn.block_store.get_snapshot(snapshot)
