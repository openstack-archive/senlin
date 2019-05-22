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

========
Receiver
========

Concept
~~~~~~~

A :term:`Receiver` is an abstract resource created in Senlin engine to handle
operation automation. You can create a receiver to trigger a specific action
on a cluster on behalf of a user when some external alarms or events are
fired.

A receiver can be of different types. The ``type`` of a receiver is specified
when being created. Currently, two receiver types are supported: ``webhook``
and ``message``. For a ``webhook`` receiver, a :term:`Webhook` URI is generated
for users or programs to trigger a cluster action by send a HTTP POST request.
For a ``message`` receiver,  a Zaqar queue is created for users or programs to
trigger a cluster action by sending a message.

A receiver encapsulates the information needed for triggering an action. These
information may include:

* ``actor``: the credential of a user on whose behalf the action will be
  triggered. This is usually the user who created the receiver, but it can be
  any other valid user explicitly specified when the receiver is created.
* ``cluster_id``: the ID of the targeted cluster. It is required only for
  ``webhook`` receivers.
* ``action``: the name of an action that is applicable on a cluster. It is
  required only for ``webhook`` receivers.
* ``params``: a dictionary feeding argument values (if any) to the action. It
  is optional for all types of receivers.

In the long term, senlin may support user-defined actions where ``action``
will be interpreted as the UUID or name of a user-defined action.


Creating a Receiver
~~~~~~~~~~~~~~~~~~~

Creating a webhook receiver
---------------------------

When a user requests to create a webhook receiver by invoking the
:program:`openstack` command, the request comes with at least three
parameters: the receiver type which should be ``webhook``, the targeted
cluster and the intended action to invoke when the receiver is triggered.
Optionally, the user can provide some additional parameters to use and/or
the credentials of a different user.

When the Senlin API service receives the request, it does three things:

* Validating the request and rejects it if any one of the following conditions
  is met:

  - the receiver type specified is not supported;
  - the targeted cluster can not be found;
  - the targeted cluster is not owned by the requester and the requester does
    not have an "``admin``" role in the project;
  - the provided action is not applicable on a cluster.

* Creating a receiver object that contains all necessary information that will
  be used to trigger the specified action on the specified cluster.

* Creating a "channel" which contains information users can use to trigger
  a cluster action. For the ``webhook`` receiver, this is a URL stored in
  the ``alarm_url`` field and it looks like::

    http://{host:port}/v1/webhooks/{webhook_id}/trigger?V=2

  **NOTE**: The ``V=2`` above is used to encode the current webhook triggering
  protocol. When the protocol changes in future, the value will be changed
  accordingly.

Finally, Senlin engine returns a dictionary containing the properties of the
receiver object.

Creating a message receiver
---------------------------

When a user requests to create a message receiver by invoking :program:`openstack`
command, the receiver type ``message`` is the only parameter need to be specified.

When the Senlin API service receives the request, it does the following things:

* Validating the request and rejecting it if the receiver type specified is not
  supported;

* Creating a receiver object whose cluster_id and action properties are `None`;

* Creating a "channel" which contains information users can use to trigger
  a cluster action. For a ``message`` receiver, the following steps are
  followed:

  - Creating a Zaqar queue whose name has the ``senlin-receiver-`` prefix.
  - Building a trust between the requester (trustor) and the Zaqar trustee
    user (trustee) if this trust relationship has not been created yet.
    The ``trust_id`` will be used to create message subscriptions in the next
    step.
  - Creating a Zaqar subscription targeting on the queue just created and
    specifying the HTTP subscriber to the following URL::

      http://{host:port}/v1/v1/receivers/{receiver_id}/notify

  - Storing the name of queue into the ``queue_name`` field of the receiver's
    channel.

Finally, Senlin engine returns a dictionary containing the properties of the
receiver object.


Triggering a Receiver
~~~~~~~~~~~~~~~~~~~~~

Different types of receivers are triggered in different ways. For example, a
``webhook`` receiver is triggered via the ``alarm_url`` channel; a message
queue receiver can be triggered via messages delivered in a shared queue.


Triggering a Webhook
--------------------

When triggering a webhook, a user or a software sends a ``POST`` request to
the receiver's ``alarm_url`` channel, which is a specially encoded URL. This
request is first processed by the ``webhook`` middleware before arriving at
the Senlin API service.

The ``webhook`` middleware checks this request and parses the format of the
request URL. The middleware attempts to find the receiver record from Senlin
database and see if the named receiver does exist. If the receiver is found,
it then tries to load the saved credentials. An error code 404 will be
returned if the receiver is not found.

After having retrieved the credentials, the middleware will proceed to get a
Keystone token using credentials combined with Senlin service account info.
Using this token, the triggering request can proceed along the pipeline of
middlewares. An exception will be thrown if the authentication operation fails.

When the senlin engine service receives the webhook triggering request it
creates an action based on the information stored in the receiver object.
The newly created action is then dispatched and scheduled by a scheduler to
perform the expected operation.

Triggering a Message Receiver
-----------------------------

When triggering a message receiver, a user or a software needs to send
message(s) to the Zaqar queue whose name can be found from the channel data of
the receiver. Then the Zaqar service will notify the Senlin service for the
message(s) by sending a HTTP POST request to the Senlin subscriber URL.
Note: this POST request is sent using the Zaqar trustee user credential
and the ``trust_id`` defined in the subscriber. Therefore, Senlin will
recognize the requester as the receiver owner rather than the Zaqar service
user.

Then Senlin API then receives this POST request, parses the authentication
information and then makes a ``receiver_notify`` RPC call to the senlin engine.

The Senlin engine receives the RPC call, claims message(s) from Zaqar and then
builds action(s) based on payload contained in the message body. A message will
be ignored if any one of the following conditions is met:

  - the ``cluster`` or the ``action`` field cannot be found in message body;
  - the targeted cluster cannot be found;
  - the targeted cluster is not owned by the receiver owner and the receiver
    owner does not have "``admin``" role in the project;
  - the provided action is not applicable on a cluster.

Then those newly created action(s) will be scheduled to run to perform the
expected operation.

Credentials
~~~~~~~~~~~

Webhook Receiver
----------------

When requesting to create a ``webhook`` receiver, the requester can choose to
provide some credentials by specifying the ``actor`` property of the receiver.
This information will be used for invoking the webhook in the future. There
are several options to provide these credentials.

If the ``credentials`` to use is explicitly specified, Senlin will save it in
the receiver DB record. When the webhook is invoked later, the saved
credentials will be used for authentication with Keystone. Senlin engine
won't check if the provided credentials actually works when creating the
receiver. The check is postponed to the moment when the receiver is triggered.

If the ``credentials`` to use is not explicitly provided, Senlin will assume
that the receiver will be triggered in the future using the requester's
credential. To make sure the future authentication succeeds, Senlin engine
will extract the ``user`` ID from the invoking context and create a trust
between the user and the ``senlin`` service account, just like the way how
Senlin deals with other operations.

The requester must be either the owner of the targeted cluster or he/she has
the ``admin`` role in the project. This is enforced by the policy middleware.
If the requester is the ``admin`` of the project, Senlin engine will use the
cluster owner's credentials (i.e. a trust with the Senlin user in this case).


Message Receiver
----------------

When requesting to create a ``message`` receiver, the requester does not need
to provide any extra credentials. However, to enable token based authentication
for Zaqar message notifications, Zaqar trustee user information like
``auth_type``, ``auth_url``, ``username``, ``password``, ``project_name``,
``user_domain_name``, ``project_domain_name``, etc. must be configured in the
Senlin configuration file. By default, Zaqar trustee user is the same as Zaqar
service user, for example "zaqar". However, operators are also allowed to
specify other dedicated user as Zaqar trustee user for message notifying.
Therefore, please ensure Zaqar trustee user information defined in senlin.conf
are identical to the ones defined in zaqar.conf.
