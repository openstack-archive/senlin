================================
Building the user and admin docs
================================

This documentation should eventually end up in the OpenStack documentation
repositories `api-site` and `openstack-manuals`.

Dependencies
============

on Ubuntu:
::

  $ sudo apt-get install maven

on Fedora Core:
::

  $ sudo yum install maven

Use `mvn`
=========

Build the Senlin admin guide:
::

  $ cd senlin-admin
  $ mvn clean generate-sources

