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
    '''Fake Cinder V2 driver for test.'''
    def __init__(self, ctx):
        self.fake_volume_create = {
            "id": "3095aefc-09fb-4bc7-b1f0-f21a304e864c",
            "size": 2,
            "links": [
                {
                    "href": " ",
                    "rel": "self"
                }
            ]
        }

        self.fake_volume_get = {
            "status": "available",
            "attachments": [],
            "links": [
                {
                    "href": " ",
                    "rel": "self"
                },
                {
                    "href": " ",
                    "rel": "bookmark"
                }
            ],
            "availability_zone": "nova",
            "bootable": "false",
            "os-vol-host-attr:host": "ip-10-168-107-25",
            "source_volid": "",
            "snapshot_id": "",
            "id": "5aa119a8-d25b-45a7-8d1b-88e127885635",
            "description": "Super volume.",
            "name": "vol-002",
            "created_at": "2013-02-25T02:40:21.000000",
            "volume_type": "None",
            "os-vol-tenant-attr:tenant_id": "0c2eba2c5af04d3f9e9d0d410b371fde",
            "size": 1,
            "os-volume-replication:driver_data": "",
            "os-volume-replication:extended_status": "",
            "metadata": {
                "contents": "not junk"
            }
        }

        self.fake_snapshot_create = {
            "name": "snap-001",
            "description": "Daily backup",
            "volume_id": "5aa119a8-d25b-45a7-8d1b-88e127885635",
            "force": True
        }

        self.fake_snapshot_get = {
            "status": "available",
            "os-extended-snapshot-attributes:progress": "100%",
            "description": "Daily backup",
            "created_at": "2013-02-25T04:13:17.000000",
            "metadata": {},
            "volume_id": "5aa119a8-d25b-45a7-8d1b-88e127885635",
            "os-extended-snapshot-attributes:project_id":
                "0c2eba2c5af04d3f9e9d0d410b371fde",
            "size": 1,
            "id": "2bb856e1-b3d8-4432-a858-09e4ce939389",
            "name": "snap-001"
        }

    def volume_create(self, **params):
        return sdk.FakeResourceObject(self.fake_volume_create)

    def volume_get(self, volume_id):
        sdk.FakeResourceObject(self.fake_volume_get)

    def volume_delete(self, volume_id, ignore_missing=True):
        return

    def snapshot_create(self, **params):
        return sdk.FakeResourceObject(self.fake_snapshot_create)

    def snapshot_get(self, volume_id):
        sdk.FakeResourceObject(self.fake_snapshot_get)

    def snapshot_delete(self, volume_id, ignore_missing=True):
        return
