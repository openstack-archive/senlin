Before You Start
================

If you would like to contribute to the development of OpenStack,
you must follow the steps in this page:

   https://docs.openstack.org/infra/manual/developers.html

Once those steps have been completed, changes to OpenStack
should be submitted for review via the Gerrit tool, following
the workflow documented at:

   https://docs.openstack.org/infra/manual/developers.html#development-workflow


Where to Start
==============

There are many ways to start your contribution.

Sign on a bug to fix
--------------------

Bugs related to senlin are reported and tracked on the individual sites on
Launchpad:

- Senlin Server: https://bugs.launchpad.net/senlin
- Senlin Client: https://bugs.launchpad.net/python-senlinclient
- Senlin Dashboard: https://bugs.launchpad.net/senlin-dashboard

You can pick any bug item that has not been assigned to work on. Each bug fix
patch should be accompanied with a release note.


Pick a TODO item
----------------

Senlin team maintains a ``TODO.rst`` file under the root directory, where you
can add new items, claim existing items and remove items that are completed.
You may want to check if there are items you can pick by:

#. Propose a patch to remove the item from the ``TODO.rst`` file.
#. Add an item to the `etherpad page`_ which the core team uses to track the
   progress of individual work items.
#. Start working on the item and keep updating your progress on the `etherpad
   page`_, e.g. paste the patch review link to the page.
#. Mark the item from the `etherpad page`_ as completed when the patches are
   all merged.


Start a Bigger Effort
---------------------

Senlin team also maintains a ``FEATURES.rst`` file under the root directory,
where you can add new items by proposing a patch to the file or claim an item
to work on. However, the work items in the ``FEATURES.rst`` file are all
non-trivial, thus demands for a deeper discussion before being worked on. The
expected workflow for these items is:

#. Propose a spec file to the ``doc/specs`` directory describing the detailed
   design and other options, if any.
#. Work with the reviewers to polish the design until it is accepted.
#. Propose blueprint(s) to track the progress of the work item by registering
   them at the `blueprint page`_.
#. Start working on the blueprints and checking in patches. Each patch should
   have a ``partial-blueprint: <blueprint>`` tag in its commit message.
#. For each blueprint, add an item to the `etherpad page`_ so that it can be
   closely tracked in weekly meetings.
#. Mark the blueprint(s) as completed when all related patches are merged.
#. Propose a patch to the ``FEATURES.rst`` file to remove the work item.
#. Propose a separate release note patch for the new feature. 


Reporting Bugs
==============

Bugs should be filed on Launchpad site:

- Senlin Server: https://bugs.launchpad.net/senlin
- Senlin Client: https://bugs.launchpad.net/python-senlinclient
- Senlin Dashboard: https://bugs.launchpad.net/senlin-dashboard


Meet the Developers
===================

Real-time communication among developers are mostly done via IRC.
The team is using the #senlin channel on oftc.net.

.. _`etherpad page`: https://etherpad.openstack.org/p/senlin-newton-workitems
.. _`blueprint page`: https://blueprints.launchpad.net/senlin
