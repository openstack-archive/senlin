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
from senlin.tests.functional.drivers.openstack import sdk


class NovaClient(base.DriverBase):
    '''Fake Nova V2 driver for functional test.'''

    def __init__(self, ctx):
        self.fake_flavor = {
            "OS-FLV-DISABLED:disabled": False,
            "disk": 1,
            "OS-FLV-EXT-DATA:ephemeral": 0,
            "os-flavor-access:is_public": True,
            "id": "1",
            "links": [],
            "name": "m1.tiny",
            "ram": 512,
            "swap": "",
            "vcpus": 1
        }

        self.fake_image = {
            "created": "2015-01-01T01:02:03Z",
            "id": "70a599e0-31e7-49b7-b260-868f441e862b",
            "links": [],
            "metadata": {
                "architecture": "x86_64",
                "auto_disk_config": "True",
                "kernel_id": "nokernel",
                "ramdisk_id": "nokernel"
            },
            "minDisk": 0,
            "minRam": 0,
            "name": "cirros-0.3.2-x86_64-uec",
            "progress": 100,
            "status": "ACTIVE",
            "updated": "2011-01-01T01:02:03Z"
        }

        self.fake_server_create = {
            "id": "893c7791-f1df-4c3d-8383-3caae9656c62",
            "name": "new-server-test",
            "imageRef": "http://localhost/openstack/images/test-image",
            "flavorRef": "http://localhost/openstack/flavors/1",
            "metadata": {
                "My Server Name": "Apache1"
            },
            "personality": [
                {
                    "path": "/etc/banner.txt",
                    "contents": "personality-content"
                }
            ],
            "block_device_mapping_v2": [
                {
                    "device_name": "/dev/sdb1",
                    "source_type": "blank",
                    "destination_type": "local",
                    "delete_on_termination": "True",
                    "guest_format": "swap",
                    "boot_index": "-1"
                },
                {
                    "device_name": "/dev/sda1",
                    "source_type": "volume",
                    "destination_type": "volume",
                    "uuid": "fake-volume-id-1",
                    "boot_index": "0"
                }
            ]
        }

        self.fake_server_get = {
            # Note: The name of some attrs are defined as following to keep
            # compatible with the resource definition in openstacksdk. But
            # the real name of these attrs returned by Nova API could be
            # different, e.g. the name of 'access_ipv4' attribute is actually
            # 'accessIPv4' in server_get API response.
            "name": "new-server-test",
            "id": "893c7791-f1df-4c3d-8383-3caae9656c62",
            "access_ipv4": "192.168.0.3",
            "access_ipv6": "fe80::ac0e:2aff:fe87:5911",
            "addresses": {
                "private": [
                    {
                        "addr": "192.168.0.3",
                        "version": 4
                    }
                ]
            },
            "created_at": "2015-08-18T21:11:09Z",
            "updated_at": "2012-08-20T21:11:09Z",
            "flavor": {
                "id": "1",
                "links": []
            },
            "host_id": "65201c14a29663e06d0748e561207d998b343",
            "image": {
                "id": "70a599e0-31e7-49b7-b260-868f441e862b",
                "links": []
            },
            "links": [],
            "metadata": {
                "My Server Name": "Apache1"
            },
            "progress": 0,
            "status": "ACTIVE",
            "project_id": "openstack",
            "user_id": "fake"
        }

    def flavor_find(self, name_or_id, ignore_missing=False):
        return sdk.FakeResourceObject(self.fake_flavor)

    def image_get_by_name(self, name_or_id, ignore_missing=False):
        return sdk.FakeResourceObject(self.fake_image)

    def server_create(self, **attrs):
        return sdk.FakeResourceObject(self.fake_server_create)

    def server_get(self, value):
        return sdk.FakeResourceObject(self.fake_server_get)

    def wait_for_server(self, value, timeout=None):
        return

    def wait_for_server_delete(self, value, timeout=None):
        return

    def server_update(self, value, **attrs):
        self.fake_server_get.update(attrs)
        return sdk.FakeResourceObject(self.fake_server_get)

    def server_delete(self, value, ignore_missing=True):
        return

    def server_metadata_get(self, **params):
        return {}

    def server_metadata_update(self, **params):
        return
