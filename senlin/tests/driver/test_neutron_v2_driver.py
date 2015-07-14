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
import six

from senlin.common import exception
from senlin.common.i18n import _
from senlin.drivers.openstack import neutron_v2
from senlin.drivers.openstack import sdk
from senlin.tests.common import base
from senlin.tests.common import utils


class TestNeutronV2Driver(base.SenlinTestCase):

    def setUp(self):
        super(TestNeutronV2Driver, self).setUp()
        self.context = utils.dummy_context()
        self.conn = mock.Mock()
        with mock.patch.object(sdk, 'create_connection') as mock_creare_conn:
            mock_creare_conn.return_value = self.conn
            self.nc = neutron_v2.NeutronClient(self.context)

    @mock.patch.object(sdk, 'create_connection')
    def test_init(self, mock_create_connection):
        params = self.context
        neutron_v2.NeutronClient(params)
        mock_create_connection.assert_called_once_with(params)

    def test_network_get(self):
        name_or_id = 'network_identifier'
        network_obj = mock.Mock()

        self.conn.network.find_network.return_value = network_obj
        res = self.nc.network_get(name_or_id)
        self.conn.network.find_network.assert_called_once_with(
            name_or_id)
        self.assertEqual(network_obj, res)

        exception_info = 'Exception happened when getting network.'
        fake_exception = sdk.exc.HttpException(exception_info)
        self.conn.network.find_network.side_effect = fake_exception
        ex = self.assertRaises(exception.Error, self.nc.network_get,
                               name_or_id)
        msg = _('Failed in getting network %(value)s: HttpException: '
                '%(ex)s') % {'value': name_or_id, 'ex': exception_info}
        self.assertEqual(msg, six.text_type(ex))

    def test_subnet_get(self):
        name_or_id = 'subnet_identifier'
        subnet_obj = mock.Mock()

        self.conn.network.find_subnet.return_value = subnet_obj
        res = self.nc.subnet_get(name_or_id)
        self.conn.network.find_subnet.assert_called_once_with(
            name_or_id)
        self.assertEqual(subnet_obj, res)

        exception_info = 'Exception happened when getting subnet.'
        fake_exception = sdk.exc.HttpException(exception_info)
        self.conn.network.find_subnet.side_effect = fake_exception
        ex = self.assertRaises(exception.Error, self.nc.subnet_get,
                               name_or_id)
        msg = _('Failed in getting subnet %(value)s: HttpException: '
                '%(ex)s') % {'value': name_or_id, 'ex': exception_info}
        self.assertEqual(msg, six.text_type(ex))

    def test_loadbalancer_get(self):
        name_or_id = 'loadbalancer_identifier'
        loadbalancer_obj = mock.Mock()

        self.conn.network.find_load_balancer.return_value = loadbalancer_obj
        res = self.nc.loadbalancer_get(name_or_id)
        self.conn.network.find_load_balancer.assert_called_once_with(
            name_or_id)
        self.assertEqual(loadbalancer_obj, res)

        exception_info = 'Exception happened when getting loadbalancer.'
        fake_exception = sdk.exc.HttpException(exception_info)
        self.conn.network.find_load_balancer.side_effect = fake_exception
        ex = self.assertRaises(exception.Error, self.nc.loadbalancer_get,
                               name_or_id)
        msg = _('Failed in getting loadbalancer %(value)s: HttpException: '
                '%(ex)s') % {'value': name_or_id, 'ex': exception_info}
        self.assertEqual(msg, six.text_type(ex))

    def test_loadbalancer_list(self):
        loadbalancers = ['lb1', 'lb2']

        self.conn.network.load_balancers.return_value = loadbalancers
        self.assertEqual(loadbalancers, self.nc.loadbalancer_list())
        self.conn.network.load_balancers.assert_called_once_with()

        exception_info = 'Exception happened when listing loadbalancer.'
        fake_exception = sdk.exc.HttpException(exception_info)
        self.conn.network.load_balancers.side_effect = fake_exception
        ex = self.assertRaises(exception.Error, self.nc.loadbalancer_list)
        msg = _('Failed in listing loadbalancer: HttpException: %(ex)s'
                ) % {'ex': exception_info}
        self.assertEqual(msg, six.text_type(ex))

    def test_loadbalancer_create(self):
        vip_subnet_id = 'ID1'
        lb_obj = mock.Mock()

        # All input parameters are provided
        kwargs = {
            'vip_address': '192.168.0.100',
            'name': 'test-loadbalancer',
            'description': 'This is a loadbalancer',
            'admin_state_up': True
        }

        self.conn.network.create_load_balancer.return_value = lb_obj
        self.assertEqual(lb_obj, self.nc.loadbalancer_create(vip_subnet_id,
                                                             **kwargs))
        self.conn.network.create_load_balancer.assert_called_once_with(
            vip_subnet_id=vip_subnet_id, **kwargs)

        # Use default input parameters
        kwargs = {
            'admin_state_up': True
        }
        self.assertEqual(lb_obj, self.nc.loadbalancer_create(vip_subnet_id))
        self.conn.network.create_load_balancer.assert_called_with(
            vip_subnet_id=vip_subnet_id, **kwargs)

        # Exception happened during creating progress
        exception_info = 'Exception happened when creating loadbalancer.'
        fake_exception = sdk.exc.HttpException(exception_info)
        self.conn.network.create_load_balancer.side_effect = fake_exception
        ex = self.assertRaises(exception.Error, self.nc.loadbalancer_create,
                               vip_subnet_id)
        msg = _('Failed in creating loadbalancer: HttpException: %(ex)s'
                ) % {'ex': exception_info}
        self.assertEqual(msg, six.text_type(ex))

    def test_loadbalancer_delete(self):
        lb_id = 'ID1'

        self.nc.loadbalancer_delete(lb_id, ignore_missing=False)
        self.conn.network.delete_load_balancer.assert_called_once_with(
            lb_id, ignore_missing=False)

        self.nc.loadbalancer_delete(lb_id)
        self.conn.network.delete_load_balancer.assert_called_with(
            lb_id, ignore_missing=True)
