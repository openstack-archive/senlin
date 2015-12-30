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


class FakeResourceObject(object):
    '''Generate a fake SDK resource object based on given dictionary'''
    def __init__(self, params):
        for key in params:
            setattr(self, key, params[key])

    def to_dict(self):
        data = {
            'image': {
                'id': 'FAKE_IMAGE'
            },
            'flavor': {
                'id': 'FAKE_FLAVOR'
            },
            'addresses': {
                'private': [
                    {
                        'OS-EXT-IPS:type': 'fixed',
                        'addr': '10.0.0.5',
                        'version': 4
                    }
                ]
            },
            'security_groups': [
                {
                    'name': 'default'
                }
            ]
        }

        return data
