====================
Tempest Integration
====================

This directory contains Tempest tests to cover senlin project.

To list all senlin tempest cases, go to tempest directory, then run::

    $ testr list-tests senlin

To run only these tests in tempest, go to tempest directory, then run::

    $ ./run_tempest.sh -N -- senlin

To run a single test case, go to tempest directory, then run with test case name, e.g.::

    $ ./run_tempest.sh -N -- senlin.tests.tempest_tests.tests.api.test_cluster_basic.TestClusterBasic.test_cluster_create_delete