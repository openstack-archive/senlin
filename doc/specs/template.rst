..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

==========================================
Example Spec - The title of your blueprint
==========================================

Include the URL of your launchpad blueprint:

https://blueprints.launchpad.net/senlin/+spec/example

Introduction paragraph -- why are we doing anything? A single paragraph of
prose that operators can understand. The title and this first paragraph
should be used as the subject line and body of the commit message
respectively.

Some notes about the senlin spec and blueprint process:

* Not all blueprints need a spec. A blueprint is primarily used for tracking
  a series of changes which could be easy to implement and easy to review.
  A spec, on the other hand, usually warrants a discussion among the
  developers (and reviewers) before work gets started.

* The aim of this document is first to define the problem we need to solve,
  and second agree the overall approach to solve that problem.

* This is not intended to be extensive documentation for a new feature.
  For example, there is no need to specify the exact configuration changes,
  nor the exact details of any DB model changes. But you should still define
  that such changes are required, and be clear on how that will affect
  upgrades.

* You should aim to get your spec approved before writing your code.
  While you are free to write prototypes and code before getting your spec
  approved, its possible that the outcome of the spec review process leads
  you towards a fundamentally different solution than you first envisaged.

* API changes are held to a much higher level of scrutiny. As soon as an API
  change merges, we must assume it could be in production somewhere, and as
  such, we then need to support that API change forever. To avoid getting that
  wrong, we do want lots of details about API changes upfront.

Some notes about using this template:

* Please wrap text at 79 columns.

* The filename in the git repository should match the launchpad URL, for
  example a URL of: https://blueprints.launchpad.net/senlin/+spec/some-thing
  should be named ``some-thing.rst``.

* Please do not delete any of the *sections* in this template.  If you have
  nothing to say for a whole section, just write: None

* For help with syntax, see http://www.sphinx-doc.org/en/stable/rest.html

* To test out your formatting, build the docs using tox and see the generated
  HTML file in doc/build/html/specs/<path_of_your_file>

* If you would like to provide a diagram with your spec, ascii diagrams are
  required.  http://asciiflow.com/ is a very nice tool to assist with making
  ascii diagrams.  The reason for this is that the tool used to review specs is
  based purely on plain text.  Plain text will allow review to proceed without
  having to look at additional files which can not be viewed in gerrit.  It
  will also allow inline feedback on the diagram itself.

* If your specification proposes any changes to the Nova REST API such as
  changing parameters which can be returned or accepted, or even the semantics
  of what happens when a client calls into the API, then you should add the
  ``APIImpact`` flag to the commit message. Specs and patches with the
  ``APIImpact`` flag can be found with the following query:

  https://review.openstack.org/#/q/status:open+project:openstack/senlin+message:apiimpact,n,z


Problem description
===================

A detailed description of the problem. What problem is this spec addressing?

Use Cases
---------

What use cases does this address?
What are the impacts on actors (developer, end user, deployer etc.)?

Proposed change
===============

Detail here the changes you propose to make with the scope clearly defined.

At this point, if you would like to just get feedback on if the problem and
proposed change fit in senlin, you can stop here and post this for review to
get early feedback.

Alternatives
------------

What are the other ways we could do this? Why aren't we using those?

This doesn't have to be a full literature review, but it should demonstrate
that thought has been put into why the proposed solution is an appropriate one.

Data model impact
-----------------

What are the new data objects and/or database schema changes, if any?

What database migrations will accompany this change?

How will the initial set of new data objects be generated?
For example if you need to consider the existing resources or modify other
existing data, describe how that will work.

REST API impact
---------------

For each API added/changed, clarify the followings:

* Method Specification

  - A description of what the method does, suitable for use in user doc;

  - Method type (POST/PUT/PATCH/GET/DELETE)

  - Normal http response code(s)

  - Expected error http response code(s)

    + A description for each possible error code should be included describing
      semantic errors which can cause it such as inconsistent parameters
      supplied to the method, or when an object is not in an appropriate state
      for the request to succeed. Errors caused by syntactic problems covered
      by the JSON schema definition do not need to be included.

  - URL for the resource

    + URL should not include underscores, and use hyphens instead.

  - Parameters which can be passed via the URL

  - Request body definition in JSON schema, if any, with sample

    * Field names should use snake_case style, not CamelCase

  - Response body definition in JSON schema, if any, with sample

    * Field names should use snake_case style, not CamelCase

* Policy changes to be introduced

  - Other things a deployer needs to think about when defining their policy.

Note that the request/response schema should be defined as restrictively as
possible. Parameters which are required should be marked as such and only
under exceptional circumstances should additional parameters which are not
defined in the schema be permitted.

Reuse of existing predefined parameter types such as regexps for passwords and
user defined names is highly encouraged.

Security impact
---------------

Describe any potential security impact on the system.  Some of the items to
consider include:

* Does this change touch sensitive data such as tokens, keys, or user data?

* Does this change alter the API in a way that may impact security, such as
  a new way to access sensitive information or a new way to login?

* Does this change involve cryptography or hashing?

* Does this change require the use of sudo or any elevated privileges?

* Does this change involve using or parsing user-provided data? This could
  be directly at the API level or indirectly such as changes to a cache layer.

* Can this change enable a resource exhaustion attack, such as allowing a
  single API interaction to consume significant server resources? Examples
  of this include launching subprocesses for each connection, or entity
  expansion attacks in XML.

For more detailed guidance, please see the OpenStack Security Guidelines as
a reference (https://wiki.openstack.org/wiki/Security/Guidelines). These
guidelines are a work in progress and are designed to help you identify
security best practices. For further information, feel free to reach out
to the OpenStack Security Group at openstack-security@lists.openstack.org.

Notifications impact
--------------------

Please specify any changes to notifications, including:

- adding new notification,
- changing an existing notification, or
- removing a notification.

Other end user impact
---------------------

Aside from the API, are there other ways a user will interact with this
feature?

* Does this change have an impact on python-senlinclient?

* What does the user interface there look like?

Performance Impact
------------------

Describe any potential performance impact on the system, for example
how often will new code be called, and is there a major change to the calling
pattern of existing code.

Examples of things to consider here include:

* A periodic task manipulating a cluster node implies workload which will be
  multiplied by the size of a cluster.

* Any code interacting with backend services (e.g. nova or heat) may introduce
  some latency which linear to the size of a cluster.

* A small change in a utility function or a commonly used decorator can have a
  large impacts on performance.

* Calls which result in a database queries can have a profound impact on
  performance when called in critical sections of the code.

* Will the change include any locking, and if so what considerations are there
  on holding the lock?

Other deployer impact
---------------------

Other impacts on how you deploy and configure OpenStack, such as:

* What config options are being added? Should they be more generic than
  proposed? Will the default values work well in real deployments?

* Is this a change that takes immediate effect after its merged, or is it
  something that has to be explicitly enabled?

* If this change involves a new binary, how would it be deployed?

* Please state anything that those doing continuous deployment, or those
  upgrading from the previous release, need to be aware of. Also describe
  any plans to deprecate configuration values or features.

Developer impact
----------------

Discuss things that will affect other developers, such as:

* If the blueprint proposes a change to the driver API, discussion of how
  other drivers would implement the feature is required.

* Does this change have an impact on openstacksdk?


Implementation
==============

Assignee(s)
-----------

Who is leading the writing of the code? Or is this a blueprint where you're
throwing it out there to see who picks it up?

If more than one person is working on the implementation, please designate the
primary author and contact.

Primary assignee:
  <launchpad-id or None>

Other contributors:
  <launchpad-id or None>

Work Items
----------

Work items or tasks -- break the feature up into the things that need to be
done to implement it. Those parts might end up being done by different people,
but we're mostly trying to understand the timeline for implementation.


Dependencies
============

* Include specific references to specs and/or blueprints, or in other
  projects, that this one either depends on or is related to.

* If this requires functionality of another project that is not currently
  used by senlin, document that fact.

* Does this feature require any new library dependencies or code otherwise
  not included in OpenStack? Or does it depend on a specific version of
  library?


Testing
=======

Please discuss how the change will be tested, especially what tempest tests
will be added. It is assumed that unit test coverage will be added so that
doesn't need to be mentioned explicitly, but discussion of why you think
unit tests are sufficient and we don't need to add more tempest tests would
need to be included.

Please discuss the important scenarios needed to test here, as well as
specific edge cases we should be ensuring work correctly. For each
scenario please specify if this requires a full openstack environment, or
can be simulated inside the senlin tree.


Documentation Impact
====================

Which audiences are affected most by this change, and which documentation
titles on docs.openstack.org should be updated because of this change?

Don't repeat details discussed above, but reference them here in the context of
documentation for multiple audiences. For example, the Operations Guide targets
cloud operators, and the End User Guide would need to be updated if the change
offers a new feature available through the CLI or dashboard. If a config option
changes or is deprecated, note here that the documentation needs to be updated
to reflect this specification's change.

References
==========

Please add any useful references here. You are not required to have any
reference. Moreover, this specification should still make sense when your
references are unavailable. Examples of what you could include are:

* Links to mailing list or IRC discussions

* Links to notes from a summit session

* Links to relevant research, if appropriate

* Related specifications as appropriate

* Anything else you feel it is worthwhile to refer to


History
=======

Optional section intended to be used each time the spec is updated to describe
new design, API or any database schema updated. Useful to let reader understand
what's happened along the time.

.. list-table:: Revisions
   :header-rows: 1

   * - Release Name
     - Description
   * - Ocata
     - Introduced
