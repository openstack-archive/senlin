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


==============
Senlin testing
==============

Overview of Testing
~~~~~~~~~~~~~~~~~~~

The Senlin project currently has five different types of testing facilities in
place for developers to perform different kinds of tests:

- *Unit Tests*: These are source code level testing that verifies the classes
  and methods behave as implemented. Once implemented, these tests are also
  used to guarantee that code behavior won't change accidentally by other
  patches.
- *API Tests*: These tests treat the *senlin-api* and the *senlin-engine* as
  black boxes. The test cases focus more on the API surface rather than how
  each API is implemented. Once implemented, these tests help ensure that
  the user-visible service interface don't change without a good reason.
- *Functional Tests*: These tests also treat the *senlin-api* and the
  *senlin-engine* as block boxes. They focus more on the user perceivable
  service behavior. Most tests are anticipated to test a particular "story"
  and verify that the *senlin-engine* always behave consistently.
- *Integration Tests*: These are the tests that integrate senlin with other
  OpenStack services and verify the senlin service can perform its operations
  correctly when interacting with other services.
- *Stress Tests*: These are tests for measuring the performance of the
  *senlin-api* and *senlin-engine* under different workloads.


Cloud Backends
~~~~~~~~~~~~~~

The senlin server is shipped with two collections of "cloud backends": one for
interacting with a real OpenStack deployment, the other for running complex
tests including api tests, functional tests, stress tests. The first cloud
backend is referred to as '`openstack`' and the second is referred to as
'`openstack_test`'. While the `openstack` cloud backend contains full featured
drivers for senlin to talk to the OpenStack services supported, the
`openstack_test` backend contains some "dummy" drivers that return fake
responses for service requests. The `openstack_test` driver is located at
:file:`senlin/tests/drivers` subdirectory. It is provided to facilitate tests
on the senlin service itself without involving any other OpenStack services.
Several types of tests can benefit from these "dummy" drivers because 1) they
can save developers a lot time on debugging complex issues when interacting
with other OpenStack services, and 2) they make running those types of tests
much easier and quicker.

Note that "Integration Tests" are designed for senlin to interact with real
services so we should use the `openstack` backend rather than the
`openstack_test` backend.

To configure the backend to use before running tests, you can check the
`[DEFAULT]` section in the configuration file :file:`/etc/senlin/senlin.conf`.

::

  [DEFAULT]
  cloud_backend = openstack_test   # use this for api, functional tests;
                                   # or 'openstack' for production environment
                                   # and integration tests.


Unit Tests
~~~~~~~~~~

All unit tests are to be placed in the :file:`senlin/tests/unit` sub-directory.
Test cases are organized by the targeted subsystems/modules. Each subsystem
directory must contain a separate blank __init__.py for tests discovery to
function properly.

An example directory structure::

  senlin
   `- tests
       `- unit
           |-- db
           |   |-- __init__.py
           |   |-- test_cluster_api.py
           |   `-- test_node_api.py
           |-- engine
           |   |-- __init__.py
           |   |-- test_clusters.py
           |   `-- test_nodes.py
           |-- __init__.py
           `-- test_utils.py


Writing a Unit Test
-------------------

The *os-testr* software (see: https://pypi.org/project/os-testr/) is used to
find and run tests, parallelize their runs, and record timing/results.

If new dependencies are introduced upon the development of a test, the
`test-requirements.txt` file needs to be updated so that the virtual
environment will be able to successfully execute all tests.

The `test-requirements.txt` file needs to be synchronized with the
openstack/global-requirements project. Developers should try avoid
introducing additional package dependencies unless forced to.


Running Unit Tests
------------------

Senlin uses `tox` for running unit tests, as practiced by many other OpenStack
projects::

  $ tox

This by default will run unit tests suite with Python 2.7 and PEP8/HACKING
style checks. To run only one type of tests you can explicitly provide `tox`
with the test environment to use::

  $ tox -e py27 # test suite on python 2.7
  $ tox -e pep8 # run full source code checker

To run only a subset of tests, you can provide `tox` with a regex argument::

  $ tox -e py27 -- -r ClusterTest

To use debugger like `pdb` during test run, you have to run tests directly
with other, non-concurrent test runner instead of `testr`.
That also presumes that you have a virtual env with all senlin dependencies
installed and configured.

A more convenient way to run specific test is to name the unit test directly,
as shown below::

  $ python -m testtools.run senlin.tests.unit.db.test_cluster_api

This command, however, is not using dependent packages in a particular virtual
environment as the `tox` command does. It is using the system-wide Python
package repository when running the tests.


API Tests
~~~~~~~~~

Senlin API test cases are written based on the *tempest* framework (see:
`tempest_overview`_). Test cases are developed using the Tempest Plugin
Interface (see: `tempest_plugin`_ ).


Writing an API Test Case
------------------------

API tests are hosted in the `senlin-tempest-plugin` project. When new APIs are added
or existing APIs are changed, an API test case should be added to the
:file:`senlin_tempest_plugin/tests/api` sub-directory, based on the resources impacted
by the change.

Each test case should derive from the class
:class:`senlin_tempest_plugin.tests.api.base.BaseSenlinAPITest`. Positive
test cases should be separated from negative ones. We don't encourage combining
more than one test case into a single method, unless there is an obvious reason.

To improve the readability of the test cases, Senlin has provided a utility
module which can be leveraged - :file:`senlin_tempest_plugin/common/utils.py`.


Running API Tests
-----------------

Senlin API tests use fake OpenStack drivers to improve the throughput of test
execution. This is because in API tests, we don't care about the details in
how *senlin-engine* is interacting with other services. We care more about the
APIs succeeds in an expected way or fails in a predictable manner.

Although the senlin engine is talking to fake drivers, the test cases still
need to communicate to the senlin API service as it would in a real
deployment. That means you will have to export your OpenStack credentials
before running the tests. For example, you will source the :file:`openrc` file
when using a devstack environment::

  $ . $HOME/devstack/openrc

This will ensure you have environment variables such as ``OS_AUTH_URL``,
``OS_USERNAME`` properly set and exported. The next step is to enter the
:file:`tempest` directory and run the tests there::

  $ cd /opt/stack/tempest
  $ nosetests -v -- senlin

To run a single test case, you can specify the test case name. For example::

  $ cd /opt/stack/tempest
  $ nosetests -v -- \
    senlin_tempest_plugin.tests.api.clusters.test_cluster_create

If you prefer running API tests in a virtual environment, you can simply use
the following command::

  $ cd /opt/stack/senlin
  $ tox -e api


Functional Tests
~~~~~~~~~~~~~~~~

Similar to the API tests, senlin functional tests are also developed based on
the *tempest* framework. Test cases are written using the Tempest Plugin
Interface (see: `tempest_plugin`_).

.. _`tempest_overview`: https://docs.openstack.org/tempest/latest/
.. _`tempest_plugin`: https://docs.openstack.org/tempest/latest/plugin


Writing Functional Tests
------------------------

Functional tests are hosted in the `senlin-tempest-plugin` project. There are current
a limited collection of functional test cases which can be
found under :file:`senlin_tempest_plugin/tests/functional/` subdirectory. In future,
we may add more test cases when needed. The above subdirectory will remain the
home of newly added functional tests.

When writing functional tests, it is highly desirable that each test case is
designed for a specific use case or story line.


Running Functional Tests
------------------------

Similar to API tests, you will need to export your OpenStack credentials
before running any functional tests.

The most straight forward way to run functional tests is to use the virtual
environment defined in the :file:`tox.ini` file, that is::

  $ cd /opt/stack/senlin
  $ tox -e functional

If you prefer running a particular functional test case, you can do the
following as well::

  $ cd /opt/stack/senlin
  $ python -m testtools.run senlin_tempest_plugin.tests.functional.test_cluster_basic


Integration Tests
~~~~~~~~~~~~~~~~~

Integration tests are basically another flavor of functional tests. The only
difference from functional tests is that integration tests use real device
drivers so the *senlin-engine* is talking to real services.


Writing Integration Tests
-------------------------

Integration tests are hosted in the `senlin-tempest-plugin` project. Integration tests
are designed to be run at Gerrit gate to ensure that changes to senlin code
won't break its interactions with other (backend) services.
Since OpenStack gate infrastructure is a shared resource pool for all
OpenStack projects, we are supposed to be very careful when adding new test
cases. The test cases added are supposed to focus more on the interaction
between senlin and other services than other things.

All integration test cases are to be placed under the subdirectory
:file:`senlin_tempest_plugin/tests/integration`. Test cases are expected to be
organized into a small number of story lines that can exercise as many
interactions between senlin and backend services as possible.

Each "story line" should be organized into a separate class module that
inherits from the ``BaseSenlinIntegrationTest`` class which can be found at
:file:`senlin_tempest_plugin/tests/integration/base.py` file. Each test case should
be annotated with a ``decorators.attr`` annotator and an idempotent ID as shown
below:

.. code-block:: python

  from tempest.lib import decorators

  from senlin.tests.tempest.integration import base


  class MyIntegrationTest(base.BaseSenlinIntegrationTest):

    @decorators.attr(type=['integration'])
    @decorators.idempotent_id('<A UUID for the test case>')
    def test_a_sad_story(self):
      # Test logic goes here
      # ...


Running Integration Tests
-------------------------

The integration tests are designed to be executed at Gerrit gate. However, you
can still run them locally in your development environment, i.e. a devstack
installation.

To run integration tests, you will need to configure *tempest* accounts by
editing the :file:`/etc/tempest/accounts.yaml` file. For each entry of the
tempest account, you will need to provide values for ``username``,
``tenant_name``, ``password`` at least. For example:

.. code-block:: yaml

  - username: 'demo'
    tenant_name: 'demo'
    password: 'secretee'

After this is configured, you can run a specific test case using the following
command:

.. code-block:: console

  $ cd /opt/stack/senlin
  $ python -m testtools.run \
      senlin_tempest_plugin.tests.integration.test_nova_server_cluster


Writing Stress Test Cases
-------------------------

<TBD>


Running Stress Tests
--------------------

<TBD>
