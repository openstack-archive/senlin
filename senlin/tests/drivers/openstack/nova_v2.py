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

import copy

from oslo_utils import uuidutils

from senlin.drivers import base
from senlin.tests.drivers.openstack import sdk


class NovaClient(base.DriverBase):
    '''Fake Nova V2 driver for test.'''

    def __init__(self, ctx):
        self.fake_flavor = {
            "OS-FLV-DISABLED:disabled": False,
            "disk": 1,
            "OS-FLV-EXT-DATA:ephemeral": 0,
            "os-flavor-access:is_public": True,
            "id": "66a81d68-bf48-4af5-897b-a3bfef7279a8",
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
                "id": "FAKE_IMAGE_ID",
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

        self.fake_service_list = [
            {
                'id': 'IDENTIFIER1',
                'binary': 'nova-api',
                'host': 'host1',
                'status': 'enabled',
                'state': 'up',
                'zone': 'nova'
            },
            {
                'id': 'IDENTIFIER2',
                'binary': 'nova-compute',
                'host': 'host1',
                'status': 'enabled',
                'state': 'up',
                'zone': 'nova'
            },
        ]

    def flavor_find(self, name_or_id, ignore_missing=False):
        return sdk.FakeResourceObject(self.fake_flavor)

    def image_find(self, name_or_id, ignore_missing=False):
        return sdk.FakeResourceObject(self.fake_image)

    def server_create(self, **attrs):
        self.fake_server_create['id'] = uuidutils.generate_uuid()
        self.fake_server_get['id'] = self.fake_server_create['id']
        return sdk.FakeResourceObject(self.fake_server_create)

    def server_get(self, server):
        return sdk.FakeResourceObject(self.fake_server_get)

    def wait_for_server(self, server, timeout=None):
        return

    def wait_for_server_delete(self, server, timeout=None):
        return

    def server_update(self, server, **attrs):
        self.fake_server_get.update(attrs)
        return sdk.FakeResourceObject(self.fake_server_get)

    def server_rebuild(self, server, imageref, name=None, admin_password=None,
                       **attrs):
        if imageref:
            attrs['image'] = {'id': imageref}
        if name:
            attrs['name'] = name
        if admin_password:
            attrs['adminPass'] = admin_password
        self.fake_server_get.update(attrs)

        return sdk.FakeResourceObject(self.fake_server_get)

    def server_resize(self, server, flavor):
        self.fake_server_get['flavor'].update({'id': flavor})

    def server_resize_confirm(self, server):
        return

    def server_resize_revert(self, server):
        return

    def server_delete(self, server, ignore_missing=True):
        return

    def server_force_delete(self, server, ignore_missing=True):
        return

    def server_metadata_get(self, server):
        return {}

    def server_metadata_update(self, server, metadata):
        new_server = copy.deepcopy(self.fake_server_get)
        new_server['metadata'] = metadata
        server = sdk.FakeResourceObject(new_server)
        return server

    def server_metadata_delete(self, server, keys):
        return

    def service_list(self):
        return sdk.FakeResourceObject(self.fake_service_list)

    def service_force_down(self, service, host, binary):
        return

    def service_enable(self, service, host, binary):
        return

    def service_disable(self, service, host, binary):
        return
