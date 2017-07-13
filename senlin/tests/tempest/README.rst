====================
Tempest Integration
====================

This directory contains Tempest tests to cover senlin project.

To list all senlin tempest cases, go to tempest directory, then run::

    $ testr list-tests senlin

To run only these tests in tempest, go to tempest directory, then run::

    $ ./run_tempest.sh -N -- senlin

To run a single test case, go to tempest directory, then run with test case name, e.g.::

    $ ./run_tempest.sh -N -- senlin.tests.tempest.api.test_cluster_basic.TestClusterBasic.test_cluster_create_delete

If you can't find run_tempest.sh script in tempest directory, that means the script has been removed in a certain version.
Then you can use "nosetests -v" to replace "./run_tempest.sh -N" in above command.
More information about running tempest test can be found here: https://docs.openstack.org/tempest/latest/
