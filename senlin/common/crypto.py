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

'''
Cryptograpy module.
'''

import base64
import math

from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import ciphers
from cryptography.hazmat.primitives.ciphers import algorithms
from cryptography.hazmat.primitives.ciphers import modes
from oslo_config import cfg
from oslo_utils import encodeutils
import six

from senlin.common.i18n import _

_cipher_opts = [
    cfg.StrOpt('cipher_init_vector', default='SenlinBigSecret!',
               help=_('A 16-bytes long string to be used as the '
                      'intialization vector for message encryption '
                      'and decryption.')),
]

cfg.CONF.register_opts(_cipher_opts)


class cipher(object):

    def __init__(self, key):
        self.backend = default_backend()
        init_vector = cfg.CONF.cipher_init_vector
        k = encodeutils.safe_encode(key)
        iv = encodeutils.safe_encode(init_vector)

        self.eng = ciphers.Cipher(algorithms.AES(k), modes.CBC(iv),
                                  backend=self.backend)

    def encrypt(self, message):
        """Encrypt the given message using the given key.

        :param message: A string to be encrypted;
        :param key: A 64-bytes long string used as the key for encryption.
        :returns: Base64-encoded encrypted message.
        """
        padded = message.ljust(int(math.ceil((len(message) / 16.0))) * 16)
        msg = encodeutils.safe_encode(padded)
        encryptor = self.eng.encryptor()

        ct = encryptor.update(msg) + encryptor.finalize()
        content = base64.b64encode(ct)
        return encodeutils.safe_decode(content)

    def decrypt(self, content):
        """Decrypt the given message using the given key.

        :param content: A base64-encoded text of encrypted message;
        :returns: A string representation of the original message.
        :raises: UnicodeEncodeError or TypeError when provided content is
                 ill-formated base64 string.
        """
        v = encodeutils.safe_encode(content)
        value = ''
        try:
            value = base64.b64decode(v)
        except Exception as ex:
            raise TypeError(six.text_type(ex))

        decryptor = self.eng.decryptor()
        msg = decryptor.update(value) + decryptor.finalize()
        try:
            message = encodeutils.safe_decode(msg)
        except UnicodeDecodeError:
            message = ''

        return message.rstrip()


def list_opts():
    yield None, _cipher_opts
