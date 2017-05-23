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

import mock
import six

from senlin.common import exception as exc
from senlin.objects import node as node_obj
from senlin.profiles.os.nova import server
from senlin.tests.unit.common import base
from senlin.tests.unit.common import utils


class TestServerNameChecking(base.SenlinTestCase):

    scenarios = [
        ('none-none', dict(
            old_name=None,
            new_name=None,
            result=(False, 'NODE_NAME'))),
        ('none-new', dict(
            old_name=None,
            new_name='NEW_NAME',
            result=(True, 'NEW_NAME'))),
        ('old-none', dict(
            old_name='OLD_NAME',
            new_name=None,
            result=(True, 'NODE_NAME'))),
        ('old-new', dict(
            old_name='OLD_NAME',
            new_name='NEW_NAME',
            result=(True, 'NEW_NAME')))
    ]

    def setUp(self):
        super(TestServerNameChecking, self).setUp()
        self.old_spec = {
            'type': 'os.nova.server',
            'version': '1.0',
            'properties': {
                'flavor': 'FLAVOR',
            }
        }
        self.new_spec = copy.deepcopy(self.old_spec)
        obj = mock.Mock()
        obj.name = 'NODE_NAME'
        self.obj = obj

    def test_check_server_name(self):
        if self.old_name:
            self.old_spec['properties']['name'] = self.old_name
        if self.new_name:
            self.new_spec['properties']['name'] = self.new_name

        profile = server.ServerProfile('t', self.old_spec)
        new_profile = server.ServerProfile('t1', self.new_spec)

        res = profile._check_server_name(self.obj, new_profile)

        self.assertEqual(self.result, res)


class TestPasswordChecking(base.SenlinTestCase):

    scenarios = [
        ('none-none', dict(
            old_passwd=None,
            new_passwd=None,
            result=(False, ''))),
        ('none-new', dict(
            old_passwd=None,
            new_passwd='NEW_PASSWD',
            result=(True, 'NEW_PASSWD'))),
        ('old-none', dict(
            old_passwd='OLD_PASSWD',
            new_passwd=None,
            result=(True, ''))),
        ('old-new', dict(
            old_passwd='OLD_PASSWD',
            new_passwd='NEW_PASSWD',
            result=(True, 'NEW_PASSWD')))
    ]

    def setUp(self):
        super(TestPasswordChecking, self).setUp()
        self.old_spec = {
            'type': 'os.nova.server',
            'version': '1.0',
            'properties': {
                'flavor': 'FLAVOR',
            }
        }
        self.new_spec = copy.deepcopy(self.old_spec)
        self.obj = mock.Mock()

    def test_check_password(self):
        if self.old_passwd:
            self.old_spec['properties']['admin_pass'] = self.old_passwd
        if self.new_passwd:
            self.new_spec['properties']['admin_pass'] = self.new_passwd

        profile = server.ServerProfile('t', self.old_spec)
        new_profile = server.ServerProfile('t1', self.new_spec)

        res = profile._check_password(self.obj, new_profile)

        self.assertEqual(self.result, res)


class TestNovaServerUpdate(base.SenlinTestCase):
    def setUp(self):
        super(TestNovaServerUpdate, self).setUp()

        self.context = utils.dummy_context()
        self.spec = {
            'type': 'os.nova.server',
            'version': '1.0',
            'properties': {
                'context': {},
                'admin_pass': 'adminpass',
                'auto_disk_config': True,
                'availability_zone': 'FAKE_AZ',
                'block_device_mapping': [{
                    'device_name': 'FAKE_NAME',
                    'volume_size': 1000,
                }],
                'config_drive': False,
                'flavor': 'FLAV',
                'image': 'FAKE_IMAGE',
                'key_name': 'FAKE_KEYNAME',
                "metadata": {"meta var": "meta val"},
                'name': 'FAKE_SERVER_NAME',
                'networks': [{
                    'port': 'FAKE_PORT',
                    'fixed_ip': 'FAKE_IP',
                    'network': 'FAKE_NET',
                }],
                'personality': [{
                    'path': '/etc/motd',
                    'contents': 'foo',
                }],
                'scheduler_hints': {
                    'same_host': 'HOST_ID',
                },
                'security_groups': ['HIGH_SECURITY_GROUP'],
                'user_data': 'FAKE_USER_DATA',
            }
        }
        self.patchobject(node_obj.Node, 'update')

    def test__update_name(self):
        profile = server.ServerProfile('t', self.spec)
        cc = mock.Mock()
        profile._computeclient = cc
        obj = mock.Mock(physical_id='NOVA_ID')

        res = profile._update_name(obj, 'NEW_NAME')

        self.assertIsNone(res)
        cc.server_update.assert_called_once_with('NOVA_ID', name='NEW_NAME')

    def test__update_name_nova_failure(self):
        profile = server.ServerProfile('t', self.spec)
        cc = mock.Mock()
        profile._computeclient = cc
        cc.server_update.side_effect = exc.InternalError(message='BOOM')
        obj = mock.Mock(physical_id='NOVA_ID')

        ex = self.assertRaises(exc.EResourceUpdate,
                               profile._update_name,
                               obj, 'NEW_NAME')

        self.assertEqual("Failed in updating server 'NOVA_ID': BOOM.",
                         six.text_type(ex))
        cc.server_update.assert_called_once_with('NOVA_ID', name='NEW_NAME')

    def test__update_password(self):
        profile = server.ServerProfile('t', self.spec)
        cc = mock.Mock()
        profile._computeclient = cc
        obj = mock.Mock(physical_id='NOVA_ID')

        res = profile._update_password(obj, 'NEW_PASSWORD')

        self.assertIsNone(res)
        cc.server_change_password.assert_called_once_with(
            'NOVA_ID', 'NEW_PASSWORD')

    def test__update_password_nova_failure(self):
        profile = server.ServerProfile('t', self.spec)
        cc = mock.Mock()
        profile._computeclient = cc
        err = exc.InternalError(message='BOOM')
        cc.server_change_password.side_effect = err
        obj = mock.Mock(physical_id='NOVA_ID')

        ex = self.assertRaises(exc.EResourceUpdate,
                               profile._update_password,
                               obj, 'NEW_PASSWORD')

        self.assertEqual("Failed in updating server 'NOVA_ID': BOOM.",
                         six.text_type(ex))
        cc.server_change_password.assert_called_once_with(
            'NOVA_ID', 'NEW_PASSWORD')

    def test__update_metadata(self):
        obj = mock.Mock(id='NODE_ID', physical_id='NOVA_ID',
                        cluster_id='CLUSTER_ID', index=456)
        cc = mock.Mock()
        profile = server.ServerProfile('t', self.spec)
        profile._computeclient = cc
        new_spec = copy.deepcopy(self.spec)
        new_spec['properties']['metadata'] = {'new_key': 'new_value'}
        new_profile = server.ServerProfile('t', new_spec)

        res = profile._update_metadata(obj, new_profile)

        self.assertIsNone(res)
        cc.server_metadata_update.assert_called_once_with(
            'NOVA_ID',
            {
                'new_key': 'new_value',
                'cluster_node_id': 'NODE_ID',
                'cluster_id': 'CLUSTER_ID',
                'cluster_node_index': '456',
            }
        )

    def test___update_metadata_no_change(self):
        obj = mock.Mock(id='NODE_ID')
        profile = server.ServerProfile('t', self.spec)
        cc = mock.Mock()
        profile._computeclient = cc
        new_spec = copy.deepcopy(self.spec)
        new_profile = server.ServerProfile('t', new_spec)

        res = profile._update_metadata(obj, new_profile)

        self.assertIsNone(res)
        self.assertEqual(0, cc.server_metadata_update.call_count)

    def test__update_metadata_nova_failure(self):
        obj = mock.Mock(id='NODE_ID', physical_id='NOVA_ID', cluster_id='')
        err = exc.InternalError(code=500, message='Nova Error')
        cc = mock.Mock()
        cc.server_metadata_update.side_effect = err
        profile = server.ServerProfile('t', self.spec)
        profile._computeclient = cc

        # new profile with new metadata
        new_spec = copy.deepcopy(self.spec)
        new_spec['properties']['metadata'] = {'fooa': 'baaar'}
        new_profile = server.ServerProfile('t', new_spec)

        ex = self.assertRaises(exc.EResourceUpdate,
                               profile._update_metadata,
                               obj, new_profile)

        self.assertEqual("Failed in updating server 'NOVA_ID': "
                         "Nova Error.", six.text_type(ex))
        cc.server_metadata_update.assert_called_once_with(
            'NOVA_ID', {'fooa': 'baaar', 'cluster_node_id': 'NODE_ID'}
        )

    def test__update_flavor(self):
        obj = mock.Mock(physical_id='NOVA_ID')
        cc = mock.Mock()
        profile = server.ServerProfile('t', self.spec)
        profile._computeclient = cc
        x_flavors = [mock.Mock(id='123'), mock.Mock(id='456')]
        mock_validate = self.patchobject(profile, '_validate_flavor',
                                         side_effect=x_flavors)
        new_spec = copy.deepcopy(self.spec)
        new_spec['properties']['flavor'] = 'new_flavor'
        new_profile = server.ServerProfile('t1', new_spec)
        profile._update_flavor(obj, new_profile)

        mock_validate.assert_has_calls([
            mock.call(obj, 'FLAV', 'update'),
            mock.call(obj, 'new_flavor', 'update')
        ])
        cc.server_resize.assert_called_once_with('NOVA_ID', '456')
        cc.server_resize_confirm.assert_called_once_with('NOVA_ID')
        cc.wait_for_server.has_calls([
            mock.call('NOVA_ID', 'VERIFY_RESIZE'),
            mock.call('NOVA_ID', 'ACTIVE')])

    def test__update_flavor_failed_validation(self):
        obj = mock.Mock(physical_id='NOVA_ID')
        cc = mock.Mock()
        profile = server.ServerProfile('t', self.spec)
        profile._computeclient = cc
        new_spec = copy.deepcopy(self.spec)
        new_spec['properties']['flavor'] = 'new_flavor'
        new_profile = server.ServerProfile('t1', new_spec)
        err = exc.EResourceUpdate(type='server', id='NOVA_ID', message='BOOM')
        mock_validate = self.patchobject(profile, '_validate_flavor',
                                         side_effect=err)

        self.assertRaises(exc.EResourceUpdate,
                          profile._update_flavor,
                          obj, new_profile)

        mock_validate.assert_called_once_with(obj, 'FLAV', 'update')

    def test__update_flavor_failed_validation_2(self):
        obj = mock.Mock(physical_id='NOVA_ID')
        cc = mock.Mock()
        profile = server.ServerProfile('t', self.spec)
        profile._computeclient = cc
        new_spec = copy.deepcopy(self.spec)
        new_spec['properties']['flavor'] = 'new_flavor'
        new_profile = server.ServerProfile('t1', new_spec)
        result = [
            mock.Mock(),
            exc.EResourceUpdate(type='server', id='NOVA_ID', message='BOOM')
        ]
        mock_validate = self.patchobject(profile, '_validate_flavor',
                                         side_effect=result)

        self.assertRaises(exc.EResourceUpdate,
                          profile._update_flavor,
                          obj, new_profile)

        mock_validate.assert_has_calls([
            mock.call(obj, 'FLAV', 'update'),
            mock.call(obj, 'new_flavor', 'update'),
        ])

    def test__update_flavor_same(self):
        obj = mock.Mock(physical_id='NOVA_ID')
        cc = mock.Mock()
        profile = server.ServerProfile('t', self.spec)
        profile._computeclient = cc
        new_spec = copy.deepcopy(self.spec)
        new_profile = server.ServerProfile('t1', new_spec)

        x_flavors = [mock.Mock(id=123), mock.Mock(id=123)]
        mock_validate = self.patchobject(profile, '_validate_flavor',
                                         side_effect=x_flavors)

        res = profile._update_flavor(obj, new_profile)

        self.assertIsNone(res)
        mock_validate.assert_has_calls([
            mock.call(obj, 'FLAV', 'update'),
            mock.call(obj, 'FLAV', 'update'),
        ])
        self.assertEqual(0, cc.server_resize.call_count)

    def test__update_flavor_resize_failed(self):
        obj = mock.Mock(physical_id='NOVA_ID')
        cc = mock.Mock()
        cc.server_resize.side_effect = [
            exc.InternalError(code=500, message='Resize failed')]
        profile = server.ServerProfile('t', self.spec)
        profile._computeclient = cc
        new_spec = copy.deepcopy(self.spec)
        new_spec['properties']['flavor'] = 'new_flavor'
        new_profile = server.ServerProfile('t1', new_spec)
        x_flavors = [mock.Mock(id='123'), mock.Mock(id='456')]
        mock_validate = self.patchobject(profile, '_validate_flavor',
                                         side_effect=x_flavors)

        ex = self.assertRaises(exc.EResourceUpdate,
                               profile._update_flavor,
                               obj, new_profile)

        mock_validate.assert_has_calls([
            mock.call(obj, 'FLAV', 'update'),
            mock.call(obj, 'new_flavor', 'update'),
        ])
        cc.server_resize.assert_called_once_with('NOVA_ID', '456')
        cc.server_resize_revert.assert_called_once_with('NOVA_ID')
        cc.wait_for_server.assert_called_once_with('NOVA_ID', 'ACTIVE')
        self.assertEqual("Failed in updating server 'NOVA_ID': Resize "
                         "failed.", six.text_type(ex))

    def test__update_flavor_first_wait_for_server_failed(self):
        obj = mock.Mock(physical_id='NOVA_ID')
        cc = mock.Mock()
        cc.wait_for_server.side_effect = [
            exc.InternalError(code=500, message='TIMEOUT'),
            None
        ]

        profile = server.ServerProfile('t', self.spec)
        profile._computeclient = cc
        new_spec = copy.deepcopy(self.spec)
        new_spec['properties']['flavor'] = 'new_flavor'
        new_profile = server.ServerProfile('t1', new_spec)
        x_flavors = [mock.Mock(id='123'), mock.Mock(id='456')]
        mock_validate = self.patchobject(profile, '_validate_flavor',
                                         side_effect=x_flavors)
        # do it
        ex = self.assertRaises(exc.EResourceUpdate,
                               profile._update_flavor,
                               obj, new_profile)

        # assertions
        mock_validate.assert_has_calls([
            mock.call(obj, 'FLAV', 'update'),
            mock.call(obj, 'new_flavor', 'update'),
        ])
        cc.server_resize.assert_called_once_with('NOVA_ID', '456')
        cc.wait_for_server.has_calls([
            mock.call('NOVA_ID', 'VERIFY_RESIZE'),
            mock.call('NOVA_ID', 'ACTIVE')])
        cc.server_resize_revert.assert_called_once_with('NOVA_ID')
        self.assertEqual("Failed in updating server 'NOVA_ID': "
                         "TIMEOUT.", six.text_type(ex))

    def test__update_flavor_resize_failed_revert_failed(self):
        obj = mock.Mock(physical_id='NOVA_ID')
        cc = mock.Mock()
        err_resize = exc.InternalError(code=500, message='Resize')
        cc.server_resize.side_effect = err_resize
        err_revert = exc.InternalError(code=500, message='Revert')
        cc.server_resize_revert.side_effect = err_revert
        profile = server.ServerProfile('t', self.spec)
        profile._computeclient = cc
        new_spec = copy.deepcopy(self.spec)
        new_spec['properties']['flavor'] = 'new_flavor'
        new_profile = server.ServerProfile('t1', new_spec)
        x_flavors = [mock.Mock(id='123'), mock.Mock(id='456')]
        mock_validate = self.patchobject(profile, '_validate_flavor',
                                         side_effect=x_flavors)

        # do it
        ex = self.assertRaises(exc.EResourceUpdate,
                               profile._update_flavor,
                               obj, new_profile)

        # assertions
        mock_validate.assert_has_calls([
            mock.call(obj, 'FLAV', 'update'),
            mock.call(obj, 'new_flavor', 'update'),
        ])
        cc.server_resize.assert_called_once_with('NOVA_ID', '456')
        cc.server_resize_revert.assert_called_once_with('NOVA_ID')
        # the wait_for_server wasn't called
        self.assertEqual(0, cc.wait_for_server.call_count)
        self.assertEqual("Failed in updating server 'NOVA_ID': "
                         "Revert.", six.text_type(ex))

    def test__update_flavor_confirm_failed(self):
        obj = mock.Mock(physical_id='NOVA_ID')
        cc = mock.Mock()
        err_confirm = exc.InternalError(code=500, message='Confirm')
        cc.server_resize_confirm.side_effect = err_confirm
        profile = server.ServerProfile('t', self.spec)
        profile._computeclient = cc
        new_spec = copy.deepcopy(self.spec)
        new_spec['properties']['flavor'] = 'new_flavor'
        new_profile = server.ServerProfile('t1', new_spec)
        x_flavors = [mock.Mock(id='123'), mock.Mock(id='456')]
        mock_validate = self.patchobject(profile, '_validate_flavor',
                                         side_effect=x_flavors)

        # do it
        ex = self.assertRaises(exc.EResourceUpdate,
                               profile._update_flavor,
                               obj, new_profile)

        # assertions
        mock_validate.assert_has_calls([
            mock.call(obj, 'FLAV', 'update'),
            mock.call(obj, 'new_flavor', 'update'),
        ])
        cc.server_resize.assert_called_once_with('NOVA_ID', '456')
        cc.server_resize_confirm.assert_called_once_with('NOVA_ID')
        cc.wait_for_server.assert_called_once_with('NOVA_ID', 'VERIFY_RESIZE')
        self.assertEqual("Failed in updating server 'NOVA_ID': Confirm.",
                         six.text_type(ex))

    def test__update_flavor_wait_confirm_failed(self):
        obj = mock.Mock(physical_id='NOVA_ID')
        cc = mock.Mock()
        err_wait = exc.InternalError(code=500, message='Wait')
        cc.wait_for_server.side_effect = [None, err_wait]
        profile = server.ServerProfile('t', self.spec)
        profile._computeclient = cc
        new_spec = copy.deepcopy(self.spec)
        new_spec['properties']['flavor'] = 'new_flavor'
        new_profile = server.ServerProfile('t1', new_spec)
        x_flavors = [mock.Mock(id='123'), mock.Mock(id='456')]
        mock_validate = self.patchobject(profile, '_validate_flavor',
                                         side_effect=x_flavors)

        # do it
        ex = self.assertRaises(exc.InternalError,
                               profile._update_flavor,
                               obj, new_profile)

        # assertions
        mock_validate.assert_has_calls([
            mock.call(obj, 'FLAV', 'update'),
            mock.call(obj, 'new_flavor', 'update'),
        ])
        cc.server_resize.assert_called_once_with('NOVA_ID', '456')
        cc.server_resize_confirm.assert_called_once_with('NOVA_ID')
        cc.wait_for_server.assert_has_calls([
            mock.call('NOVA_ID', 'VERIFY_RESIZE'),
            mock.call('NOVA_ID', 'ACTIVE')
        ])
        self.assertEqual("Failed in updating server 'NOVA_ID': Wait.",
                         six.text_type(ex))

    def test__update_image(self):
        profile = server.ServerProfile('t', self.spec)
        cc = mock.Mock()
        profile._computeclient = cc
        x_old_image = mock.Mock(id='123')
        x_new_image = mock.Mock(id='456')
        x_images = [x_new_image, x_old_image]
        mock_check = self.patchobject(profile, '_validate_image',
                                      side_effect=x_images)
        obj = mock.Mock(physical_id='NOVA_ID')
        new_spec = copy.deepcopy(self.spec)
        new_spec['properties']['image'] = 'new_image'
        new_profile = server.ServerProfile('t1', new_spec)

        profile._update_image(obj, new_profile, 'new_name', 'new_pass')

        mock_check.assert_has_calls([
            mock.call(obj, 'new_image', reason='update'),
            mock.call(obj, 'FAKE_IMAGE', reason='update')
        ])
        cc.server_rebuild.assert_called_once_with(
            'NOVA_ID', '456', 'new_name', 'new_pass')
        cc.wait_for_server.assert_called_once_with('NOVA_ID', 'ACTIVE')

    def test__update_image_new_image_is_none(self):
        profile = server.ServerProfile('t', self.spec)
        obj = mock.Mock(physical_id='NOVA_ID')
        new_spec = copy.deepcopy(self.spec)
        del new_spec['properties']['image']
        new_profile = server.ServerProfile('t1', new_spec)

        ex = self.assertRaises(exc.EResourceUpdate,
                               profile._update_image,
                               obj, new_profile, 'new_name', '')

        msg = ("Failed in updating server 'NOVA_ID': Updating Nova server"
               " with image set to None is not supported by Nova.")
        self.assertEqual(msg, six.text_type(ex))

    def test__update_image_new_image_invalid(self):
        # NOTE: The image invalid could be caused by a non-existent image or
        # a compute driver failure
        profile = server.ServerProfile('t', self.spec)
        # _validate_image will always throw EResourceUpdate if driver fails
        err = exc.EResourceUpdate(type='server', id='NOVA_ID', message='BAD')
        mock_check = self.patchobject(profile, '_validate_image',
                                      side_effect=err)
        obj = mock.Mock(physical_id='NOVA_ID')
        new_spec = copy.deepcopy(self.spec)
        new_spec['properties']['image'] = 'new_image'
        new_profile = server.ServerProfile('t1', new_spec)

        ex = self.assertRaises(exc.EResourceUpdate,
                               profile._update_image,
                               obj, new_profile, 'new_name', 'new_pass')

        msg = ("Failed in updating server 'NOVA_ID': BAD.")
        self.assertEqual(msg, six.text_type(ex))
        mock_check.assert_called_once_with(obj, 'new_image', reason='update')

    def test__update_image_old_image_invalid(self):
        # NOTE: The image invalid could be caused by a non-existent image or
        # a compute driver failure
        profile = server.ServerProfile('t', self.spec)
        profile._computeclient = mock.Mock()
        # _validate_image will always throw EResourceUpdate if driver fails
        results = [
            mock.Mock(id='NEW_IMAGE'),
            exc.EResourceUpdate(type='server', id='NOVA_ID', message='BAD')
        ]
        mock_check = self.patchobject(profile, '_validate_image',
                                      side_effect=results)
        obj = mock.Mock(physical_id='NOVA_ID')
        new_spec = copy.deepcopy(self.spec)
        new_spec['properties']['image'] = 'new_image'
        new_profile = server.ServerProfile('t1', new_spec)

        ex = self.assertRaises(exc.EResourceUpdate,
                               profile._update_image,
                               obj, new_profile, 'new_name', 'new_pass')

        msg = ("Failed in updating server 'NOVA_ID': BAD.")
        self.assertEqual(msg, six.text_type(ex))
        mock_check.assert_has_calls([
            mock.call(obj, 'new_image', reason='update'),
            mock.call(obj, 'FAKE_IMAGE', reason='update')
        ])

    def test__update_image_old_image_is_none_but_succeeded(self):
        old_spec = copy.deepcopy(self.spec)
        del old_spec['properties']['image']
        profile = server.ServerProfile('t', old_spec)
        cc = mock.Mock()
        profile._computeclient = cc
        x_server = mock.Mock(image={'id': '123'})
        cc.server_get.return_value = x_server
        # this is the new one
        x_image = mock.Mock(id='456')
        mock_check = self.patchobject(profile, '_validate_image',
                                      return_value=x_image)
        obj = mock.Mock(physical_id='NOVA_ID')
        new_spec = copy.deepcopy(self.spec)
        new_spec['properties']['image'] = 'new_image'
        new_profile = server.ServerProfile('t1', new_spec)

        res = profile._update_image(obj, new_profile, 'new_name', 'new_pass')

        self.assertTrue(res)
        mock_check.assert_called_once_with(obj, 'new_image', reason='update')
        cc.server_get.assert_called_once_with('NOVA_ID')
        cc.server_rebuild.assert_called_once_with(
            'NOVA_ID', '456', 'new_name', 'new_pass')
        cc.wait_for_server.assert_called_once_with('NOVA_ID', 'ACTIVE')

    def test__update_image_old_image_is_none_but_failed(self):
        old_spec = copy.deepcopy(self.spec)
        del old_spec['properties']['image']
        profile = server.ServerProfile('t', old_spec)
        cc = mock.Mock()
        profile._computeclient = cc
        # this is about the new one
        x_image = mock.Mock(id='456')
        mock_check = self.patchobject(profile, '_validate_image',
                                      return_value=x_image)
        cc.server_get.side_effect = exc.InternalError(message='DRIVER')
        obj = mock.Mock(physical_id='NOVA_ID')
        new_spec = copy.deepcopy(self.spec)
        new_spec['properties']['image'] = 'new_image'
        new_profile = server.ServerProfile('t1', new_spec)

        ex = self.assertRaises(exc.EResourceUpdate,
                               profile._update_image,
                               obj, new_profile, 'new_name', 'new_pass')

        self.assertEqual("Failed in updating server 'NOVA_ID': DRIVER.",
                         six.text_type(ex))
        mock_check.assert_called_once_with(obj, 'new_image', reason='update')
        cc.server_get.assert_called_once_with('NOVA_ID')

    def test__update_image_updating_to_same_image(self):
        profile = server.ServerProfile('t', self.spec)
        cc = mock.Mock()
        profile._computeclient = cc
        x_old_image = mock.Mock(id='123')
        x_new_image = mock.Mock(id='123')
        x_images = [x_old_image, x_new_image]
        mock_check = self.patchobject(profile, '_validate_image',
                                      side_effect=x_images)
        obj = mock.Mock(physical_id='NOVA_ID')
        new_spec = copy.deepcopy(self.spec)
        new_spec['properties']['image'] = 'new_image'
        new_profile = server.ServerProfile('t1', new_spec)

        res = profile._update_image(obj, new_profile, 'new_name', 'new_pass')

        self.assertFalse(res)
        mock_check.assert_has_calls([
            mock.call(obj, 'new_image', reason='update'),
            mock.call(obj, 'FAKE_IMAGE', reason='update')
        ])
        self.assertEqual(0, cc.server_rebuild.call_count)
        self.assertEqual(0, cc.wait_for_server.call_count)

    def test__update_image_failed_rebuilding(self):
        profile = server.ServerProfile('t', self.spec)
        cc = mock.Mock()
        cc.server_rebuild.side_effect = exc.InternalError(message='FAILED')
        profile._computeclient = cc
        x_old_image = mock.Mock(id='123')
        x_new_image = mock.Mock(id='456')
        x_images = [x_new_image, x_old_image]
        mock_check = self.patchobject(profile, '_validate_image',
                                      side_effect=x_images)
        obj = mock.Mock(physical_id='NOVA_ID')
        new_spec = copy.deepcopy(self.spec)
        new_spec['properties']['image'] = 'new_image'
        new_profile = server.ServerProfile('t1', new_spec)

        ex = self.assertRaises(exc.EResourceUpdate,
                               profile._update_image,
                               obj, new_profile, 'new_name', 'new_pass')

        self.assertEqual("Failed in updating server 'NOVA_ID': FAILED.",
                         six.text_type(ex))
        mock_check.assert_has_calls([
            mock.call(obj, 'new_image', reason='update'),
            mock.call(obj, 'FAKE_IMAGE', reason='update')
        ])
        cc.server_rebuild.assert_called_once_with(
            'NOVA_ID', '456', 'new_name', 'new_pass')
        self.assertEqual(0, cc.wait_for_server.call_count)

    def test__update_image_failed_waiting(self):
        profile = server.ServerProfile('t', self.spec)
        cc = mock.Mock()
        cc.wait_for_server.side_effect = exc.InternalError(message='TIMEOUT')
        profile._computeclient = cc
        x_old_image = mock.Mock(id='123')
        x_new_image = mock.Mock(id='456')
        x_images = [x_new_image, x_old_image]
        mock_check = self.patchobject(profile, '_validate_image',
                                      side_effect=x_images)
        obj = mock.Mock(physical_id='NOVA_ID')
        new_spec = copy.deepcopy(self.spec)
        new_spec['properties']['image'] = 'new_image'
        new_profile = server.ServerProfile('t1', new_spec)

        ex = self.assertRaises(exc.EResourceUpdate,
                               profile._update_image,
                               obj, new_profile, 'new_name', 'new_pass')

        self.assertEqual("Failed in updating server 'NOVA_ID': TIMEOUT.",
                         six.text_type(ex))
        mock_check.assert_has_calls([
            mock.call(obj, 'new_image', reason='update'),
            mock.call(obj, 'FAKE_IMAGE', reason='update')
        ])
        cc.server_rebuild.assert_called_once_with(
            'NOVA_ID', '456', 'new_name', 'new_pass')
        cc.wait_for_server.assert_called_once_with('NOVA_ID', 'ACTIVE')

    def test__create_interfaces(self):
        cc = mock.Mock()
        server_obj = mock.Mock()
        cc.server_get.return_value = server_obj
        profile = server.ServerProfile('t', self.spec)
        profile._computeclient = cc
        validation_results = [
            {'network': 'net1_id', 'fixed_ip': 'ip2'},
            {'network': 'net2_id'},
            {'port': 'port4'}
        ]
        mock_validate = self.patchobject(profile, '_validate_network',
                                         side_effect=validation_results)
        ports_results = [
            (mock.Mock(
                id='port1_id', network_id='net1_id',
                fixed_ips=[{'ip_address': 'ip2'}], security_group_ids=[]),
             None),
            (mock.Mock(
                id='port2_id', network_id='net2_id',
                fixed_ips=[{'ip_address': 'ip3'}], security_group_ids=[]),
             None),
            (mock.Mock(
                id='port4_id', network_id='net3_id',
                fixed_ips=[{'ip_address': 'ip4'}], security_group_ids=[]),
             None)
        ]
        mock_get_port = self.patchobject(profile, '_get_port',
                                         side_effect=ports_results)
        networks = [
            {'network': 'net1', 'port': None, 'fixed_ip': 'ip2'},
            {'network': 'net2', 'port': None, 'fixed_ip': None},
            {'network': None, 'port': 'port4', 'fixed_ip': None}
        ]
        obj = mock.Mock(physical_id='NOVA_ID', data={})

        res = profile._update_network_add_port(obj, networks)

        self.assertIsNone(res)
        cc.server_get.assert_called_with('NOVA_ID')
        validation_calls = [
            mock.call(obj,
                      {'network': 'net1', 'port': None, 'fixed_ip': 'ip2'},
                      'update'),
            mock.call(obj,
                      {'network': 'net2', 'port': None, 'fixed_ip': None},
                      'update'),
            mock.call(obj,
                      {'network': None, 'port': 'port4', 'fixed_ip': None},
                      'update')
        ]
        mock_validate.assert_has_calls(validation_calls)
        mock_get_port.assert_called_with(obj, {'port': 'port4'})
        create_calls = [
            mock.call(server_obj, port='port1_id'),
            mock.call(server_obj, port='port2_id'),
            mock.call(server_obj, port='port4_id'),
        ]
        cc.server_interface_create.assert_has_calls(create_calls)

    def test__create_interfaces_failed_getting_server(self):
        cc = mock.Mock()
        cc.server_get.side_effect = exc.InternalError(message='Not valid')
        profile = server.ServerProfile('t', self.spec)
        profile._computeclient = cc
        self.patchobject(profile, '_create_ports_from_properties')

        obj = mock.Mock(physical_id='NOVA_ID')
        networks = [{'foo': 'bar'}]  # not used

        ex = self.assertRaises(exc.EResourceUpdate,
                               profile._update_network_add_port,
                               obj, networks)

        self.assertEqual("Failed in updating server 'NOVA_ID': Not valid.",
                         six.text_type(ex))
        cc.server_get.assert_called_once_with('NOVA_ID')
        self.assertEqual(0, profile._create_ports_from_properties.call_count)

    def test__create_interfaces_failed_validation(self):
        cc = mock.Mock()
        server_obj = mock.Mock()
        cc.server_get.return_value = server_obj
        profile = server.ServerProfile('t', self.spec)
        profile._computeclient = cc
        err = exc.EResourceUpdate(type='server', id='NOVA_ID',
                                  message='Driver error')
        mock_validate = self.patchobject(profile, '_validate_network',
                                         side_effect=err)
        networks = [{'network': 'net1', 'port': None, 'fixed_ip': 'ip2'}]
        obj = mock.Mock(physical_id='NOVA_ID')

        ex = self.assertRaises(exc.EResourceUpdate,
                               profile._update_network_add_port,
                               obj, networks)

        self.assertEqual("Failed in updating server 'NOVA_ID': Driver error.",
                         six.text_type(ex))
        cc.server_get.assert_called_once_with('NOVA_ID')
        mock_validate.assert_called_once_with(obj, networks[0], 'update')
        self.assertEqual(0, cc.server_interface_create.call_count)

    def test__delete_interfaces(self):
        cc = mock.Mock()
        nc = mock.Mock()
        net1 = mock.Mock(id='net1')
        nc.network_get.return_value = net1
        nc.port_find.return_value = mock.Mock(id='port3', status='DOWN')
        profile = server.ServerProfile('t', self.spec)
        profile._computeclient = cc
        profile._networkclient = nc
        obj = mock.Mock(physical_id='NOVA_ID', data={'internal_ports': [
            {'id': 'port1', 'network_id': 'net1', 'remove': True,
             'fixed_ips': [{'ip_address': 'ip1'}]},
            {'id': 'port2', 'network_id': 'net1', 'remove': True,
             'fixed_ips': [{'ip_address': 'ip-random2'}]},
            {'id': 'port3', 'network_id': 'net1', 'remove': True,
             'fixed_ips': [{'ip_address': 'ip3'}]}]})
        networks = [
            {'network': 'net1', 'port': None, 'fixed_ip': 'ip1'},
            {'network': 'net1', 'port': None, 'fixed_ip': None},
            {'network': None, 'port': 'port3', 'fixed_ip': None}
        ]

        res = profile._update_network_remove_port(obj, networks)

        self.assertIsNone(res)

        nc.network_get.assert_has_calls([
            mock.call('net1'), mock.call('net1')
        ])
        cc.server_interface_delete.assert_has_calls([
            mock.call('port1', 'NOVA_ID'),
            mock.call('port2', 'NOVA_ID'),
            mock.call('port3', 'NOVA_ID'),
        ])
        nc.port_delete.assert_has_calls([
            mock.call('port1', ignore_missing=True),
            mock.call('port2', ignore_missing=True),
            mock.call('port3', ignore_missing=True),
        ])

    def test__delete_interfaces_failed_delete(self):
        cc = mock.Mock()
        profile = server.ServerProfile('t', self.spec)
        profile._computeclient = cc
        profile._networkclient = mock.Mock()
        candidate_ports = [
            [{'id': 'port1', 'network_id': 'net1',
             'fixed_ips': [{'ip_address': 'ip1'}]}],
        ]
        self.patchobject(profile, '_find_port_by_net_spec',
                         side_effect=candidate_ports)
        err = exc.InternalError(message='BANG')
        cc.server_interface_delete.side_effect = err
        internal_ports = [
            {'id': 'port1', 'remove': True}
        ]
        obj = mock.Mock(physical_id='NOVA_ID',
                        data={'internal_ports': internal_ports})
        networks = [
            {'network': 'net1', 'port': None, 'fixed_ip': 'ip1'},
        ]

        ex = self.assertRaises(exc.EResourceUpdate,
                               profile._update_network_remove_port,
                               obj, networks)

        self.assertEqual("Failed in updating server 'NOVA_ID': BANG.",
                         six.text_type(ex))
        cc.server_interface_delete.assert_called_once_with('port1', 'NOVA_ID')

    @mock.patch.object(server.ServerProfile, '_update_network_remove_port')
    @mock.patch.object(server.ServerProfile, '_update_network_add_port')
    def test__update_network(self, mock_create, mock_delete):
        obj = mock.Mock(physical_id='FAKE_ID')

        old_spec = copy.deepcopy(self.spec)
        old_spec['properties']['networks'] = [
            {'network': 'net1', 'fixed_ip': 'ip1'},
            {'network': 'net1'},
            {'port': 'port3'},
        ]
        profile = server.ServerProfile('t', old_spec)
        new_spec = copy.deepcopy(self.spec)
        new_spec['properties']['networks'] = [
            {'network': 'net1', 'fixed_ip': 'ip2'},
            {'network': 'net2'},
            {'port': 'port4'},
        ]
        new_profile = server.ServerProfile('t1', new_spec)

        res = profile._update_network(obj, new_profile)

        self.assertIsNone(res)

        networks_create = [
            {'floating_network': None, 'network': 'net1', 'fixed_ip': 'ip2',
             'floating_ip': None, 'port': None, 'security_groups': None},
            {'floating_network': None, 'network': 'net2', 'fixed_ip': None,
             'floating_ip': None, 'port': None, 'security_groups': None},
            {'floating_network': None, 'network': None, 'fixed_ip': None,
             'floating_ip': None, 'port': 'port4', 'security_groups': None}
        ]
        mock_create.assert_called_once_with(obj, networks_create)
        networks_delete = [
            {'floating_network': None, 'network': 'net1', 'fixed_ip': 'ip1',
             'floating_ip': None, 'port': None, 'security_groups': None},
            {'floating_network': None, 'network': 'net1', 'fixed_ip': None,
             'floating_ip': None, 'port': None, 'security_groups': None},
            {'floating_network': None, 'network': None, 'fixed_ip': None,
             'floating_ip': None, 'port': 'port3', 'security_groups': None}
        ]
        mock_delete.assert_called_once_with(obj, networks_delete)

    @mock.patch.object(server.ServerProfile, '_update_password')
    @mock.patch.object(server.ServerProfile, '_check_password')
    @mock.patch.object(server.ServerProfile, '_update_name')
    @mock.patch.object(server.ServerProfile, '_check_server_name')
    @mock.patch.object(server.ServerProfile, '_update_flavor')
    @mock.patch.object(server.ServerProfile, '_update_metadata')
    @mock.patch.object(server.ServerProfile, '_update_image')
    @mock.patch.object(server.ServerProfile, '_update_network')
    def test_do_update_name_succeeded(self, mock_update_network,
                                      mock_update_image, mock_update_metadata,
                                      mock_update_flavor, mock_check_name,
                                      mock_update_name, mock_check_password,
                                      mock_update_password):
        mock_check_name.return_value = True, 'NEW_NAME'
        mock_check_password.return_value = True, 'NEW_PASSWORD'
        mock_update_image.return_value = False
        obj = mock.Mock(physical_id='FAKE_ID')

        profile = server.ServerProfile('t', self.spec)
        profile._computeclient = mock.Mock()
        new_profile = server.ServerProfile('t', self.spec)

        res = profile.do_update(obj, new_profile)

        self.assertTrue(res)
        mock_check_name.assert_called_once_with(obj, new_profile)
        mock_update_metadata.assert_called_once_with(obj, new_profile)
        mock_update_image.assert_called_once_with(
            obj, new_profile, 'NEW_NAME', 'NEW_PASSWORD')
        mock_update_name.assert_called_once_with(obj, 'NEW_NAME')
        mock_update_password.assert_called_once_with(obj, 'NEW_PASSWORD')
        mock_update_flavor.assert_called_once_with(obj, new_profile)
        mock_update_network.assert_called_once_with(obj, new_profile)

    @mock.patch.object(server.ServerProfile, '_update_password')
    @mock.patch.object(server.ServerProfile, '_check_password')
    @mock.patch.object(server.ServerProfile, '_update_name')
    @mock.patch.object(server.ServerProfile, '_check_server_name')
    @mock.patch.object(server.ServerProfile, '_update_flavor')
    @mock.patch.object(server.ServerProfile, '_update_metadata')
    @mock.patch.object(server.ServerProfile, '_update_image')
    @mock.patch.object(server.ServerProfile, '_update_network')
    def test_do_update_name_no_change(self, mock_update_network,
                                      mock_update_image, mock_update_metadata,
                                      mock_update_flavor, mock_check_name,
                                      mock_update_name, mock_check_password,
                                      mock_update_password):
        mock_check_name.return_value = False, 'NEW_NAME'
        mock_check_password.return_value = False, 'OLD_PASS'
        obj = mock.Mock(physical_id='NOVA_ID')

        profile = server.ServerProfile('t', self.spec)
        profile._computeclient = mock.Mock()
        new_profile = server.ServerProfile('t', self.spec)

        res = profile.do_update(obj, new_profile)

        self.assertTrue(res)
        mock_check_name.assert_called_once_with(obj, new_profile)
        mock_check_password.assert_called_once_with(obj, new_profile)
        mock_update_image.assert_called_once_with(
            obj, new_profile, 'NEW_NAME', 'OLD_PASS')
        self.assertEqual(0, mock_update_name.call_count)
        self.assertEqual(0, mock_update_password.call_count)
        mock_update_flavor.assert_called_once_with(obj, new_profile)
        mock_update_network.assert_called_once_with(obj, new_profile)
        mock_update_metadata.assert_called_once_with(obj, new_profile)

    @mock.patch.object(server.ServerProfile, '_update_password')
    @mock.patch.object(server.ServerProfile, '_check_password')
    @mock.patch.object(server.ServerProfile, '_update_name')
    @mock.patch.object(server.ServerProfile, '_check_server_name')
    @mock.patch.object(server.ServerProfile, '_update_flavor')
    @mock.patch.object(server.ServerProfile, '_update_metadata')
    @mock.patch.object(server.ServerProfile, '_update_image')
    @mock.patch.object(server.ServerProfile, '_update_network')
    def test_do_update_name_failed(self, mock_update_network,
                                   mock_update_image, mock_update_metadata,
                                   mock_update_flavor, mock_check_name,
                                   mock_update_name, mock_check_password,
                                   mock_update_password):
        mock_check_name.return_value = True, 'NEW_NAME'
        mock_check_password.return_value = False, 'OLD_PASS'
        mock_update_image.return_value = False
        err = exc.EResourceUpdate(type='server', id='NOVA_ID', message='BANG')
        mock_update_name.side_effect = err
        obj = mock.Mock(physical_id='NOVA_ID')

        profile = server.ServerProfile('t', self.spec)
        profile._computeclient = mock.Mock()
        new_profile = server.ServerProfile('t', self.spec)

        ex = self.assertRaises(exc.EResourceUpdate,
                               profile.do_update,
                               obj, new_profile)

        self.assertEqual("Failed in updating server 'NOVA_ID': BANG.",
                         six.text_type(ex))
        mock_check_name.assert_called_once_with(obj, new_profile)
        mock_check_password.assert_called_once_with(obj, new_profile)
        mock_update_image.assert_called_once_with(
            obj, new_profile, 'NEW_NAME', 'OLD_PASS')
        mock_update_name.assert_called_once_with(obj, 'NEW_NAME')
        self.assertEqual(0, mock_update_password.call_count)
        self.assertEqual(0, mock_update_flavor.call_count)
        self.assertEqual(0, mock_update_metadata.call_count)

    @mock.patch.object(server.ServerProfile, '_update_password')
    @mock.patch.object(server.ServerProfile, '_update_name')
    @mock.patch.object(server.ServerProfile, '_check_password')
    @mock.patch.object(server.ServerProfile, '_check_server_name')
    @mock.patch.object(server.ServerProfile, '_update_flavor')
    @mock.patch.object(server.ServerProfile, '_update_image')
    def test_do_update_image_succeeded(self, mock_update_image,
                                       mock_update_flavor, mock_check_name,
                                       mock_check_password, mock_update_name,
                                       mock_update_password):
        mock_check_name.return_value = False, 'OLD_NAME'
        mock_check_password.return_value = False, 'OLD_PASS'
        mock_update_image.return_value = True
        obj = mock.Mock()
        obj.physical_id = 'FAKE_ID'

        profile = server.ServerProfile('t', self.spec)
        profile._computeclient = mock.Mock()
        new_spec = copy.deepcopy(self.spec)
        new_spec['properties']['image'] = 'FAKE_IMAGE_NEW'
        new_profile = server.ServerProfile('t', new_spec)

        res = profile.do_update(obj, new_profile)

        self.assertTrue(res)
        mock_update_image.assert_called_with(
            obj, new_profile, 'OLD_NAME', 'OLD_PASS')
        self.assertEqual(0, mock_update_name.call_count)
        self.assertEqual(0, mock_update_password.call_count)

    @mock.patch.object(server.ServerProfile, '_update_flavor')
    @mock.patch.object(server.ServerProfile, '_update_name')
    @mock.patch.object(server.ServerProfile, '_update_metadata')
    @mock.patch.object(server.ServerProfile, '_update_image')
    @mock.patch.object(server.ServerProfile, '_check_password')
    @mock.patch.object(server.ServerProfile, '_check_server_name')
    def test_do_update_image_failed(self, mock_check_name, mock_check_password,
                                    mock_update_image, mock_update_meta,
                                    mock_update_name, mock_update_flavor):
        mock_check_name.return_value = False, 'OLD_NAME'
        mock_check_password.return_value = False, 'OLD_PASS'
        # _update_image always throw EResourceUpdate
        ex = exc.EResourceUpdate(type='server', id='NOVA_ID',
                                 message='Image Not Found')
        mock_update_image.side_effect = ex
        obj = mock.Mock(physical_id='NOVA_ID')

        profile = server.ServerProfile('t', self.spec)
        profile._computeclient = mock.Mock()
        # don't need to invent a new spec
        new_spec = copy.deepcopy(self.spec)
        new_profile = server.ServerProfile('t', new_spec)

        ex = self.assertRaises(exc.EResourceUpdate,
                               profile.do_update,
                               obj, new_profile)

        mock_update_image.assert_called_with(
            obj, new_profile, 'OLD_NAME', 'OLD_PASS')
        self.assertEqual("Failed in updating server 'NOVA_ID': "
                         "Image Not Found.", six.text_type(ex))

    @mock.patch.object(server.ServerProfile, '_update_flavor')
    def test_do_update_update_flavor_succeeded(self, mock_update_flavor):
        obj = mock.Mock(physical_id='FAKE_ID')
        profile = server.ServerProfile('t', self.spec)
        profile._computeclient = mock.Mock()
        new_spec = copy.deepcopy(self.spec)
        new_spec['properties']['flavor'] = 'FAKE_FLAVOR_NEW'
        new_profile = server.ServerProfile('t', new_spec)

        res = profile.do_update(obj, new_profile)
        self.assertTrue(res)
        mock_update_flavor.assert_called_with(obj, new_profile)

    @mock.patch.object(server.ServerProfile, '_update_flavor')
    def test_do_update_update_flavor_failed(self, mock_update_flavor):
        ex = exc.EResourceUpdate(type='server', id='NOVA_ID',
                                 message='Flavor Not Found')
        mock_update_flavor.side_effect = ex
        obj = mock.Mock(physical_id='NOVA_ID')
        profile = server.ServerProfile('t', self.spec)
        profile._computeclient = mock.Mock()
        new_spec = copy.deepcopy(self.spec)
        new_spec['properties']['flavor'] = 'FAKE_FLAVOR_NEW'
        new_profile = server.ServerProfile('t', new_spec)

        ex = self.assertRaises(exc.EResourceUpdate,
                               profile.do_update,
                               obj, new_profile)

        mock_update_flavor.assert_called_with(obj, new_profile)
        self.assertEqual("Failed in updating server 'NOVA_ID': "
                         "Flavor Not Found.",
                         six.text_type(ex))

    @mock.patch.object(server.ServerProfile, '_update_flavor')
    @mock.patch.object(server.ServerProfile, '_update_network')
    def test_do_update_update_network_succeeded(
            self, mock_update_network, mock_update_flavor):
        mock_update_network.return_value = True
        profile = server.ServerProfile('t', self.spec)
        profile._computeclient = mock.Mock()

        obj = mock.Mock(physical_id='NOVA_ID')

        new_spec = copy.deepcopy(self.spec)
        new_spec['properties']['networks'] = [
            {'network': 'new_net', 'port': 'new_port', 'fixed_ip': 'new-ip'}
        ]
        new_profile = server.ServerProfile('t', new_spec)

        res = profile.do_update(obj, new_profile)
        self.assertTrue(res)
        mock_update_network.assert_called_with(obj, new_profile)

    @mock.patch.object(server.ServerProfile, '_update_password')
    @mock.patch.object(server.ServerProfile, '_check_password')
    @mock.patch.object(server.ServerProfile, '_update_name')
    @mock.patch.object(server.ServerProfile, '_check_server_name')
    @mock.patch.object(server.ServerProfile, '_update_flavor')
    @mock.patch.object(server.ServerProfile, '_update_metadata')
    @mock.patch.object(server.ServerProfile, '_update_image')
    @mock.patch.object(server.ServerProfile, '_update_network')
    def test_do_update_update_network_failed(
            self, mock_update_network, mock_update_image, mock_update_metadata,
            mock_update_flavor, mock_check_name, mock_update_name,
            mock_check_password, mock_update_password):

        mock_check_name.return_value = True, 'NEW_NAME'
        mock_check_password.return_value = True, 'NEW_PASSWORD'
        mock_update_image.return_value = True
        err = exc.EResourceUpdate(type='server', id='NOVA_ID', message='BOOM')
        mock_update_network.side_effect = err

        profile = server.ServerProfile('t', self.spec)
        profile._computeclient = mock.Mock()
        new_network = {
            'port': 'FAKE_PORT_NEW',
            'fixed_ip': 'FAKE_IP_NEW',
            'network': 'FAKE_NET_NEW',
        }
        new_spec = copy.deepcopy(self.spec)
        new_spec['properties']['networks'] = [new_network]
        new_profile = server.ServerProfile('t', new_spec)
        obj = mock.Mock(physical_id='NOVA_ID')

        ex = self.assertRaises(exc.EResourceUpdate,
                               profile.do_update,
                               obj, new_profile)

        self.assertEqual("Failed in updating server 'NOVA_ID': BOOM.",
                         six.text_type(ex))
        mock_check_name.assert_called_once_with(obj, new_profile)
        mock_check_password.assert_called_once_with(obj, new_profile)
        mock_update_image.assert_called_once_with(
            obj, new_profile, 'NEW_NAME', 'NEW_PASSWORD')
        self.assertEqual(0, mock_update_name.call_count)
        self.assertEqual(0, mock_update_password.call_count)
        mock_update_flavor.assert_called_once_with(obj, new_profile)
        mock_update_network.assert_called_with(obj, new_profile)
        self.assertEqual(0, mock_update_metadata.call_count)

    def test_do_update_without_profile(self):
        profile = server.ServerProfile('t', self.spec)
        obj = mock.Mock()
        obj.physical_id = 'FAKE_ID'
        new_profile = None
        res = profile.do_update(obj, new_profile)
        self.assertFalse(res)

    def test_do_update_no_physical_id(self):
        profile = server.ServerProfile('t', self.spec)
        profile._computeclient = mock.Mock()
        node_obj = mock.Mock(physical_id=None)
        new_profile = mock.Mock()

        # Test path where server doesn't exist
        res = profile.do_update(node_obj, new_profile)

        self.assertFalse(res)
