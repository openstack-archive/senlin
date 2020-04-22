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


=================
Event Dispatchers
=================

An event :term:`dispatcher<Dispatcher>` is a processor that converts a given action in
Senlin engine into certain format and then persists it into some storage or
sends it to downstream processing software.

Since version 3.0.0, Senlin comes with some built-in dispatchers that can
dump event records into database and/or send event notifications via the
default message queue. The former is referred to as the ``database`` dispatcher
which is enabled by default; the latter is referred to as the ``message``
dispatcher which has to be manually enabled by adding the following line to
the ``senlin.conf`` file::

  event_dispatchers = message

However, the distributors or the users can always add their own event
dispatchers easily when needed.

Event dispatchers are managed as Senlin plugins. Once a new event dispatcher
is implemented, a deployer can enable it by first adding a new item to the
``senlin.dispatchers`` entries in the ``entry_points`` section of the
``setup.cfg`` file, followed by a reinstall of the Senlin service, i.e.
``sudo pip install`` command.


The Base Class ``EventBackend``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

All event dispatchers are expected to subclass the base class ``EventBackend``
in the ``senlin.events.base`` module. The only requirement for a dispatcher
subclass is to override the ``dump()`` method that implements the processing
logic.


Providing New Dispatchers
~~~~~~~~~~~~~~~~~~~~~~~~~

Developing A New Event Dispatcher
---------------------------------

The first step for adding a new dispatcher is to create a new file containing
a subclass of ``EventBackend``. In this new class, say ``JsonDispatcher``,
you will need to implement the ``dump()`` class method as exemplified below:

.. code-block:: python

  class JsonDispatcher(base.EventBackend):
      """Dispatcher for dumping events to a JSON file."""

      @classmethod
      def dump(cls, level, action, **kwargs):
          # Your logic goes here
          ...

The ``level`` parameter for the method is identical to that defined by the
``logging`` module of Python. It is an integer representing the criticality
of an event. The ``action`` parameter is an instance of Senlin action class,
which is defined in the ``senlin.engine.actions.base`` module. There is
virtually no constraints on which properties you will pick and how you want to
process them.

Finally, the ``**kwargs`` parameter may provide some useful fields for you
to use:

* ``timestamp``: A datetime value that indicates when the event was generated.
* ``phase``: A string value indicating the phase an action is in. Most of the
  time this can be safely ignored.
* ``reason``: There are some rare cases where an event comes with a textual
  description. Most of the time, this is empty.
* ``extra``: There are even rarer cases where an event comes with some
  additional fields for attention. This can be safely ignored most of the
  time.


Registering the New Dispatcher
------------------------------

For Senlin service to be aware of and thus to make use of the new dispatcher,
you will register it to the Senlin engine service. This is done by editing the
``setup.cfg`` file in the root directory of the code base, for example:

::

  [entry_points]
  senlin.dispatchers =
      database = senlin.events.database:DBEvent
      message = senlin.events.message:MessageEvent
      jsonfile = <path to the dispatcher module>:<dispatch class name>

Finally, save that file and do a reinstall of the Senlin service, followed
by a restart of the ``senlin-engine`` process.

::

  $ sudo pip install -e .


Dynamically Enabling/Disabling a Dispatcher
-------------------------------------------

All dispatchers are loaded when the Senlin engine is started, however, they
can be dynamically enabled or disabled by editing the ``senlin.conf`` file.
The option ``event_dispatchers`` in the ``[DEFAULT]`` section is a multi-string
value option for this purpose. To enable your dispatcher (i.e. ``jsonfile``),
you will need to add the following line to the ``senlin.conf`` file:

::

  event_dispatchers = jsonfile
