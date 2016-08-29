#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

from oslo_config import cfg
from senlin.common.i18n import _

service_available_group = cfg.OptGroup(name="service_available",
                                       title="Available OpenStack Services")

ServiceAvailableGroup = [
    cfg.BoolOpt("senlin",
                default=True,
                help=_("Whether or not senlin is expected to be available")),
]

clustering_group = cfg.OptGroup(name="clustering",
                                title="Clustering Service Options")

ClusteringGroup = [
    cfg.StrOpt("catalog_type",
               default="clustering",
               help=_("Catalog type of the clustering service.")),
    cfg.IntOpt("wait_timeout",
               default=60,
               help=_("Waiting time for a specific status, in seconds."))
]
