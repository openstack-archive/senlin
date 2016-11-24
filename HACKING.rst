Senlin Style Commandments
=========================

- Step 1: Read the OpenStack Style Commandments
  http://docs.openstack.org/developer/hacking/
- Step 2: Read on

Senlin Specific Commandments
----------------------------

- [S318] Use assertion ``assertIsNone(A)`` instead of ``assertEqual(A, None)``
         or ``assertEqual(None, A)``.
- [S319] Use ``jsonutils`` functions rather than using the ``json`` package
         directly.
- [S320] Default arguments of a method should not be mutable.
- [S321] The api_version decorator has to be the first decorator on a method.
- [S322] LOG.warn is deprecated. Enforce use of LOG.warning.
- [S323] Use assertTrue(...) rather than assertEqual(True, ...).

Working on APIs
---------------

If you are proposing new APIs or fixes to existing APIs, please spend some
time reading the guidelines published by the API WorkGroup:

http://git.openstack.org/cgit/openstack/api-wg/tree/guidelines

Any work on improving Senlin's APIs to conform to the guidelines are welcomed.

Creating Unit Tests
-------------------

For every new feature, unit tests should be created that both test and
(implicitly) document the usage of said feature. When submitting a patch to a
bug without a unit test, a new unit test should be added. If a submitted bug
fix does have a unit test, be sure to add a new one that fails without the
patch and passes with the patch.

For more information on creating and running unit tests , please read
senlin/doc/source/developer/testing.txt.


Running Tests
-------------

The testing system is based on a combination of `tox` and `testr`. The
canonical approach to running tests is to simply run the command `tox`.
This will create virtual environments, populate them with dependencies and
run all of the tests that OpenStack CI systems run.

Behind the scenes, `tox` is running `ostestr --slowest`, but is set up such
that you can supply any additional arguments to the `ostestr` command.
For example, the following command makes `tox` to tell `ostestr` to add
`--analyze-isolation` to its argument list::

  tox -- --analyze-isolation
