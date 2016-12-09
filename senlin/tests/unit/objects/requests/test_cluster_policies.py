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
import six

from senlin.objects.requests import cluster_policies as cp
from senlin.tests.unit.common import base as test_base


class TestClusterPolicyList(test_base.SenlinTestCase):

    params = {
        'identity': 'fake_cluster',
        'policy_name': 'fake_name',
        'policy_type': 'fake_type',
        'enabled': True,
        'sort': 'enabled'
    }

    def test_cluster_policy_list(self):
        data = self.params

        sot = cp.ClusterPolicyListRequest(**data)
        self.assertEqual('fake_cluster', sot.identity)
        self.assertEqual('fake_name', sot.policy_name)
        self.assertEqual('fake_type', sot.policy_type)
        self.assertTrue(sot.enabled)
        self.assertEqual('enabled', sot.sort)

    def test_cluster_policy_list_invalid_param(self):
        data = copy.deepcopy(self.params)
        data['enabled'] = 'bad'
        ex = self.assertRaises(ValueError, cp.ClusterPolicyListRequest,
                               **data)
        self.assertEqual("Unrecognized value 'bad', acceptable values are: "
                         "'0', '1', 'f', 'false', 'n', 'no', 'off', 'on', "
                         "'t', 'true', 'y', 'yes'", six.text_type(ex))

    def test_cluster_policy_list_primitive(self):
        data = self.params

        sot = cp.ClusterPolicyListRequest(**data)
        res = sot.obj_to_primitive()

        self.assertIn('identity', res['senlin_object.changes'])
        self.assertIn('sort', res['senlin_object.changes'])
        self.assertIn('enabled', res['senlin_object.changes'])
        self.assertIn('policy_name', res['senlin_object.changes'])
        self.assertIn('policy_type', res['senlin_object.changes'])

        self.assertEqual('1.0', res['senlin_object.version'])
        self.assertEqual('senlin', res['senlin_object.namespace'])
        self.assertEqual('ClusterPolicyListRequest', res['senlin_object.name'])

        param = res['senlin_object.data']
        self.assertEqual('fake_cluster', param['identity'])
        self.assertEqual('enabled', param['sort'])
        self.assertEqual('fake_name', param['policy_name'])
        self.assertEqual('fake_type', param['policy_type'])
        self.assertTrue(param['enabled'])


class TestClusterPolicyGet(test_base.SenlinTestCase):

    def test_cluster_policy_get(self):
        sot = cp.ClusterPolicyGetRequest(identity='cid', policy_id='pid')

        self.assertEqual('cid', sot.identity)
        self.assertEqual('pid', sot.policy_id)

        res = sot.obj_to_primitive()

        self.assertIn('identity', res['senlin_object.changes'])
        self.assertIn('policy_id', res['senlin_object.changes'])

        self.assertEqual('senlin', res['senlin_object.namespace'])
        self.assertEqual('1.0', res['senlin_object.version'])
        self.assertEqual('ClusterPolicyGetRequest', res['senlin_object.name'])

        data = res['senlin_object.data']
        self.assertEqual('cid', data['identity'])
        self.assertEqual('pid', data['policy_id'])

    def test_cluster_policy_get_invalid_params(self):

        ex = self.assertRaises(ValueError, cp.ClusterPolicyGetRequest,
                               identity='cid', policy_id=['bad'])
        self.assertEqual("A string is required in field policy_id, not a list",
                         six.text_type(ex))
