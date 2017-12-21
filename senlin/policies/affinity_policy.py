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

"""
Policy for placing nodes based on Nova server groups.

NOTE:  For full documentation about how the affinity policy works, check:
https://docs.openstack.org/senlin/latest/developer/policies/affinity_v1.html
"""

import re
import six

from oslo_log import log as logging
from senlin.common import constraints
from senlin.common import consts
from senlin.common import context
from senlin.common import exception as exc
from senlin.common.i18n import _
from senlin.common import scaleutils as su
from senlin.common import schema
from senlin.common import utils
from senlin.objects import cluster_policy as cpo
from senlin.policies import base


LOG = logging.getLogger(__name__)


class AffinityPolicy(base.Policy):
    """Policy for placing members of a cluster based on server groups.

    This policy is expected to be enforced before new member(s) added to an
    existing cluster.
    """
    VERSION = '1.0'
    VERSIONS = {
        '1.0': [
            {'status': consts.SUPPORTED, 'since': '2016.10'}
        ]
    }
    PRIORITY = 300

    TARGET = [
        ('BEFORE', consts.CLUSTER_SCALE_OUT),
        ('BEFORE', consts.CLUSTER_RESIZE),
        ('BEFORE', consts.NODE_CREATE),
    ]

    PROFILE_TYPE = [
        'os.nova.server-1.0',
    ]

    KEYS = (
        SERVER_GROUP, AVAILABILITY_ZONE, ENABLE_DRS_EXTENSION,
    ) = (
        'servergroup', 'availability_zone', 'enable_drs_extension',
    )

    _GROUP_KEYS = (
        GROUP_NAME, GROUP_POLICIES,
    ) = (
        'name', 'policies',
    )

    _POLICIES_VALUES = (
        # NOTE: soft policies are supported from compute micro version 2.15
        AFFINITY, SOFT_AFFINITY, ANTI_AFFINITY, SOFT_ANTI_AFFINITY,
    ) = (
        'affinity', 'soft-affinity', 'anti-affinity', 'soft-anti-affinity',
    )

    properties_schema = {
        SERVER_GROUP: schema.Map(
            _('Properties of the VM server group'),
            schema={
                GROUP_NAME: schema.String(
                    _('The name of the server group'),
                ),
                GROUP_POLICIES: schema.String(
                    _('The server group policies.'),
                    default=ANTI_AFFINITY,
                    constraints=[
                        constraints.AllowedValues(_POLICIES_VALUES),
                    ],
                ),
            },
        ),
        AVAILABILITY_ZONE: schema.String(
            _('Name of the availability zone to place the nodes.'),
        ),
        ENABLE_DRS_EXTENSION: schema.Boolean(
            _('Enable vSphere DRS extension.'),
            default=False,
        ),
    }

    def __init__(self, name, spec, **kwargs):
        super(AffinityPolicy, self).__init__(name, spec, **kwargs)

        self.enable_drs = self.properties.get(self.ENABLE_DRS_EXTENSION)

    def validate(self, context, validate_props=False):
        super(AffinityPolicy, self).validate(context, validate_props)

        if not validate_props:
            return True

        az_name = self.properties.get(self.AVAILABILITY_ZONE)
        if az_name:
            nc = self.nova(context.user_id, context.project_id)
            valid_azs = nc.validate_azs([az_name])
            if not valid_azs:
                msg = _("The specified %(key)s '%(value)s' could not be "
                        "found.") % {'key': self.AVAILABILITY_ZONE,
                                     'value': az_name}
                raise exc.InvalidSpec(message=msg)

        return True

    def attach(self, cluster, enabled=True):
        """Routine to be invoked when policy is to be attached to a cluster.

        :para cluster: The cluster to which the policy is being attached to.
        :param enabled: The attached cluster policy is enabled or disabled.
        :returns: When the operation was successful, returns a tuple (True,
                  message); otherwise, return a tuple (False, error).
        """
        res, data = super(AffinityPolicy, self).attach(cluster)
        if res is False:
            return False, data

        data = {'inherited_group': False}
        nc = self.nova(cluster.user, cluster.project)
        group = self.properties.get(self.SERVER_GROUP)

        # guess servergroup name
        group_name = group.get(self.GROUP_NAME, None)

        if group_name is None:
            profile = cluster.rt['profile']
            if 'scheduler_hints' in profile.spec:
                hints = profile.spec['scheduler_hints']
                group_name = hints.get('group', None)

        if group_name:
            try:
                server_group = nc.server_group_find(group_name, True)
            except exc.InternalError as ex:
                msg = _("Failed in retrieving servergroup '%s'."
                        ) % group_name
                LOG.exception('%(msg)s: %(ex)s' % {
                              'msg': msg, 'ex': six.text_type(ex)})
                return False, msg

            if server_group:
                # Check if the policies match
                policies = group.get(self.GROUP_POLICIES)
                if policies and policies != server_group.policies[0]:
                    msg = _("Policies specified (%(specified)s) doesn't match "
                            "that of the existing servergroup (%(existing)s)."
                            ) % {'specified': policies,
                                 'existing': server_group.policies[0]}
                    return False, msg

                data['servergroup_id'] = server_group.id
                data['inherited_group'] = True

        if not data['inherited_group']:
            # create a random name if necessary
            if not group_name:
                group_name = 'server_group_%s' % utils.random_name()
            try:
                server_group = nc.server_group_create(
                    name=group_name,
                    policies=[group.get(self.GROUP_POLICIES)])
            except Exception as ex:
                msg = _('Failed in creating servergroup.')
                LOG.exception('%(msg)s: %(ex)s' % {
                    'msg': msg, 'ex': six.text_type(ex)})
                return False, msg

            data['servergroup_id'] = server_group.id

        policy_data = self._build_policy_data(data)

        return True, policy_data

    def detach(self, cluster):
        """Routine to be called when the policy is detached from a cluster.

        :param cluster: The cluster from which the policy is to be detached.
        :returns: When the operation was successful, returns a tuple of
                  (True, data) where the data contains references to the
                  resources created; otherwise returns a tuple of (False,
                  error) where the err contains a error message.
        """

        reason = _('Servergroup resource deletion succeeded.')

        ctx = context.get_admin_context()
        binding = cpo.ClusterPolicy.get(ctx, cluster.id, self.id)
        if not binding or not binding.data:
            return True, reason

        policy_data = self._extract_policy_data(binding.data)
        if not policy_data:
            return True, reason

        group_id = policy_data.get('servergroup_id', None)
        inherited_group = policy_data.get('inherited_group', False)

        if group_id and not inherited_group:
            try:
                nc = self.nova(cluster.user, cluster.project)
                nc.server_group_delete(group_id)
            except Exception as ex:
                msg = _('Failed in deleting servergroup.')
                LOG.exception('%(msg)s: %(ex)s' % {
                    'msg': msg, 'ex': six.text_type(ex)})
                return False, msg

        return True, reason

    def pre_op(self, cluster_id, action):
        """Routine to be called before target action is executed.

        This policy annotates the node with a server group ID before the
        node is actually created. For vSphere DRS, it is equivalent to the
        selection of vSphere host (cluster).

        :param cluster_id: ID of the cluster on which the relevant action
                            is to be executed.
        :param action: The action object that triggered this operation.
        :returns: Nothing.
        """
        zone_name = self.properties.get(self.AVAILABILITY_ZONE)
        if not zone_name and self.enable_drs:
            # we make a reasonable guess of the zone name for vSphere
            # support because the zone name is required in that case.
            zone_name = 'nova'

        # we respect other policies decisions (if any) and fall back to the
        # action inputs if no hints found.
        pd = action.data.get('creation', None)
        if pd is not None:
            count = pd.get('count', 1)
        elif action.action == consts.CLUSTER_SCALE_OUT:
            count = action.inputs.get('count', 1)
        elif action.action == consts.NODE_CREATE:
            count = 1
        else:  # CLUSTER_RESIZE
            cluster = action.entity
            current = len(cluster.nodes)
            su.parse_resize_params(action, cluster, current)
            if 'creation' not in action.data:
                return
            count = action.data['creation']['count']

        cp = cpo.ClusterPolicy.get(action.context, cluster_id, self.id)
        policy_data = self._extract_policy_data(cp.data)
        pd_entry = {'servergroup': policy_data['servergroup_id']}

        # special handling for vSphere DRS case where we need to find out
        # the name of the vSphere host which has DRS enabled.
        if self.enable_drs:
            obj = action.entity
            nc = self.nova(obj.user, obj.project)

            hypervisors = nc.hypervisor_list()
            hv_id = ''
            pattern = re.compile(r'.*drs*', re.I)
            for hypervisor in hypervisors:
                match = pattern.match(hypervisor.hypervisor_hostname)
                if match:
                    hv_id = hypervisor.id
                    break

            if not hv_id:
                action.data['status'] = base.CHECK_ERROR
                action.data['status_reason'] = _('No suitable vSphere host '
                                                 'is available.')
                action.store(action.context)
                return

            hv_info = nc.hypervisor_get(hv_id)
            hostname = hv_info['service']['host']
            pd_entry['zone'] = ":".join([zone_name, hostname])

        elif zone_name:
            pd_entry['zone'] = zone_name

        pd = {
            'count': count,
            'placements': [pd_entry] * count,
        }
        action.data.update({'placement': pd})
        action.store(action.context)

        return
