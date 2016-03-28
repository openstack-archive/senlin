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

All unit tests are to be placed in the senlin/tests directory, and tests can
be organized by the targeted subsystems/modules. Each subsystem directory
must contain a separate blank __init__.py for tests discovery to function.

An example directory structure::

  senlin
    `-- tests
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

Implementing a test
-------------------

Testrepository - http://pypi.python.org/pypi/testrepository is used to
find and run tests, parallelize their runs, and record timing/results.

If new dependencies are introduced upon the development of a test, the
test-requirements.txt file needs to be updated so that the virtual
environment will be able to successfully execute all tests.

The `test-requirements.txt` file needs to be synchronized with the
openstack/global-requirements project. Developers should try avoid 
introducing additional package dependencies unless forced to.


Running Tests
~~~~~~~~~~~~~

Senlin uses `tox` for running unit tests, as practiced by many other OpenStack
projects::

  $ tox

This by default will run unit tests suite with Python 2.7 and PEP8/HACKING
style checks. To run only one type of tests you can explicitly provide `tox`
with the test environment to use::

  $ tox -epy27 # test suite on python 2.7
  $ tox -epep8 # run full source code checker

To run only a subset of tests, you can provide `tox` with a regex argument::

  $ tox -epy27 -- VolumeTests

To use debugger like `pdb` during test run, you have to run tests directly
with other, non-concurrent test runner instead of `testr`.
That also presumes that you have a virtual env with all senlin dependencies
installed and configured.

Below is an example bash script using `testtools` test runner that also allows
running single tests by providing a regex::

  #! /usr/bin/env sh
  testlist=$(mktemp)
  testr list-tests "$1" > $testlist
  python -m testtools.run --load-list $testlist

A more convenient way to run specific test is to name the unit test directly,
as shown below::

  $ python -m testtools.run senlin.tests.unit.db.test_cluster_api
