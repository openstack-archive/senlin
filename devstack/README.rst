===========================
Enabling senlin in DevStack
===========================

1. Download DevStack::

     $ git clone https://git.openstack.org/openstack-dev/devstack
     $ cd devstack

2. Add following repo as external repositories into your ``local.conf`` file::

     [[local|localrc]]
     #Enable senlin
     enable_plugin senlin https://git.openstack.org/openstack/senlin
     #Enable senlin-dashboard
     enable_plugin senlin-dashboard https://git.openstack.org/openstack/senlin-dashboard

Optionally, you can add a line ``SENLIN_USE_MOD_WSGI=True`` to the same ``local.conf``
file if you prefer running the Senlin API service under Apache.

3. Run ``./stack.sh``.
