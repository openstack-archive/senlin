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

from oslo_config import cfg

from senlin.drivers import base as driver_base
from senlin.engine.notifications import message as mmod
from senlin.tests.unit.common import base
from senlin.tests.unit.common import utils

UUID = 'aa5f86b8-e52b-4f2b-828a-4c14c770938d'


class TestMessage(base.SenlinTestCase):
    def setUp(self):
        super(TestMessage, self).setUp()
        self.context = utils.dummy_context()

    @mock.patch.object(driver_base, 'SenlinDriver')
    def test_zaqar_client(self, mock_senlindriver):
        sd = mock.Mock()
        zc = mock.Mock()
        sd.message.return_value = zc
        mock_senlindriver.return_value = sd

        message = mmod.Message('myqueue', user='user1',
                               project='project1')

        # cached will be returned
        message._zaqarclient = zc
        self.assertEqual(zc, message.zaqar())

        # new zaqar client created if no cache found
        message._zaqarclient = None
        params = mock.Mock()
        mock_param = self.patchobject(mmod.Message, '_build_conn_params',
                                      return_value=params)
        res = message.zaqar()
        self.assertEqual(zc, res)
        self.assertEqual(zc, message._zaqarclient)
        mock_param.assert_called_once_with('user1', 'project1')
        sd.message.assert_called_once_with(params)

    @mock.patch.object(mmod.Message, 'zaqar')
    def test_post_lifecycle_hook_message(self, mock_zaqar):
        cfg.CONF.set_override('max_message_size', 8192, 'notification')
        mock_zc = mock.Mock()
        mock_zaqar.return_value = mock_zc
        queue_name = 'my_queue'
        message = mmod.Message(queue_name)
        mock_zc.queue_exists.return_value = True

        lifecycle_action_token = 'ACTION_ID'
        node_id = 'NODE_ID'
        lifecycle_transition_type = 'TYPE'

        message.post_lifecycle_hook_message(lifecycle_action_token, node_id,
                                            lifecycle_transition_type)

        mock_zc.queue_create.assert_not_called()

        message_list = [{
            "ttl": 300,
            "body": {
                "lifecycle_action_token": lifecycle_action_token,
                "node_id": node_id,
                "lifecycle_transition_type": lifecycle_transition_type
            }
        }]
        mock_zc.message_post.assert_called_once_with(queue_name, message_list)

    @mock.patch.object(mmod.Message, 'zaqar')
    def test_post_lifecycle_hook_message_queue_nonexistent(self, mock_zaqar):
        cfg.CONF.set_override('max_message_size', 8192, 'notification')
        cfg.CONF.set_override('ttl', 500, 'notification')

        mock_zc = mock.Mock()
        mock_zaqar.return_value = mock_zc
        queue_name = 'my_queue'
        message = mmod.Message(queue_name)
        kwargs = {
            '_max_messages_post_size': 8192,
            'description': "Senlin lifecycle hook notification",
            'name': queue_name
        }
        mock_zc.queue_exists.return_value = False

        lifecycle_action_token = 'ACTION_ID'
        node_id = 'NODE_ID'
        lifecycle_transition_type = 'TYPE'

        message.post_lifecycle_hook_message(lifecycle_action_token, node_id,
                                            lifecycle_transition_type)

        mock_zc.queue_create.assert_called_once_with(**kwargs)

        message_list = [{
            "ttl": 500,
            "body": {
                "lifecycle_action_token": lifecycle_action_token,
                "node_id": node_id,
                "lifecycle_transition_type": lifecycle_transition_type
            }
        }]
        mock_zc.message_post.assert_called_once_with(queue_name, message_list)
