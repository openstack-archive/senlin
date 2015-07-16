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

from oslo_log import log
import six

from senlin.common import exception
from senlin.common.i18n import _
from senlin.drivers import base
from senlin.drivers.openstack import sdk

LOG = log.getLogger(__name__)


class NeutronClient(base.DriverBase):
    '''Neutron V2 driver.'''

    def __init__(self, params):
        self.conn = sdk.create_connection(params)

    def network_get(self, name_or_id):
        try:
            network = self.conn.network.find_network(name_or_id)
        except sdk.exc.HttpException as ex:
            msg = _('Failed in getting network %(value)s: %(ex)s'
                    ) % {'value': name_or_id, 'ex': six.text_type(ex)}
            raise exception.Error(msg=msg)

        return network

    def subnet_get(self, name_or_id):
        try:
            subnet = self.conn.network.find_subnet(name_or_id)
        except sdk.exc.HttpException as ex:
            msg = _('Failed in getting subnet %(value)s: %(ex)s'
                    ) % {'value': name_or_id, 'ex': six.text_type(ex)}
            # TODO(Yanyan Hu): choose more proper exception type,
            # e.g. ResourceNotFound.
            raise exception.Error(msg=msg)

        return subnet

    def loadbalancer_get(self, name_or_id):
        try:
            lb = self.conn.network.find_load_balancer(name_or_id)
        except sdk.exc.HttpException as ex:
            msg = _('Failed in getting loadbalancer %(value)s: %(ex)s'
                    ) % {'value': name_or_id, 'ex': six.text_type(ex)}
            raise exception.Error(msg=msg)

        return lb

    def loadbalancer_list(self):
        try:
            lbs = [lb for lb in self.conn.network.load_balancers()]
        except sdk.exc.HttpException as ex:
            msg = _('Failed in listing loadbalancer: %(ex)s'
                    ) % {'ex': six.text_type(ex)}
            raise exception.Error(msg=msg)

        return lbs

    def loadbalancer_create(self, vip_subnet_id, vip_address=None,
                            admin_state_up=True, name=None, description=None):

        kwargs = {
            'vip_subnet_id': vip_subnet_id,
            'admin_state_up': admin_state_up,
        }

        if vip_address is not None:
            kwargs['vip_address'] = vip_address
        if name is not None:
            kwargs['name'] = name
        if description is not None:
            kwargs['description'] = description

        try:
            res = self.conn.network.create_load_balancer(**kwargs)
        except sdk.exc.HttpException as ex:
            msg = _('Failed in creating loadbalancer: %(ex)s'
                    ) % {'ex': six.text_type(ex)}
            raise exception.Error(msg=msg)

        return res

    def loadbalancer_delete(self, lb_id, ignore_missing=True):
        try:
            self.conn.network.delete_load_balancer(
                lb_id, ignore_missing=ignore_missing)
        except sdk.exc.HttpException as ex:
            msg = _('Failed in deleting loadbalancer %(id)s: %(ex)s'
                    ) % {'id': lb_id, 'ex': six.text_type(ex)}
            raise exception.Error(msg=msg)

        return

    def listener_get(self, name_or_id):
        try:
            listener = self.conn.network.find_listener(name_or_id)
        except sdk.exc.HttpException as ex:
            msg = _('Failed in getting lb listener %(value)s: %(ex)s'
                    ) % {'value': name_or_id, 'ex': six.text_type(ex)}
            raise exception.Error(msg=msg)

        return listener

    def listener_list(self):
        try:
            listeners = [i for i in self.conn.network.listeners()]
        except sdk.exc.HttpException as ex:
            msg = _('Failed in listing lb listener: %(ex)s'
                    ) % {'ex': six.text_type(ex)}
            raise exception.Error(msg=msg)

        return listeners

    def listener_create(self, loadbalancer_id, protocol, protocol_port,
                        connection_limit=None,
                        admin_state_up=True, name=None, description=None):

        kwargs = {
            'loadbalancer_id': loadbalancer_id,
            'protocol': protocol,
            'protocol_port': protocol_port,
            'admin_state_up': admin_state_up,
        }

        if connection_limit is not None:
            kwargs['connection_limit'] = connection_limit
        if name is not None:
            kwargs['name'] = name
        if description is not None:
            kwargs['description'] = description

        try:
            res = self.conn.network.create_listener(**kwargs)
        except sdk.exc.HttpException as ex:
            msg = _('Failed in creating lb listener: %(ex)s'
                    ) % {'ex': six.text_type(ex)}
            raise exception.Error(msg=msg)

        return res

    def listener_delete(self, listener_id, ignore_missing=True):
        try:
            self.conn.network.delete_listener(listener_id,
                                              ignore_missing=ignore_missing)
        except sdk.exc.HttpException as ex:
            msg = _('Failed in deleting lb listener %(id)s: %(ex)s'
                    ) % {'id': listener_id, 'ex': six.text_type(ex)}
            raise exception.Error(msg=msg)

        return

    def pool_get(self, name_or_id):
        try:
            pool = self.conn.network.find_pool(name_or_id)
        except sdk.exc.HttpException as ex:
            msg = _('Failed in getting lb pool %(value)s: %(ex)s'
                    ) % {'value': name_or_id, 'ex': six.text_type(ex)}
            raise exception.Error(msg=msg)

        return pool

    def pool_list(self):
        try:
            pools = [p for p in self.conn.network.pools()]
        except sdk.exc.HttpException as ex:
            msg = _('Failed in listing lb pool: %(ex)s'
                    ) % {'ex': six.text_type(ex)}
            raise exception.Error(msg=msg)

        return pools

    def pool_create(self, lb_algorithm, listener_id, protocol,
                    admin_state_up=True, name=None, description=None):

        kwargs = {
            'lb_algorithm': lb_algorithm,
            'listener_id': listener_id,
            'protocol': protocol,
            'admin_state_up': admin_state_up,
        }

        if name is not None:
            kwargs['name'] = name
        if description is not None:
            kwargs['description'] = description

        try:
            res = self.conn.network.create_pool(**kwargs)
        except sdk.exc.HttpException as ex:
            msg = _('Failed in creating lb pool: %(ex)s'
                    ) % {'ex': six.text_type(ex)}
            raise exception.Error(msg=msg)

        return res

    def pool_delete(self, pool_id, ignore_missing=True):
        try:
            self.conn.network.delete_pool(pool_id,
                                          ignore_missing=ignore_missing)
        except sdk.exc.HttpException as ex:
            msg = _('Failed in deleting lb pool %(id)s: %(ex)s'
                    ) % {'id': pool_id, 'ex': six.text_type(ex)}
            raise exception.Error(msg=msg)

        return

    def pool_member_get(self, pool_id, name_or_id):
        try:
            member = self.conn.network.find_pool_member(name_or_id,
                                                        pool_id)
        except sdk.exc.HttpException as ex:
            msg = _('Failed in getting lb pool_member %(value)s: %(ex)s'
                    ) % {'value': name_or_id, 'ex': six.text_type(ex)}
            raise exception.Error(msg=msg)

        return member

    def pool_member_list(self, pool_id):
        try:
            members = [m for m in self.conn.network.pool_members(pool_id)]
        except sdk.exc.HttpException as ex:
            msg = _('Failed in listing lb members of pool %(id)s: %(ex)s'
                    ) % {'id': pool_id, 'ex': six.text_type(ex)}
            raise exception.Error(msg=msg)

        return members

    def pool_member_create(self, pool_id, address, protocol_port, subnet_id,
                           weight=None, admin_state_up=True):

        kwargs = {
            'pool_id': pool_id,
            'address': address,
            'protocol_port': protocol_port,
            'admin_state_up': admin_state_up,
            'subnet_id': subnet_id,
        }

        if weight is not None:
            kwargs['weight'] = weight

        try:
            res = self.conn.network.create_pool_member(**kwargs)
        except sdk.exc.HttpException as ex:
            msg = _('Failed in adding member to lb pool %(id)s: %(ex)s'
                    ) % {'id': pool_id, 'ex': six.text_type(ex)}
            raise exception.Error(msg=msg)

        return res

    def pool_member_delete(self, pool_id, member_id, ignore_missing=True):
        try:
            self.conn.network.delete_pool_member(
                member_id, pool_id, ignore_missing=ignore_missing)
        except sdk.exc.HttpException as ex:
            msg = _('Failed in deleting lb member %(id)s from pool %(pool)s: '
                    '%(ex)s') % {'id': member_id, 'pool': pool_id,
                                 'ex': six.text_type(ex)}
            raise exception.Error(msg=msg)

        return

    def healthmonitor_get(self, name_or_id):
        try:
            hm = self.conn.network.find_health_monitor(name_or_id)
        except sdk.exc.HttpException as ex:
            msg = _('Failed in getting lb healthmonitor %(value)s: %(ex)s'
                    ) % {'value': name_or_id, 'ex': six.text_type(ex)}
            raise exception.Error(msg=msg)

        return hm

    def healthmonitor_list(self):
        try:
            hms = [hm for hm in self.conn.network.list_health_monitors()]
        except sdk.exc.HttpException as ex:
            msg = _('Failed in listing lb healthmonitor: %(ex)s'
                    ) % {'ex': six.text_type(ex)}
            raise exception.Error(msg=msg)

        return hms

    def healthmonitor_create(self, hm_type, delay, timeout, max_retries,
                             pool_id, admin_state_up=True,
                             http_method=None, url_path=None,
                             expected_codes=None):
        kwargs = {
            'type': hm_type,
            'delay': delay,
            'timeout': timeout,
            'max_retries': max_retries,
            'pool_id': pool_id,
            'admin_state_up': admin_state_up,
        }

        if hm_type == 'HTTP':
            if http_method is not None:
                kwargs['http_method'] = http_method
            if url_path is not None:
                kwargs['url_path'] = url_path
            if expected_codes is not None:
                kwargs['expected_codes'] = expected_codes

        try:
            res = self.conn.network.create_pool(**kwargs)
        except sdk.exc.HttpException as ex:
            msg = _('Failed in creating lb healthmonitor: %(ex)s'
                    ) % {'ex': six.text_type(ex)}
            raise exception.Error(msg=msg)

        return res

    def healthmonitor_delete(self, hm_id, ignore_missing=True):
        try:
            self.conn.network.delete_health_monitor(
                hm_id, ignore_missing=ignore_missing)
        except sdk.exc.HttpException as ex:
            msg = _('Failed in deleting lb healthmonitor %(id)s: %(ex)s'
                    ) % {'id': hm_id, 'ex': six.text_type(ex)}
            raise exception.Error(msg=msg)

        return
