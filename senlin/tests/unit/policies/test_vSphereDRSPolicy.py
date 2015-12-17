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

import mock
from senlin.common import exception
from senlin.engine import cluster as cluster_base
from senlin.engine import cluster_policy
from senlin.policies import vSphereDRS_policy as vp
from senlin.profiles import base as profile_base
from senlin.tests.unit.common import base
from senlin.tests.unit.common import utils


class TestvSphereDRSPolicy(base.SenlinTestCase):

    def setUp(self):
        super(TestvSphereDRSPolicy, self).setUp()
        self.context = utils.dummy_context()
        self.context.is_admin = True
        self.spec = {
            'type': 'senlin.policy.vSphereDRSPolicy',
            'version': '1.0',
            'properties': {
                'placement_group': {}
            },
        }
        profile = mock.Mock()
        profile.id = 'PROFILE_ID'
        cluster = mock.Mock()
        cluster.id = 'CLUSTER_ID'
        self.profile = profile
        self.cluster = cluster

    def test_policy_init(self):
        policy = vp.vSphereDRSPolicy('test-policy', self.spec)
        self.assertIsNone(policy.id)
        self.assertEqual('test-policy', policy.name)
        self.assertEqual('senlin.policy.vSphereDRSPolicy-1.0', policy.type)
        self.assertIsNone(policy._novaclient)

    def test_attach_with_profile_info(self):
        profile_base.Profile.load = mock.Mock(return_value=self.profile)
        profile_spec = {
            'scheduler_hints': {
                'group': 'GP_NAME',
            },
        }
        self.profile.spec = profile_spec

        sg_instance = mock.Mock()
        sg_instance.id = 'GROUP_ID'
        nc = mock.Mock()
        nc.get_server_group = mock.Mock(return_value=sg_instance)

        policy = vp.vSphereDRSPolicy('test-policy', self.spec)
        policy._novaclient = nc

        policy_data = {
            'vSphereDRSPolicy': {
                'data': {
                    'group_id': 'GROUP_ID',
                    'inherited_group': True,
                },
                'version': '1.0'
            }
        }

        res, data = policy.attach(self.cluster)

        self.assertTrue(res)
        self.assertEqual(policy_data, data)

        nc.get_server_group.side_effect = exception.InternalError(
            code=400, message='failed request')
        res, data = policy.attach(self.cluster)

        self.assertFalse(res)
        self.assertEqual('Failed in searching server_group',
                         data)

    def test_attach_with_rule(self):
        profile_base.Profile.load = mock.Mock(return_value=self.profile)
        profile_spec = {}
        self.profile.spec = profile_spec

        self.spec = {
            'type': 'senlin.policy.vSphereDRSPolicy',
            'version': '1.0',
            'properties': {
                'placement_group': {
                    'placement_rule': 'anti_affinity',
                },
            },
        }

        sg_instance = mock.Mock()
        sg_instance.id = 'GROUP_ID'
        nc = mock.Mock()
        nc.create_server_group = mock.Mock(return_value=sg_instance)

        policy = vp.vSphereDRSPolicy('test-policy', self.spec)
        policy._novaclient = nc

        policy_data = {
            'vSphereDRSPolicy': {
                'data': {
                    'group_id': 'GROUP_ID',
                    'inherited_group': False,
                },
                'version': '1.0'
            }
        }

        res, data = policy.attach(self.cluster)

        self.assertTrue(res)
        self.assertEqual(policy_data, data)

        nc.create_server_group.side_effect = exception.InternalError(
            code=400, message='failed request')

        res, data = policy.attach(self.cluster)

        self.assertFalse(res)
        self.assertEqual('Failed in creating server_group',
                         data)

    def test_attach_with_group_name(self):
        profile_base.Profile.load = mock.Mock(return_value=self.profile)
        profile_spec = {}
        self.profile.spec = profile_spec

        self.spec = {
            'type': 'senlin.policy.vSphereDRSPolicy',
            'version': '1.0',
            'properties': {
                'placement_group': {
                    'group_name': 'GP_NAME',
                },
            },
        }

        sg_instance = mock.Mock()
        sg_instance.id = 'GROUP_ID'
        nc = mock.Mock()
        nc.get_server_group = mock.Mock(return_value=sg_instance)

        policy = vp.vSphereDRSPolicy('test-policy', self.spec)
        policy._novaclient = nc

        policy_data = {
            'vSphereDRSPolicy': {
                'data': {
                    'group_id': 'GROUP_ID',
                    'inherited_group': True,
                },
                'version': '1.0'
            }
        }

        res, data = policy.attach(self.cluster)

        self.assertTrue(res)
        self.assertEqual(policy_data, data)

        nc.get_server_group.side_effect = exception.InternalError(
            code=400, message='failed request')

        res, data = policy.attach(self.cluster)

        self.assertFalse(res)
        self.assertEqual('Failed in searching server_group',
                         data)

    @mock.patch.object(cluster_policy.ClusterPolicy, 'load')
    def test_detach_no_policy_data(self, mock_load):
        cp = mock.Mock()
        cp_data = {
            'vSphereDRSPolicy': {
                'version': '1.0',
                'data': None,
            }
        }
        cp.data = cp_data
        mock_load.return_value = cp
        policy = vp.vSphereDRSPolicy('test-policy', self.spec)
        res, data = policy.detach(self.cluster)
        self.assertTrue(res)
        self.assertEqual('Server group resources deletion succeeded',
                         data)

    @mock.patch.object(cluster_policy.ClusterPolicy, 'load')
    def test_detach_with_policy_data(self, mock_load):
        cp = mock.Mock()
        policy_data = {
            'group_id': 'GROUP_ID',
            'inherited_group': False,
        }
        cp_data = {
            'vSphereDRSPolicy': {
                'version': '1.0',
                'data': policy_data
            }
        }
        cp.data = cp_data

        nc = mock.Mock()
        nc.delete_server_group = mock.Mock(return_value=True)

        policy = vp.vSphereDRSPolicy('test-policy', self.spec)
        policy._novaclient = nc
        policy.count = 2

        mock_load.return_value = cp
        res, data = policy.detach(self.cluster)

        self.assertTrue(res)
        self.assertEqual('Server group resources deletion succeeded', data)

        nc.delete_server_group.side_effect = exception.InternalError(
            code=400, message='failed request')

        res, data = policy.detach(self.cluster)

        self.assertFalse(res)
        self.assertEqual('Failed in deleting server_group',
                         data)

    @mock.patch.object(cluster_policy.ClusterPolicy, 'load')
    @mock.patch.object(cluster_base.Cluster, 'load')
    def test_pre_op(self, mock_cluster_get, mock_policy_load):
        # test pre_op method whether returns the correct action.data
        cp = mock.Mock()
        policy_data = {
            'group_id': 'GROUP_ID',
        }
        cp_data = {
            'vSphereDRSPolicy': {
                'version': '1.0',
                'data': policy_data,
            }
        }
        cp.data = cp_data

        hypervisor = mock.Mock()
        hypervisor.hypervisor_hostname = 'opestack_drs'
        hypervisor.id = 'HOST_ID'

        hypervisors = {hypervisor}
        hypervisor_info = {
            'service': {
                'host': 'openstack_drs'
            }
        }

        nc = mock.Mock()
        nc.get_hypervisors = mock.Mock(return_value=hypervisors)
        nc.get_hypervisor_by_id = mock.Mock(return_value=hypervisor_info)

        policy = vp.vSphereDRSPolicy('test-policy', self.spec)
        policy._novaclient = nc
        policy.count = 2

        mock_policy_load.return_value = cp
        mock_cluster_get.return_value = self.cluster

        action = mock.Mock()
        action.context = self.context
        action.data = {'placement': {'count': 2}}

        policy.pre_op(self.cluster.id, action)

        placement = {
            'count': 2,
            'placements': [
                {
                    'zone': 'nova:openstack_drs',
                    'scheduler_hints': {
                        'group': 'GROUP_ID',
                    },
                },
                {
                    'zone': 'nova:openstack_drs',
                    'scheduler_hints': {
                        'group': 'GROUP_ID',
                    },
                }
            ]
        }

        self.assertEqual(placement, action.data['placement'])
        action.store.assert_called_with(self.context)
