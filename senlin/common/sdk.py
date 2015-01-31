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
SDK Client
'''
from openstack import connection
from openstack import exceptions
from openstack import user_preference

USER_AGENT = 'senlin'

exc = exceptions


def create_connection(context):
    kwargs = {
        'auth_url': context.auth_url,
        'domain_id': context.domain_id,
        'project_id': context.project_id,
        'project_domain_id': context.project_domain_id,
        'user_domain_id': context.user_domain_id,
        'user_id': context.user_id,
        'password': context.password,
        'token': context.auth_token,
        #  'auth_plugin': args.auth_plugin,
        #  'verify': OS_CACERT, TLS certificate to verify remote server
    }

    pref = user_preference.UserPreference()
    if context.region_name:
        pref.set_set_region(pref.ALL, context.region_name)

    try:
        conn = connection.Connection(preferences=pref, user_agent=USER_AGENT,
                                     **kwargs)
    except exceptions.HttpException as ex:
        raise ex
    return conn
