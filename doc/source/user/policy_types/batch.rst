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

.. _ref-batch-policy:

============
Batch Policy
============

The batch policy is designed to automatically group a large number of
operations into smaller batches so that the service interruption can be better
managed and there won't be flood of service requests sending to any other
services that will form a DOS (denial-of-service) attack.

Currently, this policy is applicable to clusters of all profile types and it
is enforced when cluster is updated. The development team is still looking
for an elegant solution that can regulate the resource creation requests.


Properties
~~~~~~~~~~

.. schemaprops::
  :package: senlin.policies.batch_policy.BatchPolicy

Sample
~~~~~~

Below is a typical spec for a batch policy:

.. literalinclude :: /../../examples/policies/batch_policy.yaml
  :language: yaml

The ``min_in_service`` property specifies the minimum number of nodes to be
kept in ACTIVE status. This is mainly for cluster update use cases. The
other property ``max_batch_size`` specifies the number of nodes to be updated
in each batch. This property is mainly used to ensure that batch requests
are still within the processing capability of a backend service.

Between each batch of service requests, you can specify an interval in the
unit of seconds using the ``pause_time`` property. This can be used to ensure
that updated nodes are fully active to provide services, for example.
