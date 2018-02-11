..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

====================================
Generic Event Interface and Backends
====================================

The URL of the launchpad blueprint:

https://blueprints.launchpad.net/senlin/+spec/generic-event

Currently senlin has a DB backend to log events that might be interested to
users/operators. However, we will also need to send out event notifications
for integration with 3rd party software/services. Users/operators may want to
dump the events into a file or a time series database for processing.

The blueprint proposes a generic interface for dumping events/notifications.
Such an interface can be implemented by different backends as event plugins.

Problem description
===================

While the Senlin engine is operating clusters or nodes, interacting with other
services or enforcing policies, there are many cases where the operations
(and the results) should be dumped.

Currently, Senlin only has a builtin event table in database. It is
accumulating very fast, it is not flexible and the content is not versioned.

To integrate with other services, Senlin will need to generate and send
notifications when certain events happen. More complex (pre-)processing can
be offloaded to service dedicated to this task (e.g. Panko from Ceilomter),
but the basic notifications should always come from the engine.
(Note that we treat "notifications" as a special form of events, i.e. they
are "events on the wire", they are events sent to a message queue for other
services/software to consume.)

As Senlin evolves, changes are inevitable regarding to the content of the
payload of such events and/or notifications. To best protect users investment
in downstream event processing, we will need to be very explicit about the
content and format of each and every event/notification.

The format of event/notification should be well documented so that users or
developers of downstream software don't need digging into Senlin's source code
to find out the exact format of each event type or notification type. This
should remain true even when the event/notification format evolves over time.

There is no one-size-fits-all solution that meets all requirements from the
use cases enumerated in the "Use Cases" subsection below. The event generation
has to be an open framework, with a generic interface, that allows for
diversified backend implementation, aka, drivers.

Events or notifications are inherently of different criticality or severity.
Users should be able to filter the events by their severity easily. Similarly,
events or notifications are generated from different types of modules, e.g.
``engine``, ``profile``, ``policy``, we may want to enable an operator to
specify the sources of events to include or exclude. Note the source-based
filtering is not a high priority requirement as we see it today.

Use Cases
---------

The dumping of events could serve several use cases:

- Problem diagnosis: Although there are cases where users can check the logs
  from the engine (let's suppose we are already dumping rich information
  already), it is unlikely that everyone is granted access to the raw log
  files. Event logs are a replacement for raw log files.
- Integration with Other Software: When building a solution by integrating
  Senlin with other software/services, the said service may need Senlin to
  emit events of interests so that some operations can be adjusted
  dynamically.
- Auditing: In the case where there are auditing requirements regarding
  user behavior analysis or resource usage tracking, a history of user
  operations would be very helpful to conduct this kind of analysis.

Proposed change
===============

Add an interface definition for event logging and notification. This will be
an unified interface for all backends. The interface is a generalization of
the existing event dumping support.

Make the existing event module (which is dumping events into DB tables) a
plugin that implements the logging interface.

Model all events dumped today as versioned objects. Different event types will
use different objects. This will be done by preserving the existing DB schema
of the ``event`` table if possible. And, more importantly, the event
abstraction should match the expectations from notification interface from
the ``oslo.messaging`` package. We will learn from the versioned notification
design from Nova but we are going one step further.

Add filters for event/notification generation, regarding the sererity and the
source. Expose these filters as configurable options in ``senlin.conf``.
These filters (among others) may deserve a new section, but we will decide
when we are there.

Add stevedore plugin loading support to logging, with "``database``" and
"``messaging``" set as default. We may add a ``json file`` backend
for demonstration's purpose, but that is optional. The backend of event
logging (and notification) will be exposed as a multi-string configuration
option in ``senlin.conf``.

Following the "api-ref" scheme for API documentation, we will document the
formats of all events/notifications in REST files.

Alternatives
------------

Keep the event generation and notification separate. This seems a duplication
of a lot logic. From the source location where you want to fire an event and
also a log and also a notification, you may have to do three calls.

Data model impact
-----------------

We will strive to keep the existing DB schema (especially the ``event`` table
format) unless we have a good reason to add columns.

REST API impact
---------------

There is no change to REST API planned.

Security impact
---------------

One thing we not so sure is where to draw the line between "proper" and
"excessive" dumping of events. We will need some profiling when trading things
off.

Both events and notifications will leverage the multi-tenancy support (i.e.
``project`` will be include in the payload), so tenant isolation won't be a
problem.

Notifications impact
--------------------

Well... this spec is about constructing the infrastructure for notification,
in addition to events and logs.

Other end user impact
---------------------

Users will be able to see notifications from Senlin in the message queue.
Users will get detailed documentation about the event/notification format.

No change to python-senlinclient will be involved.

There could be changes to senlin-dashboard if we change the response from the
``event-list`` or ``event-show`` API, but that is not expected.

Performance Impact
------------------

* An overloaded message queue may lead to slower response of senlin-engine?
  Not quite sure.

* An overloaded DBMS may slow down the senlin-engine.

* High frequency of event generation, based on common sense, will impact the
  service performance.

Other deployer impact
---------------------

There is no new dependency to other packages planned.

There will be several new config options added. We will make them as generic
as possible because the infrastructure proposed is a generic one. We will
include database and message as the default backend, which should work in
most real deployments.

The changes to the configuration file will be documented in release notes.

Developer impact
----------------

There will be some reference documents for event/notification format design
for developers of downstream software/service.

There will be some developer documents for adding new logging backends.


Implementation
==============

Assignee(s)
-----------

Primary assignee:
  Qiming <tengqim@cn.ibm.com>

Other contributors:
  Anyone who wish to adventure ...

Work Items
----------

Currently identified work items:

- Abstract class (interface) for logging;
- Rebase event dumping module onto this interface;
- Versioned objects for existing events;
- Driver for dumping events (thus become notifications) to message queue;
- Dynamic loading of both backends (database and message);
- Configuration options for backend selection and customization;
- Documentation of event formats;
- User documentation for events (improvement);
- Developer documentation for new logging backends;

Dependencies
============

No dependency on other specs/bps/projects.

Need to watch changes in ``oslo.messaging`` and ``oslo.versionedobjects`` to
tune the implementation.

Testing
=======

Only unit tests are planned.

There is not yet plan for API test, functional test, stress test or
integration test.

Documentation Impact
====================

New documentation:

- Documentation of event formats;
- User documentation for events (improvement);
- Developer documentation for new logging backends;
- Release notes

References
==========

N/A

History
=======

.. list-table:: Revisions
   :header-rows: 1

   * - Release Name
     - Description
   * - Ocata
     - Introduced
