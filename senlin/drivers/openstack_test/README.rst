OpenStack Test Driver
=====================

This is a fake driver for Senlin test. All interactions between Senlin
and backend OpenStack services, like Nova, Heat are simulated using this
driver. With it, Senlin API and engine workflow can be easily tested
without setting up backend services.

Configure the following option in senlin.conf to enable this driver:

    `cloud_backend = openstack_test`
