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

import uuid

from senlin.drivers import heat_v1 as heat
from senlin.profiles import base

__type_name__ = 'aws.autoscaling.launchconfig'


class LaunchConfigProfile(base.Profile):
    '''
    Profile for an AWS AutoScaling LaunchConfiguration.

    When this profile is used, the whole cluster is a Heat stack where each
    member is a YAML snippet that describes a
    AWS::AutoScaling::LaunchConfiguration resource.
    '''
    def __init__(self, name, type_name=__type_name__, **kwargs):
        super(LaunchConfigProfile, self).__init__(name, type_name, kwargs)

        self.ImageId = kwargs.get('ImageId')
        self.InstanceType = kwargs.get('InstanceType')
        self.KeyName = kwargs.get('KeyName')
        self.UserData = kwargs.get('UserData')
        self.SecurityGroups = kwargs.get('SecurityGroups')
        self.KernelId = kwargs.get('KernelId')
        self.RamDiskId = kwargs.get('RamDiskId')
        self.BlockDeviceMappings = kwargs.get('BlockDeviceMappings')
        self.NovaSchedulerHings = kwargs.get('NovaSchedulerHints')
        
        # new properties
        self.InstanceMonitoring = kwargs.get('InstanceMonitoring')
        self.SpotPrice = kwargs.get('SpotPrice')
        self.AssocatePublicIpAddress = kwargs.get('AssociatePublicIpAddress')
        self.PlaementTenancy = kwargs.get('PlacementTenancy')

    def do_create(self):
        '''
        This method creates a YAML format Heat resource definition.
        '''
        return tmpl

    def do_delete(self):
        return True

    def do_update(self, ):
        self.status = self.UPDATING

        self.status = self.ACTIVE
        return True
