How To Use the Sample Spec File
===============================

This directory contains a sample spec file that can be used to create a
profile of type 'os.heat.stack'. It demonstrates how to use environment
files when creating a profile and how to assign default parameters for
the stack to use. In addition to that, it shows an example about making
use of the 'get_file' function supported by Heat.

To create a profile using the spec, use the following command::

  senlin profile-create \
    -s heat_stack_random_string.yaml \
    -p 1111
    my_stack

To get help on the command line options for creating profiles::

  senlin profile-create

To show the profile created::

  senlin profile-show <profile_id>
