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
            'floating_ip': 'FAKE_FLOATING_IP',
            'floating_network': 'FAKE_FLOATING_NET',
            'security_groups': ['FAKE_SECURITY_GROUP'],
            'port': 'FAKE_PORT',
            'fixed_ip': 'FAKE_IP',
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
            message="Failed in updating server 'NOVA_ID': BANG.")),
        ('update:not_found', dict(
            reason='update',
            success=False,
            validate_result=exc.InternalError(code=404, message='BANG'),
            result='FID',
            exception=exc.EResourceUpdate,
            message="Failed in updating server 'NOVA_ID': BANG.")),
        ('update:disabled', dict(
            reason='update',
            success=False,
            validate_result=[mock.Mock(id='FID', is_disabled=True)],
            result='FID',
            exception=exc.EResourceUpdate,
            message=("Failed in updating server 'NOVA_ID': The specified "
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
            message="Failed in updating server 'NOVA_ID': BANG.")),
        ('update:not_found', dict(
            reason='update',
            success=False,
            validate_result=exc.InternalError(code=404, message='BANG'),
            result='FID',
            exception=exc.EResourceUpdate,
            message="Failed in updating server 'NOVA_ID': BANG.")),
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
            message="Failed in updating server 'NOVA_ID': BANG.")),
        ('update:not_found', dict(
            reason='update',
            success=False,
            validate_result=exc.InternalError(code=404, message='BANG'),
            result='FID',
            exception=exc.EResourceUpdate,
            message="Failed in updating server 'NOVA_ID': BANG.")),
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


class TestNetworkValidation(base.SenlinTestCase):

    scenarios = [
        ('validate:net-n:port-n:fixed_ip-n:sgroups-n', dict(
            reason=None,
            success=True,
            inputs={'port': 'PORT'},
            net_result=[],
            port_result=[mock.Mock(id='PORT_ID', status='DOWN')],
            sg_result=[],
            floating_result=[],
            result={'port': 'PORT_ID'},
            exception=None,
            message='')),
        ('validate:net-y:port-n:fixed_ip-n:sgroups-y', dict(
            reason=None,
            success=True,
            inputs={'network': 'NET', 'security_groups': ['default']},
            net_result=[mock.Mock(id='NET_ID')],
            port_result=[],
            sg_result=[mock.Mock(id='SG_ID')],
            floating_result=[],
            result={'network': 'NET_ID', 'security_groups': ['SG_ID']},
            exception=None,
            message='')),
        ('validate:net-y:port-n:fixed_ip-n:sgroups-n:floating_net-y', dict(
            reason=None,
            success=True,
            inputs={'network': 'NET', 'floating_network': 'NET'},
            net_result=[mock.Mock(id='NET_ID'), mock.Mock(id='NET_ID')],
            port_result=[],
            sg_result=[],
            floating_result=[],
            result={'network': 'NET_ID', 'floating_network': 'NET_ID'},
            exception=None,
            message='')),
        ('validate:net-y:port-n:fixed_ip-n:floating_net-y:floating_ip-y', dict(
            reason=None,
            success=True,
            inputs={'network': 'NET', 'floating_network': 'NET',
                    'floating_ip': 'FLOATINGIP'},
            net_result=[mock.Mock(id='NET_ID'), mock.Mock(id='NET_ID')],
            port_result=[],
            sg_result=[],
            floating_result=[mock.Mock(id='FLOATINGIP_ID', status='INACTIVE')],
            result={'network': 'NET_ID', 'floating_network': 'NET_ID',
                    'floating_ip_id': 'FLOATINGIP_ID',
                    'floating_ip': 'FLOATINGIP'},
            exception=None,
            message='')),
        ('validate:net-y:port-n:fixed_ip-y:sgroups-n', dict(
            reason=None,
            success=True,
            inputs={'network': 'NET', 'fixed_ip': 'FIXED_IP'},
            net_result=[mock.Mock(id='NET_ID')],
            port_result=[],
            sg_result=[],
            floating_result=[],
            result={'network': 'NET_ID', 'fixed_ip': 'FIXED_IP'},
            exception=None,
            message='')),
        ('validate:net-f:port-y:fixed_ip-n:sgroups-n', dict(
            reason=None,
            success=False,
            inputs={'network': 'NET', 'port': 'PORT'},
            net_result=[exc.InternalError(message='NET Failure')],
            port_result=[],
            sg_result=[],
            floating_result=[],
            result={},
            exception=exc.InvalidSpec,
            message='NET Failure')),
        ('validate:net-n:port-f:fixed_ip-n', dict(
            reason=None,
            success=False,
            inputs={'port': 'PORT'},
            net_result=[],
            port_result=[exc.InternalError(message='PORT Failure')],
            sg_result=[],
            floating_result=[],
            result={},
            exception=exc.InvalidSpec,
            message='PORT Failure')),
        ('validate:net-n:port-active:fixed_ip-n', dict(
            reason=None,
            success=False,
            inputs={'port': 'PORT'},
            net_result=[],
            port_result=[mock.Mock(id='PORT_ID', status='ACTIVE')],
            sg_result=[],
            floating_result=[],
            result={},
            exception=exc.InvalidSpec,
            message='The status of the port PORT must be DOWN')),
        ('validate:net-n:port-y:fixed_ip-n:floating_net-n:floating_ip-y', dict(
            reason=None,
            success=False,
            inputs={'port': 'PORT', 'floating_ip': 'FLOATINGIP'},
            net_result=[],
            port_result=[mock.Mock(id='PORT_ID', status='DOWN')],
            sg_result=[],
            floating_result=[mock.Mock(id='FLOATINGIP_ID', status='INACTIVE')],
            result={},
            exception=exc.InvalidSpec,
            message='Must specify a network to create floating IP')),
        ('validate:net-n:port-y:fixed_ip-n:floating_ip-active', dict(
            reason=None,
            success=False,
            inputs={'port': 'PORT', 'floating_network': 'NET',
                    'floating_ip': 'FLOATINGIP'},
            net_result=[mock.Mock(id='NET_ID')],
            port_result=[mock.Mock(id='PORT_ID', status='DOWN')],
            sg_result=[],
            floating_result=[mock.Mock(id='FLOATINGIP_ID', status='ACTIVE')],
            result={},
            exception=exc.InvalidSpec,
            message='the floating IP FLOATINGIP has been used.')),
        ('validate:net-n:port-n:fixed_ip-n', dict(
            reason=None,
            success=False,
            inputs={'fixed_ip': 'FIXED_IP'},
            net_result=[],
            port_result=[],
            sg_result=[],
            floating_result=[],
            result={},
            exception=exc.InvalidSpec,
            message="One of 'port' and 'network' must be provided")),
        ('validate:net-n:port-y:fixed_ip-y', dict(
            reason=None,
            success=False,
            inputs={'port': 'PORT', 'fixed_ip': 'FIXED_IP'},
            net_result=[],
            port_result=[mock.Mock(id='PORT_ID', status='DOWN')],
            sg_result=[],
            floating_result=[],
            result={},
            exception=exc.InvalidSpec,
            message=("The 'port' property and the 'fixed_ip' property cannot "
                     "be specified at the same time"))),
        ('create:net-y:port-y:fixed_ip-n', dict(
            reason='create',
            success=True,
            inputs={'network': 'NET', 'port': 'PORT'},
            net_result=[mock.Mock(id='NET_ID')],
            port_result=[mock.Mock(id='PORT_ID', status='DOWN')],
            sg_result=[],
            floating_result=[],
            result={'network': 'NET_ID', 'port': 'PORT_ID'},
            exception=None,
            message='')),
        ('create:net-y:port-n:fixed_ip-y', dict(
            reason='create',
            success=True,
            inputs={'network': 'NET', 'fixed_ip': 'FIXED_IP'},
            net_result=[mock.Mock(id='NET_ID')],
            port_result=[],
            sg_result=[],
            floating_result=[],
            result={'network': 'NET_ID', 'fixed_ip': 'FIXED_IP'},
            exception=None,
            message='')),
        ('create:net-y:port-n:fixed_ip-n:sgroups-y', dict(
            reason='create',
            success=True,
            inputs={'network': 'NET', 'security_groups': ['default']},
            net_result=[mock.Mock(id='NET_ID')],
            port_result=[],
            sg_result=[mock.Mock(id='SG_ID')],
            floating_result=[],
            result={'network': 'NET_ID', 'security_groups': ['SG_ID']},
            exception=None,
            message='')),
        ('create:net-y:port-n:fixed_ip-n:sgroups-n:floating_net-y', dict(
            reason=None,
            success=True,
            inputs={'network': 'NET', 'floating_network': 'NET'},
            net_result=[mock.Mock(id='NET_ID'), mock.Mock(id='NET_ID')],
            port_result=[],
            sg_result=[],
            floating_result=[],
            result={'network': 'NET_ID', 'floating_network': 'NET_ID'},
            exception=None,
            message='')),
        ('create:net-f:port-y:fixed_ip-n', dict(
            reason='create',
            success=False,
            inputs={'network': 'NET', 'port': 'PORT'},
            net_result=[exc.InternalError(message='NET Failure')],
            port_result=[],
            sg_result=[],
            floating_result=[],
            result={},
            exception=exc.EResourceCreation,
            message='Failed in creating server: NET Failure.')),
        ('create:net-n:port-f:fixed_ip-n', dict(
            reason='create',
            success=False,
            inputs={'port': 'PORT'},
            net_result=[],
            port_result=[exc.InternalError(message='PORT Failure')],
            sg_result=[],
            floating_result=[],
            result={},
            exception=exc.EResourceCreation,
            message='Failed in creating server: PORT Failure.')),
        ('create:net-n:port-active:fixed_ip-n', dict(
            reason='create',
            success=False,
            inputs={'port': 'PORT'},
            net_result=[],
            port_result=[mock.Mock(id='PORT_ID', status='ACTIVE')],
            sg_result=[],
            floating_result=[],
            result={},
            exception=exc.EResourceCreation,
            message=('Failed in creating server: The status of the port PORT '
                     'must be DOWN.'))),
        ('create:net-n:port-n:fixed_ip-n', dict(
            reason='create',
            success=False,
            inputs={'fixed_ip': 'FIXED_IP'},
            net_result=[],
            port_result=[],
            sg_result=[],
            floating_result=[],
            result={},
            exception=exc.EResourceCreation,
            message=("Failed in creating server: One of 'port' "
                     "and 'network' must be provided."))),
        ('create:net-n:port-y:fixed_ip-y', dict(
            reason='create',
            success=False,
            inputs={'port': 'PORT', 'fixed_ip': 'FIXED_IP'},
            net_result=[],
            port_result=[mock.Mock(id='PORT_ID', status='DOWN')],
            sg_result=[],
            floating_result=[],
            result={},
            exception=exc.EResourceCreation,
            message=("Failed in creating server: The 'port' property and the "
                     "'fixed_ip' property cannot be specified at the same "
                     "time."))),
        ('update:net-y:port-y:fixed_ip-n', dict(
            reason='update',
            success=True,
            inputs={'network': 'NET', 'port': 'PORT'},
            net_result=[mock.Mock(id='NET_ID')],
            port_result=[mock.Mock(id='PORT_ID', status='DOWN')],
            sg_result=[],
            floating_result=[],
            result={'network': 'NET_ID', 'port': 'PORT_ID'},
            exception=None,
            message='')),
        ('update:net-y:port-n:fixed_ip-y', dict(
            reason='update',
            success=True,
            inputs={'network': 'NET', 'fixed_ip': 'FIXED_IP'},
            net_result=[mock.Mock(id='NET_ID')],
            port_result=[],
            sg_result=[],
            floating_result=[],
            result={'network': 'NET_ID',
                    'fixed_ip': 'FIXED_IP'},
            exception=None,
            message='')),
        ('update:net-y:port-n:fixed_ip-n:sgroups-y', dict(
            reason='create',
            success=True,
            inputs={'network': 'NET', 'security_groups': ['default']},
            net_result=[mock.Mock(id='NET_ID')],
            port_result=[],
            sg_result=[mock.Mock(id='SG_ID')],
            floating_result=[],
            result={'network': 'NET_ID', 'security_groups': ['SG_ID']},
            exception=None,
            message='')),
        ('update:net-y:port-n:fixed_ip-n:sgroups-n:floating_net-y', dict(
            reason=None,
            success=True,
            inputs={'network': 'NET', 'floating_network': 'NET'},
            net_result=[mock.Mock(id='NET_ID'), mock.Mock(id='NET_ID')],
            port_result=[],
            sg_result=[],
            floating_result=[],
            result={'network': 'NET_ID', 'floating_network': 'NET_ID'},
            exception=None,
            message='')),
        ('update:net-f:port-y:fixed_ip-n', dict(
            reason='update',
            success=False,
            inputs={'network': 'NET', 'port': 'PORT'},
            net_result=[exc.InternalError(message='NET Failure')],
            port_result=[],
            sg_result=[],
            floating_result=[],
            result={},
            exception=exc.EResourceUpdate,
            message="Failed in updating server 'NOVA_ID': NET Failure.")),
        ('update:net-n:port-f:fixed_ip-n', dict(
            reason='update',
            success=False,
            inputs={'port': 'PORT'},
            net_result=[],
            port_result=[exc.InternalError(message='PORT Failure')],
            sg_result=[],
            floating_result=[],
            result={},
            exception=exc.EResourceUpdate,
            message="Failed in updating server 'NOVA_ID': PORT Failure.")),
        ('update:net-n:port-active:fixed_ip-n', dict(
            reason='update',
            success=False,
            inputs={'port': 'PORT'},
            net_result=[],
            port_result=[mock.Mock(id='PORT_ID', status='ACTIVE')],
            sg_result=[],
            floating_result=[],
            result={},
            exception=exc.EResourceUpdate,
            message=("Failed in updating server 'NOVA_ID': The status of the "
                     "port PORT must be DOWN."))),
        ('update:net-n:port-n:fixed_ip-n', dict(
            reason='update',
            success=False,
            inputs={'fixed_ip': 'FIXED_IP'},
            net_result=[],
            port_result=[],
            sg_result=[],
            floating_result=[],
            result={},
            exception=exc.EResourceUpdate,
            message=("Failed in updating server 'NOVA_ID': One of 'port' "
                     "and 'network' must be provided."))),
        ('update:net-n:port-y:fixed_ip-y', dict(
            reason='update',
            success=False,
            inputs={'port': 'PORT', 'fixed_ip': 'FIXED_IP'},
            net_result=[],
            port_result=[mock.Mock(id='PORT_ID', status='DOWN')],
            sg_result=[],
            floating_result=[],
            result={},
            exception=exc.EResourceUpdate,
            message=("Failed in updating server 'NOVA_ID': The 'port' "
                     "property and the 'fixed_ip' property cannot be "
                     "specified at the same time."))),
    ]

    def setUp(self):
        super(TestNetworkValidation, self).setUp()

        self.nc = mock.Mock()
        self.profile = server.ServerProfile('t', spec)
        self.profile._networkclient = self.nc

    def test_validation(self):
        self.nc.network_get.side_effect = self.net_result
        self.nc.port_find.side_effect = self.port_result
        self.nc.security_group_find.side_effect = self.sg_result
        self.nc.floatingip_find.side_effect = self.floating_result
        obj = mock.Mock(physical_id='NOVA_ID')

        if self.success:
            res = self.profile._validate_network(obj, self.inputs, self.reason)
            self.assertEqual(self.result, res)
        else:
            ex = self.assertRaises(self.exception,
                                   self.profile._validate_network,
                                   obj, self.inputs, self.reason)
            self.assertEqual(self.message, six.text_type(ex))

        if self.net_result:
            self.nc.network_get.assert_called_with('NET')
        if self.port_result:
            self.nc.port_find.assert_called_once_with('PORT')
        if self.sg_result:
            self.nc.security_group_find.assert_called_once_with('default')
        if self.floating_result:
            self.nc.floatingip_find.assert_called_once_with('FLOATINGIP')


class TestNovaServerValidate(base.SenlinTestCase):

    def setUp(self):
        super(TestNovaServerValidate, self).setUp()

        self.context = utils.dummy_context()

    def test_do_validate_all_passed(self):
        profile = server.ServerProfile('t', spec)
        mock_az = self.patchobject(profile, '_validate_az')
        mock_flavor = self.patchobject(profile, '_validate_flavor')
        mock_image = self.patchobject(profile, '_validate_image')
        mock_keypair = self.patchobject(profile, '_validate_keypair')
        mock_network = self.patchobject(profile, '_validate_network')
        obj = mock.Mock()

        res = profile.do_validate(obj)

        properties = spec['properties']
        self.assertTrue(res)
        mock_az.assert_called_once_with(obj, properties['availability_zone'])
        mock_flavor.assert_called_once_with(obj, properties['flavor'])
        mock_image.assert_called_once_with(obj, properties['image'])
        mock_keypair.assert_called_once_with(obj, properties['key_name'])
        mock_network.assert_called_once_with(obj, properties['networks'][0])
