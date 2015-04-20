Senlin Feature Request Pipeline
===============================

This document records the feature requests the developer team has received and
considered. This document SHOULD NOT be treated as a replacement of the
blueprints (or specs) which already accompanied with a design.  The feature
requests here are meant to be a pipeline for mid-term goals that Senlin should
strive to achieve. Whenever a feature can be implemented with a practical
design, the feature should be moved to a blueprint (and/or specs) review.

This document SHOULD NOT be treated as a replacement of the `TODO` file the
development team is maintaining. The `TODO` file records actionable work items
that can be picked up by any developer who is willing to do it, while this
document records more general requirements that needs at least a draft design
before being worked on.

-------------
High Priority
-------------

Event Listener
^^^^^^^^^^^^^^

To make Senlin responsive to events published by other OpenStack services, an
event subscriber is needed so that Senlin can receive notifications from
sources such as Ceilometer, Nova, or Zaqar.

This is of a high priority because Senlin needs it as one of its HA solutions.


Scavenger Process
^^^^^^^^^^^^^^^^^

Senlin needs a scavenger process that runs as a background daemon. It is
tasked with cleansing database for old data, e.g. event records. Its behavior
must be customizable because users may want the old records to be removed or
to be archived in a certain way.


---------------
Middle Priority
---------------

Horizon Plugin
^^^^^^^^^^^^^^

Senlin needs a plug-in at the OpenStack dashboard side so that users can
interact with the service in a more user-friendly way.


User Defined Actions
^^^^^^^^^^^^^^^^^^^^

Actions in Senlin are mostly built-in ones at present. There are requirements
to incorporate Shell scripts and/or other structured software configuration
tools into the whole picture. One of the option is to provide a easy way for
Senlin to work with Ansible, for example.


CoreOS based Container Support
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

To Senlin, CoreOS is just another VM image. However, CoreOS provides some
builtin support to Container/Docker and it provides clustering facility for
user applications.


Define and Enforce Quotas
^^^^^^^^^^^^^^^^^^^^^^^^^

There is a potential request to limit how many clusters a user can create, how
large a cluster can become.


Event Notification
^^^^^^^^^^^^^^^^^^

Event notification is a feature that enables an external tool to subscribe to
events sent from Senlin when interesting things happen. One option is to use
the messaging service provided by the Zaqar project.


Use Barbican to Store Secrets
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Currently, Senlin uses the `cryptography` package for data encryption and
decryption. There should be support for users to store credentials using the
Barbican service, in addition to the current solution.


Use VPNaaS to Build Cross-Region/Cross-Cloud
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

When buidling clusters that span more than one region or cloud, there are
requirements to place all cluster nodes on the same VPN so that workloads can
be distributed to the nodes as if they sit on the same network.


Make Use of Nova ServerGroup API
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

When creating a cluster of Nova servers, Senlin needs to work with Nova and its
scheduler to provide sophisticated scheduling decisions. While a user do not
necessarily have control over the admin plane, he or she does have a right to
express their requirements in an abstract manner.


------------
Low Priority
------------

Replace Green Threads with Python Threading
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Senlin is now using green threads (eventlets) for async executions. The
eventlets execution model is not making the use of multi-processing platforms
in an efficient way. Senlin needs a scalable execution engine, so native
multi-threading is needed.


Metrics Collection
^^^^^^^^^^^^^^^^^^

Senlin needs to support metric collections about the clusters and nodes it
manages. These metrics should be collectable by the ceilometer service, for
example.


AWS Compatible API
^^^^^^^^^^^^^^^^^^

There are requirements for Senlin to provide a AWS compatible API layer so
that existing workloads can be deployed to Senlin and AWS without needing to
change a lot of code or configurations.


Integration with Mistral
^^^^^^^^^^^^^^^^^^^^^^^^

There are cases where the (automated) operations on clusters and nodes form a
workflow. For example, an event triggers some actions to be executed in
sequence and those actions in turn triggers other actions to be executed.


Support to Suspend/Resume Operations
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

A user may want to suspend/resume a cluster or an individual node. Senlin
needs to provide a generic definition of 'suspend' and 'resume'. It needs to
be aware of whether the profile and the driver support such operations.


Support to Scheduled Actions
^^^^^^^^^^^^^^^^^^^^^^^^^^^^

This is a request to trigger some actions at a specified time. One typical use
case is to scale up a cluster before weekend or promotion season as a
preparation for the comming burst of workloads.


Interaction with Congress
^^^^^^^^^^^^^^^^^^^^^^^^^

This is of low priority because Senlin needs a notification mechanism in place
before it can talk to Congress. The reason to interact with Congress is that
there could be enterprise level policy enforcement that Senlin has to comply
to.


Integration with Tooz
^^^^^^^^^^^^^^^^^^^^^

There is potential requirement to do a better coordination between nodes in a
cluster. That is where the Tooz project can be leveraged.
