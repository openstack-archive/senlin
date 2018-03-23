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

===================
API Microversioning
===================

Background
~~~~~~~~~~

The *API Microversioning* is a framework in Senlin to enable smooth evolution
of the Senlin REST API while preserving its backward compatibility. The basic
idea is that a user has to explicitly specify the particular version of API
requested in the request. Disruptive changes to the API can then be added
without breaking existing users who don't specifically ask for it. This is
done with an HTTP header ``OpenStack-API-Version`` as suggested by the
OpenStack API Working Group. The value of the header should contain the
service name (``clustering``) and the desired API version which is a
monotonically increasing semantic version number starting from ``1.0``.

If a user makes a request without specifying a version, they will get the
``DEFAULT_API_VERSION`` as defined in ``senlin.api.common.wsgi``.  This value
is currently ``1.0`` and is expected to remain so for quite a long time.

There is a special value "``latest``" which can be specified, which will allow
a client to always invoke the most recent version of APIs from the server.

.. warning:: The ``latest`` value is mostly meant for integration testing and
  would be dangerous to rely on in client code since Senlin microversions are
  not following semver and therefore backward compatibility is not guaranteed.
  Clients, like python-senlinclient or openstacksdk, python-openstackclient
  should always require a specific microversion but limit what is acceptable
  to the version range that it understands at the time.


When to Bump the Microversion
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

A microversion is needed when the contract to the user is changed. The user
contract covers many kinds of information such as:

- the Request

  - the list of resource URLs which exist on the server

    Example: adding a new ``GET clusters/{ID}/foo`` resource which didn't exist
    in a previous version of the code

  - the list of query parameters that are valid on URLs

    Example: adding a new parameter ``is_healthy`` when querying a node by
    ``GET nodes/{ID}?is_healthy=True``

  - the list of query parameter values for non-freeform fields

    Example: parameter ``filters`` takes a small set of properties "``A``",
    "``B``", "``C``", now support for new property "``D``" is added

  - new headers accepted on a request

  - the list of attributes and data structures accepted.

    Example: adding a new attribute ``'locked': True/False`` to a request body

- the Response

  - the list of attributes and data structures returned

    Example: adding a new attribute ``'locked': True/False`` to the output
    of ``GET clusters/{ID}``

  - the allowed values of non-freeform fields

    Example: adding a new allowed "``status``" field to ``GET servers/{ID}``

  - the list of status codes allowed for a particular request

    Example: an API previously could return 200, 400, 403, 404 and the
    change would make the API now also be allowed to return 409.

  - changing a status code on a particular response

    Example: changing the return code of an API from 501 to 400.

    .. note:: According to the OpenStack API Working Group, a
      **500 Internal Server Error** should **NOT** be returned to the user for
      failures due to user error that can be fixed by changing the request on
      the client side. This kind of a fix doesn't require a change to the
      microversion.

  - new headers returned on a response

The following flow chart attempts to walk through the process of "do
we need a microversion".


.. graphviz::

   digraph states {

    label="Do I need a microversion?"

    silent_fail[shape="diamond", style="", group=g1, label="Did we silently
   fail to do what is asked?"];
    ret_500[shape="diamond", style="", group=g1, label="Did we return a 500
   before?"];
    new_error[shape="diamond", style="", group=g1, label="Are we changing the
    status code returned?"];
    new_attr[shape="diamond", style="", group=g1, label="Did we add or remove
    an attribute to a resource?"];
    new_param[shape="diamond", style="", group=g1, label="Did we add or remove
    an accepted query string parameter or value?"];
    new_resource[shape="diamond", style="", group=g1, label="Did we add or
    remove a resource url?"];


   no[shape="box", style=rounded, label="No microversion needed"];
   yes[shape="box", style=rounded, label="Yes, you need a microversion"];
   no2[shape="box", style=rounded, label="No microversion needed, it's a bug"];

   silent_fail -> ret_500[label=" no"];
   silent_fail -> no2[label="yes"];

    ret_500 -> no2[label="yes [1]"];
    ret_500 -> new_error[label=" no"];

    new_error -> new_attr[label=" no"];
    new_error -> yes[label="yes"];

    new_attr -> new_param[label=" no"];
    new_attr -> yes[label="yes"];

    new_param -> new_resource[label=" no"];
    new_param -> yes[label="yes"];

    new_resource -> no[label=" no"];
    new_resource -> yes[label="yes"];

   {rank=same; yes new_attr}
   {rank=same; no2 ret_500}
   {rank=min; silent_fail}
   }


.. NOTE:: The reason behind such a strict contract is that we want application
  developers to be sure what the contract is at every microversion in Senlin.

  When in doubt, consider application authors. If it would work with no client
  side changes on both Nova versions, you probably don't need a microversion.
  If, however, there is any ambiguity, a microversion is likely needed.


When a Microversion Is Not Needed
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

A microversion is not needed in the following situations:

- the response

  - Changing the error message without changing the response code does not
    require a new microversion.

  - Removing an inapplicable HTTP header, for example, suppose the Retry-After
    HTTP header is being returned with a 4xx code. This header should only be
    returned with a 503 or 3xx response, so it may be removed without bumping
    the microversion.


Working with Microversions
~~~~~~~~~~~~~~~~~~~~~~~~~~

In the ``senlin.api.common.wsgi`` module, we define an ``@api_version``
decorator which is intended to be used on top-level methods of controllers.
It is not appropriate for lower-level methods.


Adding a New API Method
-----------------------

In the controller class:

.. code-block:: python

    @wsgi.Controller.api_version("2.4")
    def my_api_method(self, req, id):
        ....

This method is only available if the caller had specified a request header
``OpenStack-API-Version`` with value ``clustering <ver>`` and ``<ver>`` is >=
``2.4``. If they had specified a lower version (or omitted it thus got the
default of ``1.0``) the server would respond with HTTP 404.


Removing an API Method
----------------------

In the controller class:

.. code-block:: python

    @wsgi.Controller.api_version("2.1", "2.4")
    def my_api_method(self, req, id):
        ....

This method would only be available if the caller had specified an
``OpenStack-API-Version`` with value ``clustering <ver>`` and the ``<ver>`` is
<= ``2.4``. If ``2.5`` or later is specified the server will respond with
HTTP 404.


Changing a Method's Behavior
----------------------------

In the controller class:

.. code-block:: python

    @wsgi.Controller.api_version("1.0", "2.3")
    def my_api_method(self, req, id):
        .... method_1 ...

    @wsgi.Controller.api_version("2.4")  # noqa
    def my_api_method(self, req, id):
        .... method_2 ...

If a caller specified ``2.1``, ``2.2`` or ``2.3`` (or received the default of
``1.0``) they would see the result from ``method_1``, ``2.4`` or later
``method_2``.

It is vital that the two methods have the same name, so the second one will
need ``# noqa`` to avoid failing flake8's ``F811`` rule. The two methods may
be different in any kind of semantics (schema validation, return values,
response codes, etc.)


When Not Using Decorators
-------------------------

When you don't want to use the ``@api_version`` decorator on a method or you
want to change behavior within a method (say it leads to simpler or simply a
lot less code) you can directly test for the requested version with a method
as long as you have access to the API request object. Every API method has an
``version_request`` object attached to the ``Request`` object and that can be
used to modify behavior based on its value:

.. code-block:: python

    import senlin.api.common.version_request as vr

    def index(self, req):
        # common code ...

        req_version = req.version_request
        req1_min = vr.APIVersionRequest("2.1")
        req1_max = vr.APIVersionRequest("2.5")
        req2_min = vr.APIVersionRequest("2.6")
        req2_max = vr.APIVersionRequest("2.10")

        if req_version.matches(req1_min, req1_max):
            # stuff...
        elif req_version.matches(req2min, req2_max):
            # other stuff...
        elif req_version > vr.APIVersionRequest("2.10"):
            # more stuff...

        # common code ...

The first argument to the matches method is the minimum acceptable version
and the second is maximum acceptable version. A specified version can be null:

.. code-block:: python

    null_version = APIVersionRequest()

If the minimum version specified is null then there is no restriction on
the minimum version, and likewise if the maximum version is null there
is no restriction the maximum version. Alternatively an one sided comparison
can be used as in the example above.


Planning and Committing Changes
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Once the idea of an API change is discussed with the core team and the
consensus has been reached to bump the micro-version of Senlin API, you can
start working on the changes in the following order:

1. Prepare the engine and possibly the action layer for the change. One STRICT
   requirement is that the newly proposed change(s) should not break any
   existing users.

2. Add a new versioned object if a new API is introduced; or modify the fields
   of an existing object representing the API request. You are expected to
   override the ``obj_make_compatible()`` method to ensure the request formed
   will work on an older version of engine.

3. If the change is about modifying an existing API, you will need to bump the
   version of the request object. You are also required to add or change the
   ``VERSION_MAP`` dictionary of the request object class where the key is the
   API microversion and the value is the object version. For example:

.. code-block:: python

   @base.SenlinObjectRegistry.register
   class ClusterDanceRequest(base.SenlinObject):

       # VERSION 1.0: Initial version
       # VERSION 1.1: Add field 'style'
       VERSION = '1.1'
       VERSION_MAP = {
         'x.y': '1.1'
       }

       fields = {
         ...
         'style': fields.StringField(nullable=True),
       }

       def obj_make_compatible(self, primitive, target_version):
          # add the logic to convert the request for a target version
          ...


4. Patch the API layer to introduce the change. This involves changing the
   ``senlin/api/openstack/history.rst`` file to include the descriptive
   information about the changes made.

5. Revise the API reference documentation so that the changes are properly
   documented.

6. Add a release note entry for the API change.

7. Add tempest based API test and functional tests.

8. Update ``_MAX_API_VERSION`` in ``senlin.api.openstack.versions``, if needed.
   Note that each time we bump the API microversion, we may introduce two or
   more changes rather than one single change, the update of
   ``_MAX_API_VERSION`` needs to be done only once if this is the case.

9. Commit patches to the ``openstacksdk`` project so that new API
   changes are accessible from client side.

10. Wait for the new release of ``openstacksdk`` project that includes
    the new changes and then propose changes to ``python-senlinclient``
    project.


Allocating a microversion
~~~~~~~~~~~~~~~~~~~~~~~~~

If you are adding a patch which adds a new microversion, it is necessary to
allocate the next microversion number. Except under extremely unusual
circumstances, the minor number of ``_MAX_API_VERSION`` will be incremented.
This will also be the new microversion number for the API change.

It is possible that multiple microversion patches would be proposed in
parallel and the microversions would conflict between patches.  This will
cause a merge conflict. We don't reserve a microversion for each patch in
advance as we don't know the final merge order. Developers may need over time
to rebase their patch calculating a new version number as above based on the
updated value of ``_MAX_API_VERSION``.


.. include:: ../../../senlin/api/openstack/history.rst
