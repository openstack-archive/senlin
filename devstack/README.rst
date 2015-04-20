====================
Devstack Integration
====================

This directory contains the files necessary to integrate Senlin with devstack.

Refer the quickstart guide for more information on using devstack and senlin.

To install senlin into devstack, add the following settings to enable senlin plugin: ::

     [[local|localrc]]
     enable_plugin senlin https://github.com/stackforge/senlin master
     enable_service sl-api sl-eng

Run devstack as normal: ::

    cd /opt/stack/devstack
    ./stack.sh
