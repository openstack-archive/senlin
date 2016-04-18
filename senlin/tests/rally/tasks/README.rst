This is the directory to hold Rally test jobs for Senlin benchmarking.

To run a single rally test job, use the following cmd:

 $rally task start tempest_cluster_create_delete.yaml

Note: Before Rally supports to install tempest plugin for specified
deployment, manual installation of Senlin tempest plugin in Rally's
tempest virtual environment is necessary for benchmarking Senlin with
existing tempest test cases.
