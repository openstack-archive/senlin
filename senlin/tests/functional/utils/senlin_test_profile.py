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

from senlin.common.i18n import _
from senlin.common import schema
from senlin.profiles import base


class TestProfile(base.Profile):
    '''Test profile type'''

    KEYS = (
        CONTEXT, KEY1, KEY2
    ) = (
        'context', 'key1', 'key2',
    )

    spec_schema = {
        CONTEXT: schema.Map(
            _('A dictionary for specifying the customized context'),
            default={},
        ),
        KEY1: schema.String(
            _('The first key of Senlin test profile schema'),
            default='value1',
        ),
        KEY2: schema.String(
            _('The second key of Senlin test profile schema'),
            default='value2',
        ),
    }

    def __init__(self, type_name, name, **kwargs):
        super(TestProfile, self).__init__(type_name, name, **kwargs)
        return

    def do_validate(self, obj):
        return True

    def do_create(self, obj):
        return 'TEST_ID'

    def do_delete(self, obj):
        return True

    def do_update(self, obj, new_profile, **params):
        return True

    def do_check(self, obj):
        return True

    def do_get_details(self, obj):
        return {'description': 'An os.senlin.test profile'}

    def do_join(self, obj, cluster_id):
        return {}

    def do_leave(self, obj):
        return True
