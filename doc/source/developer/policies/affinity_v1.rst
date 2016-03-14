..
  Licensed under the Apache License, Version 2.0 (the "License"); you may
  not use this file except in compliance with the License. You may obtain
  a copy of the License at

          http://www.apache.org/licenses/LICENSE-2.0

  Unless required by applicable law or agreed to in writing, software
  distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
  WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
  License for the specific language governing permissions and limitations
  under the License.


====================
Affinity Policy V1.0
====================

This policy is designed for Senlin clusters to exploit the *servergroup* API
exposed by the Nova compute service. The basic policy has been extended to
work with vSphere hypervisor when VMware DRS feature is enabled. However, such
an extension is only applicable to *admin* owned server clusters.


Applicable Profiles
~~~~~~~~~~~~~~~~~~~

The policy is designed to handle only Nova server profile type, e.g.
``os.nova.server-1.0``.


Actions Handled
~~~~~~~~~~~~~~~

The policy is capable of handling the following actions:

- ``CLUSTER_SCALE_OUT``: an action that carries an optional integer value
  named ``count`` in its ``inputs``.

- ``CLUSTER_RESIZE``: an action that carries various input parameters to
  resize a cluster. The policy will try to parse the raw inputs if no other
  policies have done this.

The policy will be checked **BEFORE** any of the above mentioned actions is
executed. When the action is ``CLUSTER_RESIZE``, the affinity policy will
check if it is about the creation of new nodes. If the resize request is about
the removal of existing nodes, the policy won't block the request.

Senlin engine respects outputs (i.e. number of nodes to create) from other
policies, if any. If no such data exists, it then checks the user-provided
"``count``" input if there is one. The policy is also designed to parse a
cluster resize request and see if there are new nodes to be created.

After validating the ``count`` value, the deletion policy proceeds to update
the ``data`` property of the action with node placement data. For example:

::

  {
    'placement': {
      'count': 2,
      'placements': [
        {'servergroup': 'XYZ-ABCD'},
        {'servergroup': 'XYZ-ABCD'}
      ]
    }
  }


Scenarios
~~~~~~~~~

S1: Inheriting Server Group from Profile
----------------------------------------

When attaching the affinity policy to a cluster that is based on a profile
type of ``os.nova.server-1.0``, if the profile contains ``scheduler_hints``
property and the property value (a collection) has a ``group`` key, the engine
will use the value of the ``group`` key as a Nova server group name. In this
case, the affinity policy will check if the specified server group does exist.
If the group doesn't exist, or the rules specified in the group doesn't match
that specified (or implied) by the affinity policy, you will get an error when
attaching the policy to the cluster. If, on the contrary, the group is found
and the rules do match that of the current policy, the engine will record the
ID of the server group into the policy binding data. The engine also saves a
key-value pair ``inherited_group: True`` into the policy binding data, so that
in future the engine knows that the server group wasn't created from scratch
by the affinity policy. This will lead to the following data stored into the
policy binding data:

::

  {
    'AffinityPolicy': {
      'version': 1.0,
      'data': {
        'servergroup_id': 'XYZ-ABCD',
        'inherited_group': True
      }
    }
  }

When an affinity policy is to be detached from a cluster, the Senlin engine
will check and learn the server group was not created by the affinity policy.
The engine will not delete the server group.

Before any of the targeted actions is executed, the affinity policy gets a
chance to be checked. It does so by looking into the policy binding data and
find out the server group ID to use. For node creation requests, the policy
will yield some data into ``action.data`` property that looks like:

::

  {
    'placement': {
      'count': 2,
      'placements': [
        {'servergroup': 'XYZ-ABCD'},
        {'servergroup': 'XYZ-ABCD'}
      ]
    }
  }


S2: Creating A Server Group when Needed
---------------------------------------

When attaching an affinity policy to a cluster, if the cluster profile doesn't
contain a ``scheduler_hints`` property or there is no ``group`` value
specified in the ``scheduler_hints`` property, the engine will create a new
server group by invoking the Nova API, providing it the policies specified (or
implied) as inputs. The ID of the newly created server group is then saved
into the policy binding data, along with a ``inherited_group: False`` key-value
pair. For example:

::

  {
    'AffinityPolicy': {
      'version': 1.0,
      'data': {
        'servergroup_id': 'XYZ-ABCD',
        'inherited_group': False
      }
    }
  }

When such a policy is later detached from the cluster, the Senlin engine will
check and learn that the server group should be deleted. It then deletes the
server group by invoking Nova API.

When the targeted actions are about to be executed, the protocol for checking
and data saving is identical to that outlined in scenario *S1*.


S3: Enabling vSphere DRS Extensions
-----------------------------------

When you have vSphere hosts (with DRS feature enabled) serving hypervisors to
Nova, a vSphere host is itself a collection of physical nodes. To make better
use of the vSphere DRS feature, you can enable the DRS extension by specifying
``enable_drs_extension: True`` in your affinity policy.

When attaching and detaching the affinity policy to/from a cluster, the engine
operations are the same as described in scenario *S1* and *S2*. However, when
one of the targeted actions is triggered, the affinity policy will first check
if the ``availability_zone`` property is set and it will use "``nova``" as the
default value if not specified.

The engine then continues to check the input parameters (as outlined above) to
find out the number of nodes to create. It also checks the server group ID to
use by looking into the policy binding data.

After the policy has collected all inputs it needs, it proceeds to check the
available vSphere hypervisors with DRS enabled. It does so by looking into the
``hypervisor_hostname`` property of each hypervisor reported by Nova
(**Note**: retrieving hypervisor list is an admin-only API, and that is the
reason the vSphere extension is only applicable to admin-owned clusters).
The policy attempts to find a hypervisor whose host name contains ``drs``. If
it fails to find such a hypervisor, the policy check fails with the action's
``data`` field set to:

::

  {
    'status': 'ERROR',
    'status_reason': 'No suitable vSphere host is available.'
  }

The affinity uses the first matching hypervisor as the target host and it
forms a string containing the availability zone name and the hypervisor
host name, e.g. "``nova:vsphere_drs_1``". This string will later be used as
the availability zone name sent to Nova. For example, the following is sample
result when applying the affinity policy to a cluster with vSphere DRS
enabled.

::

  {
    'placement': {
      'count': 2,
      'placements': [{
          'zone': 'nova:vsphere_drs_1',
          'servergroup': 'XYZ-ABCD'
        }, {
          'zone': 'nova:vsphere_drs_1',
          'servergroup': 'XYZ-ABCD'
        }
      ]
    }
  }

**NOTE**: The ``availability_zone`` property is effective even when the
vSphere DRS extension is not enabled. When ``availability_zone`` is explicitly
specified, the affinity policy will pass it along with the server group ID
to the Senlin engine for further processing, e.g.:

::

  {
    'placement': {
      'count': 2,
      'placements': [{
          'zone': 'nova_1',
          'servergroup': 'XYZ-ABCD'
        }, {
          'zone': 'nova_1',
          'servergroup': 'XYZ-ABCD'
        }
      ]
    }
  }
