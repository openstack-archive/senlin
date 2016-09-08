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
from senlin.profiles.os.nova import server
from senlin.tests.unit.common import base
from senlin.tests.unit.common import utils

spec = {
    'type': 'os.nova.server',
    'version': '1.0',
    'properties': {
        'context': {},
        'auto_disk_config': True,
        'availability_zone': 'FAKE_AZ',
        'block_device_mapping': [{
            'device_name': 'FAKE_NAME',
            'volume_size': 1000,
        }],
        'flavor': 'FLAV',
        'image': 'FAKE_IMAGE',
        'key_name': 'FAKE_KEYNAME',
        "metadata": {"meta var": "meta val"},
        'name': 'FAKE_SERVER_NAME',
        'networks': [{
            'port': 'FAKE_PORT',
            'fixed-ip': 'FAKE_IP',
            'network': 'FAKE_NET',
        }],
        'scheduler_hints': {
            'same_host': 'HOST_ID',
        },
    }
}


class TestAvailabilityZoneValidation(base.SenlinTestCase):

    scenarios = [
        ('validate:success', dict(
            reason=None,
            success=True,
            validate_result=[['FAKE_AZ']],
            result='FAKE_AZ',
            exception=None,
            message='')),
        ('validate:driver_failure', dict(
            reason=None,
            success=False,
            validate_result=exc.InternalError(message='BANG.'),
            result='FAKE_AZ',
            exception=exc.InternalError,
            message='BANG.')),
        ('validate:not_found', dict(
            reason=None,
            success=False,
            validate_result=[[]],
            result='FAKE_AZ',
            exception=exc.InvalidSpec,
            message=("The specified availability_zone 'FAKE_AZ' could "
                     "not be found"))),
        ('create:success', dict(
            reason='create',
            success=True,
            validate_result=[['FAKE_AZ']],
            result='FAKE_AZ',
            exception=None,
            message='')),
        ('create:driver_failure', dict(
            reason='create',
            success=False,
            validate_result=exc.InternalError(message='BANG'),
            result='FAKE_AZ',
            exception=exc.EResourceCreation,
            message='Failed in creating server: BANG.')),
        ('create:not_found', dict(
            reason='create',
            success=False,
            validate_result=[[]],
            result='FAKE_AZ',
            exception=exc.EResourceCreation,
            message=("Failed in creating server: The specified "
                     "availability_zone 'FAKE_AZ' could not be found.")))
    ]

    def setUp(self):
        super(TestAvailabilityZoneValidation, self).setUp()

        self.cc = mock.Mock()
        prof = server.ServerProfile('t', spec)
        prof._computeclient = self.cc
        self.profile = prof

    def test_validation(self):
        self.cc.validate_azs.side_effect = self.validate_result
        node = mock.Mock(id='NODE_ID')

        if self.success:
            res = self.profile._validate_az(node, 'FAKE_AZ', self.reason)
            self.assertEqual(self.result, res)
        else:
            ex = self.assertRaises(self.exception,
                                   self.profile._validate_az,
                                   node, 'FAKE_AZ', self.reason)
            self.assertEqual(self.message, six.text_type(ex))

        self.cc.validate_azs.assert_called_once_with(['FAKE_AZ'])


class TestFlavorValidation(base.SenlinTestCase):

    scenarios = [
        ('validate:success', dict(
            reason=None,
            success=True,
            validate_result=[mock.Mock(id='FID', is_disabled=False)],
            result='FID',
            exception=None,
            message='')),
        ('validate:driver_failure', dict(
            reason=None,
            success=False,
            validate_result=exc.InternalError(message='BANG.'),
            result='FID',
            exception=exc.InternalError,
            message='BANG.')),
        ('validate:not_found', dict(
            reason=None,
            success=False,
            validate_result=exc.InternalError(code=404, message='BANG.'),
            result='FID',
            exception=exc.InvalidSpec,
            message="The specified flavor 'FLAVOR' could not be found.")),
        ('validate:disabled', dict(
            reason=None,
            success=False,
            validate_result=[mock.Mock(id='FID', is_disabled=True)],
            result='FID',
            exception=exc.InvalidSpec,
            message="The specified flavor 'FLAVOR' is disabled")),
        ('create:success', dict(
            reason='create',
            success=True,
            validate_result=[mock.Mock(id='FID', is_disabled=False)],
            result='FID',
            exception=None,
            message='')),
        ('create:driver_failure', dict(
            reason='create',
            success=False,
            validate_result=exc.InternalError(message='BANG'),
            result='FID',
            exception=exc.EResourceCreation,
            message='Failed in creating server: BANG.')),
        ('create:not_found', dict(
            reason='create',
            success=False,
            validate_result=exc.InternalError(code=404, message='BANG'),
            result='FID',
            exception=exc.EResourceCreation,
            message="Failed in creating server: BANG.")),
        ('create:disabled', dict(
            reason='create',
            success=False,
            validate_result=[mock.Mock(id='FID', is_disabled=True)],
            result='FID',
            exception=exc.EResourceCreation,
            message=("Failed in creating server: The specified flavor "
                     "'FLAVOR' is disabled."))),
        ('update:success', dict(
            reason='update',
            success=True,
            validate_result=[mock.Mock(id='FID', is_disabled=False)],
            result='FID',
            exception=None,
            message='')),
        ('update:driver_failure', dict(
            reason='update',
            success=False,
            validate_result=exc.InternalError(message='BANG'),
            result='FID',
            exception=exc.EResourceUpdate,
            message='Failed in updating server NOVA_ID: BANG.')),
        ('update:not_found', dict(
            reason='update',
            success=False,
            validate_result=exc.InternalError(code=404, message='BANG'),
            result='FID',
            exception=exc.EResourceUpdate,
            message="Failed in updating server NOVA_ID: BANG.")),
        ('update:disabled', dict(
            reason='update',
            success=False,
            validate_result=[mock.Mock(id='FID', is_disabled=True)],
            result='FID',
            exception=exc.EResourceUpdate,
            message=("Failed in updating server NOVA_ID: The specified "
                     "flavor 'FLAVOR' is disabled.")))
    ]

    def setUp(self):
        super(TestFlavorValidation, self).setUp()

        self.cc = mock.Mock()
        self.profile = server.ServerProfile('t', spec)
        self.profile._computeclient = self.cc

    def test_validation(self):
        self.cc.flavor_find.side_effect = self.validate_result
        node = mock.Mock(id='NODE_ID', physical_id='NOVA_ID')
        flavor = 'FLAVOR'

        if self.success:
            res = self.profile._validate_flavor(node, flavor, self.reason)
            self.assertIsNotNone(res)
            self.assertEqual(self.result, res.id)
        else:
            ex = self.assertRaises(self.exception,
                                   self.profile._validate_flavor,
                                   node, flavor, self.reason)
            self.assertEqual(self.message, six.text_type(ex))

        self.cc.flavor_find.assert_called_once_with(flavor, False)


class TestImageValidation(base.SenlinTestCase):

    scenarios = [
        ('validate:success', dict(
            reason=None,
            success=True,
            validate_result=[mock.Mock(id='IMAGE_ID')],
            result='IMAGE_ID',
            exception=None,
            message='')),
        ('validate:driver_failure', dict(
            reason=None,
            success=False,
            validate_result=exc.InternalError(message='BANG.'),
            result='FID',
            exception=exc.InternalError,
            message='BANG.')),
        ('validate:not_found', dict(
            reason=None,
            success=False,
            validate_result=exc.InternalError(code=404, message='BANG.'),
            result='FID',
            exception=exc.InvalidSpec,
            message="The specified image 'IMAGE' could not be found.")),
        ('create:success', dict(
            reason='create',
            success=True,
            validate_result=[mock.Mock(id='IMAGE_ID')],
            result='IMAGE_ID',
            exception=None,
            message='')),
        ('create:driver_failure', dict(
            reason='create',
            success=False,
            validate_result=exc.InternalError(message='BANG'),
            result='FID',
            exception=exc.EResourceCreation,
            message='Failed in creating server: BANG.')),
        ('create:not_found', dict(
            reason='create',
            success=False,
            validate_result=exc.InternalError(code=404, message='BANG'),
            result='FID',
            exception=exc.EResourceCreation,
            message="Failed in creating server: BANG.")),
        ('update:success', dict(
            reason='update',
            success=True,
            validate_result=[mock.Mock(id='IMAGE_ID')],
            result='IMAGE_ID',
            exception=None,
            message='')),
        ('update:driver_failure', dict(
            reason='update',
            success=False,
            validate_result=exc.InternalError(message='BANG'),
            result='FID',
            exception=exc.EResourceUpdate,
            message='Failed in updating server NOVA_ID: BANG.')),
        ('update:not_found', dict(
            reason='update',
            success=False,
            validate_result=exc.InternalError(code=404, message='BANG'),
            result='FID',
            exception=exc.EResourceUpdate,
            message="Failed in updating server NOVA_ID: BANG.")),
    ]

    def setUp(self):
        super(TestImageValidation, self).setUp()

        self.cc = mock.Mock()
        self.profile = server.ServerProfile('t', spec)
        self.profile._computeclient = self.cc

    def test_validation(self):
        self.cc.image_find.side_effect = self.validate_result
        node = mock.Mock(id='NODE_ID', physical_id='NOVA_ID')
        image = 'IMAGE'

        if self.success:
            res = self.profile._validate_image(node, image, self.reason)
            self.assertIsNotNone(res)
            self.assertEqual(self.result, res.id)
        else:
            ex = self.assertRaises(self.exception,
                                   self.profile._validate_image,
                                   node, image, self.reason)
            self.assertEqual(self.message, six.text_type(ex))

        self.cc.image_find.assert_called_once_with(image, False)


class TestKeypairValidation(base.SenlinTestCase):

    scenarios = [
        ('validate:success', dict(
            reason=None,
            success=True,
            validate_result=[mock.Mock(id='KEY_ID')],
            result='KEY_ID',
            exception=None,
            message='')),
        ('validate:driver_failure', dict(
            reason=None,
            success=False,
            validate_result=exc.InternalError(message='BANG.'),
            result='FID',
            exception=exc.InternalError,
            message='BANG.')),
        ('validate:not_found', dict(
            reason=None,
            success=False,
            validate_result=exc.InternalError(code=404, message='BANG.'),
            result='FID',
            exception=exc.InvalidSpec,
            message="The specified key_name 'KEY' could not be found.")),
        ('create:success', dict(
            reason='create',
            success=True,
            validate_result=[mock.Mock(id='IMAGE_ID')],
            result='IMAGE_ID',
            exception=None,
            message='')),
        ('create:driver_failure', dict(
            reason='create',
            success=False,
            validate_result=exc.InternalError(message='BANG'),
            result='FID',
            exception=exc.EResourceCreation,
            message='Failed in creating server: BANG.')),
        ('create:not_found', dict(
            reason='create',
            success=False,
            validate_result=exc.InternalError(code=404, message='BANG'),
            result='FID',
            exception=exc.EResourceCreation,
            message="Failed in creating server: BANG.")),
        ('update:success', dict(
            reason='update',
            success=True,
            validate_result=[mock.Mock(id='KEY_ID')],
            result='KEY_ID',
            exception=None,
            message='')),
        ('update:driver_failure', dict(
            reason='update',
            success=False,
            validate_result=exc.InternalError(message='BANG'),
            result='FID',
            exception=exc.EResourceUpdate,
            message='Failed in updating server NOVA_ID: BANG.')),
        ('update:not_found', dict(
            reason='update',
            success=False,
            validate_result=exc.InternalError(code=404, message='BANG'),
            result='FID',
            exception=exc.EResourceUpdate,
            message="Failed in updating server NOVA_ID: BANG.")),
    ]

    def setUp(self):
        super(TestKeypairValidation, self).setUp()

        self.cc = mock.Mock()
        self.profile = server.ServerProfile('t', spec)
        self.profile._computeclient = self.cc

    def test_validation(self):
        self.cc.keypair_find.side_effect = self.validate_result
        node = mock.Mock(id='NODE_ID', physical_id='NOVA_ID')
        key = 'KEY'

        if self.success:
            res = self.profile._validate_keypair(node, key, self.reason)
            self.assertIsNotNone(res)
            self.assertEqual(self.result, res.id)
        else:
            ex = self.assertRaises(self.exception,
                                   self.profile._validate_keypair,
                                   node, key, self.reason)
            self.assertEqual(self.message, six.text_type(ex))

        self.cc.keypair_find.assert_called_once_with(key, False)


class TestNovaServerValidate(base.SenlinTestCase):

    def setUp(self):
        super(TestNovaServerValidate, self).setUp()

        self.context = utils.dummy_context()

    def test__validate_bdm(self):
        profile = server.ServerProfile('t', spec)

        res = profile._validate_bdm()

        self.assertIsNone(res)

    def test__validate_bdm_both_specified_validate(self):
        new_spec = copy.deepcopy(spec)
        new_spec['properties']['block_device_mapping_v2'] = [{
            'source_type': 'XTYPE',
            'destination_type': 'YTYPE',
            'volume_size': 10
        }]
        profile = server.ServerProfile('t', new_spec)

        ex = self.assertRaises(exc.InvalidSpec,
                               profile._validate_bdm)

        self.assertEqual("Only one of 'block_device_mapping' or "
                         "'block_device_mapping_v2' can be specified, "
                         "not both", six.text_type(ex))

    def test__validate_bdm_both_specified_create(self):
        new_spec = copy.deepcopy(spec)
        new_spec['properties']['block_device_mapping_v2'] = [{
            'source_type': 'XTYPE',
            'destination_type': 'YTYPE',
            'volume_size': 10
        }]
        profile = server.ServerProfile('t', new_spec)

        ex = self.assertRaises(exc.EResourceCreation,
                               profile._validate_bdm,
                               'create')

        self.assertEqual("Failed in creating server: Only one of "
                         "'block_device_mapping' or 'block_device_mapping_v2'"
                         " can be specified, not both.",
                         six.text_type(ex))

    def test__validate_network(self):
        nc = mock.Mock()
        nc.network_get.return_value = mock.Mock(id='NET_ID')
        profile = server.ServerProfile('t', spec)
        profile._networkclient = nc
        networks = [{'network': 'NET_NAME', 'port': None, 'fixed-ip': None}]

        res = profile._validate_network(mock.Mock(), networks)

        self.assertEqual([{'uuid': 'NET_ID'}], res)
        nc.network_get.assert_called_once_with('NET_NAME')

    def test__validate_network_port_fixed_ip_preserved(self):
        nc = mock.Mock()
        profile = server.ServerProfile('t', spec)
        profile._networkclient = nc
        networks = [{'port': 'PORT_ID', 'fixed-ip': 'FIXED_IP'}]

        res = profile._validate_network(mock.Mock(), networks)

        self.assertEqual([{'port': 'PORT_ID', 'fixed-ip': 'FIXED_IP'}], res)
        self.assertEqual(0, nc.network_get.call_count)

    def test__validate_network_driver_error(self):
        nc = mock.Mock()
        nc.network_get.side_effect = exc.InternalError(message='BOOM')
        profile = server.ServerProfile('t', spec)
        profile._networkclient = nc
        networks = [{'network': 'NET_NAME', 'port': None, 'fixed-ip': None}]

        ex = self.assertRaises(exc.EResourceCreation,
                               profile._validate_network,
                               mock.Mock(), networks)

        self.assertEqual('Failed in creating server: BOOM.',
                         six.text_type(ex))
        nc.network_get.assert_called_once_with('NET_NAME')

    def test_do_validate_all_passed(self):
        profile = server.ServerProfile('t', spec)
        cc = mock.Mock()
        cc.validate_azs.return_value = ['FAKE_AZ']
        x_flavor = mock.Mock(is_disabled=False, id='FLAV')
        cc.flavor_find.return_value = x_flavor
        x_image = mock.Mock()
        cc.image_find.return_value = x_image
        x_key = mock.Mock()
        cc.keypair_find.return_value = x_key
        profile._computeclient = cc

        res = profile.do_validate(mock.Mock())

        self.assertTrue(res)
        cc.validate_azs.assert_called_once_with(['FAKE_AZ'])
        cc.flavor_find.assert_called_once_with('FLAV', False)
        cc.image_find.assert_called_once_with('FAKE_IMAGE', False)
        cc.keypair_find.assert_called_once_with('FAKE_KEYNAME', False)
