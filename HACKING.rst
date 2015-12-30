Senlin Style Commandments
=========================

- Step 1: Read the OpenStack Style Commandments
  http://docs.openstack.org/developer/hacking/
- Step 2: Read on

Senlin Specific Commandments
----------------------------

- [S318] Change assertEqual(A, None) or assertEqual(None, A) by optimal assert
  like assertIsNone(A)

Working on APIs
---------------

If you are proposing new APIs or fixes to existing APIs, please spend some
time reading the guidelines published by the API WorkGroup:

http://git.openstack.org/cgit/openstack/api-wg/tree/guidelines

Any work on improving Senlin's APIs to conform to the guidelines are welcomed.

Creating Unit Tests
-------------------
For every new feature, unit tests should be created that both test and
(implicitly) document the usage of said feature. If submitting a patch for a
bug that had no unit test, a new passing unit test should be added. If a
submitted bug fix does have a unit test, be sure to add a new one that fails
without the patch and passes with the patch.

For more information on creating and running unit tests , please read
senlin/doc/source/testing.txt.


Running Tests
-------------

The testing system is based on a combination of `tox` and `testr`. The
canonical approach to running tests is to simply run the command `tox`.
This will create virtual environments, populate them with dependencies and
run all of the tests that OpenStack CI systems run.

Behind the scenes, `tox` is running `testr run --parallel`, but is set up
such that you can supply any additional `testr` arguments that are needed
by `tox`. For example, the following command makes `tox` to tell `testr` to
add `--analyze-isolation` to its argument list::

  tox -- --analyze-isolation

It is also possible to run the tests inside of a virtual environment
you have created, or it is possible that you have all of the dependencies
installed locally already. In this case, you can interact with the testr
command directly. Running `testr run` will run the entire test suite. `testr
run --parallel` will run it in parallel (this is the default incantation tox
uses.) More information about testr can be found at:
http://wiki.openstack.org/testr

