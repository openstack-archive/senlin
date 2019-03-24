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

.. _tutorial-basic:

=============
Senlin Basics
=============

.. note::

  This tutorial assumes that you are working on the master branch of the
  senlin source code which contains the latest profile samples and policy
  samples. To clone the latest code base:

  .. code-block:: console

    $ git clone https://git.openstack.org/openstack/senlin.git

Follow the `Installation Guide`_ to install the senlin service.


Creating Your First Profile
~~~~~~~~~~~~~~~~~~~~~~~~~~~

A profile captures the necessary elements you need to create a node. The
following is a profile specification (``spec`` for short) that can be used
to create a nova server:

.. literalinclude:: ../../../examples/profiles/nova_server/cirros_basic.yaml
   :language: yaml

.. note::
  The above source file can be found in senlin source tree at
  ``/examples/profiles/nova_server/cirros_basic.yaml``.

The **spec** assumes that:

- you have a nova keypair named ``oskey``, and
- you have a neutron network named ``private``, and
- there is a glance image named ``cirros-0.3.5-x86_64-disk``

You may have to change the values based on your environment setup before using
this file to create a profile. After the **spec** file is modified properly,
you can use the following command to create a profile object:

.. code-block:: console

  $ cd $SENLIN_ROOT/examples/profiles/nova_server
  $ openstack cluster profile create --spec-file cirros_basic.yaml myserver

Check the :doc:`Profiles <../user/profiles>` section in the
:ref:`user-references` documentation for more details.

Creating Your First Cluster
~~~~~~~~~~~~~~~~~~~~~~~~~~~

With a profile created, we can proceed to create a cluster by specifying the
profile and a cluster name.

.. code-block:: console

  $ openstack cluster create --profile myserver mycluster

If you don't explicitly specify a number as the desired capacity of the
cluster, senlin won't create nodes in the cluster. That means the newly
created cluster is empty. If you do provide a number as the desired capacity
for the cluster as shown below, senlin will create the specified number of
nodes in the cluster.

.. code-block:: console

  $ openstack cluster create --profile myserver --desired-capacity 1 mycluster
  $ openstack cluster show mycluster

For more details, check the :doc:`Creating a Cluster <../user/clusters>`
section in the :ref:`user-references` documentation.


Scaling a Cluster
~~~~~~~~~~~~~~~~~

Now you can try to change the size of your cluster. To increase the size,
use the following command:

.. code-block:: console

  $ openstack cluster expand mycluster
  $ openstack cluster show mycluster

To decrease the size of the cluster, use the following command:

.. code-block:: console

  $ openstack cluster shrink mycluster
  $ openstack cluster show mycluster

For more details, please check the :doc:`Resizing a Cluster <../user/clusters>`
section in the :ref:`user-references` section.


Resizing a Cluster
~~~~~~~~~~~~~~~~~~

Yet another way to change the size of a cluster is to use the command
``cluster-resize``:

.. code-block:: console

  $ openstack cluster resize --capacity 2 mycluster
  $ openstack cluster show mycluster

The ``cluster-resize`` command supports more flexible options to control how
a cluster is resized. For more details, please check the
:doc:`Resizing a Cluster <../user/clusters>` section in the
:ref:`user-references` section.


Creating a Node
---------------

Another way to manage cluster node membership is to create a standalone node
then add it to a cluster. To create a node using a given profile:

.. code-block:: console

  $ openstack cluster node create --profile myserver newnode
  $ openstack cluster node show newnode

For other options supported by the ``node-create`` command, please check the
:doc:`Creating a Node <../user/nodes>` subsection in the
:ref:`user-references` documentation.


Adding a Node to a Cluster
--------------------------

If a node has the same profile type as that of a cluster, you can add the node
to the cluster using the ``cluster-node-add`` command:

.. code-block:: console

  $ openstack cluster members add --nodes newnode mycluster
  $ openstack cluster members list mycluster
  $ openstack cluster show mycluster
  $ openstack cluster node show newnode

After the operation is completed, you will see that the node becomes a member
of the target cluster, with an index value assigned.

Removing a Node from a Cluster
------------------------------

You can also remove a node from a cluster using the ``cluster-node-del``
command:

.. code-block:: console

  $ openstack cluster members del --nodes newnode mycluster
  $ openstack cluster members list mycluster
  $ openstack cluster show mycluster
  $ openstack cluster node show newnode

For other cluster membership management commands and options, please check the
:doc:`Cluster Membership <../user/membership>` section in the
:ref:`user-references` section.


.. _Installation Guide: https://docs.openstack.org/senlin/latest/install
