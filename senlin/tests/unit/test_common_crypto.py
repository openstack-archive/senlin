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

from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import ciphers
from cryptography.hazmat.primitives.ciphers import algorithms
from cryptography.hazmat.primitives.ciphers import modes
import mock
from oslo_config import cfg
from oslo_utils import encodeutils

from senlin.common import crypto
from senlin.tests.unit.common import base


class CipherTest(base.SenlinTestCase):

    def setUp(self):
        super(CipherTest, self).setUp()
        self.backend = default_backend()

    @mock.patch.object(ciphers, 'Cipher')
    @mock.patch.object(algorithms, 'AES')
    @mock.patch.object(modes, 'CBC')
    def test_create(self, CBC, AES, CIPHER):
        fake_key = '0123456789012345'
        c = crypto.cipher(fake_key)

        k = encodeutils.safe_encode(fake_key)
        iv = encodeutils.safe_encode(cfg.CONF.cipher_init_vector)

        AES.assert_called_once_with(k)
        aes = AES.return_value
        CBC.assert_called_once_with(iv)
        cbc = CBC.return_value
        CIPHER.assert_called_once_with(aes, cbc, backend=self.backend)
        self.assertEqual(c.eng, CIPHER.return_value)

    def test_encrypt(self):
        fake_key = '0123456789012345'
        c = crypto.cipher(fake_key)

        res = c.encrypt('message')
        self.assertEqual('ctYA/fpwUYEwTfDCPGHtLQ==', res)

        res = c.encrypt('a new message')
        self.assertEqual('AFQ6djtA8HpQcFgBd5bU7Q==', res)

        res = c.encrypt('a pretty long message to be encrypted')
        self.assertEqual('JSB0xbd1OWvqMba+WnScEL'
                         'XQo2LdkQXwDuVIgoqVAXok'
                         'VTyTK4rgNlrHIMqpAvYT', res)

    def test_decrypt(self):
        fake_key = '0123456789012345'

        c = crypto.cipher(fake_key)
        res = c.decrypt('ctYA/fpwUYEwTfDCPGHtLQ==')
        self.assertEqual('message', res)

        res = c.decrypt('AFQ6djtA8HpQcFgBd5bU7Q==')
        self.assertEqual('a new message', res)

        res = c.decrypt('JSB0xbd1OWvqMba+WnScELXQo2LdkQXwDuVIgoqVAXok'
                        'VTyTK4rgNlrHIMqpAvYT')
        self.assertEqual('a pretty long message to be encrypted', res)

    def test_decrypt_mismatch(self):
        fake_key = '0123456789012346'
        c = crypto.cipher(fake_key)

        res = c.decrypt('ctYA/fpwUYEwTfDCPGHtLQ==')
        self.assertNotEqual('message', res)

    def test_decrypt_incorrect_content(self):
        fake_key = '0123456789012345'

        c = crypto.cipher(fake_key)
        self.assertRaises(TypeError, c.decrypt, u'\xD4456')

        self.assertRaises(TypeError, c.decrypt, '123456')
