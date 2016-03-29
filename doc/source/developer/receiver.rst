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
when being created. For example, the most common type of receiver is
``webhook``, where a :term:`Webhook` is a URI that can be accessed from any
user or program.

A receiver encapsulates the information needed for triggering an action. These
information include:

* ``actor``: the credential of a user on whose behalf the action will be
  triggered. This is usually the user who created the receiver, but it can be
  any other valid user explicitly specified when the receiver is created.
* ``cluster_id``: the ID of the targeted cluster.
* ``action``: the name of an action that is applicable on a cluster.
* ``params``: a dictionary feeding argument values (if any) to the action.

In the long term, senlin may support user-defined actions where ``action``
will be interpreted as the UUID or name of a user-defined action.


Creating a Receiver
~~~~~~~~~~~~~~~~~~~

When a user requests the creation of a receiver by invoking :program:`senlin`
command line tool, the request comes with at least two parameters: the
targeted cluster and the intended action to invoke when the receiver is
triggered. Optionally, the user can provide some additional parameters to use
and/or the credentials of a different user. By default, a receiver of type
"``webhook``" is created. In future, we may support more receiver types.

When the Senlin API service receives the request, it does three things:

* Validates the request and rejects it if any of the following conditions is
  met:

  - the targeted cluster could not be found;
  - the receiver type specified is not supported;
  - the targeted cluster is not owned by the requester and the requester does
    not have an "``admin``" role in the project;
  - the provided action is not applicable on a cluster.

* Creates a receiver object that contains all necessary information that will
  be used to trigger the specified action on the specified cluster.

* Creates a "channel" which is specific to the receiver type. For example, a
  receiver of type "``webhook``" will contain a key named "``alarm_url``" in
  its channel which looks like::

    http://{host:port}/v1/webhooks/{webhook_id}/trigger?V=1

  **NOTE**: The ``V=1`` above is used to encode the current webhook triggering
  protocol. When the protocol changes in future, the value will be changed
  accordingly.

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


Credentials
~~~~~~~~~~~

When requesting the creation of a receiver, the requester can choose to
provide some credentials by specifying the ``actor`` property of the receiver.
This information will be used for invoking the webhook in the future. There
are several options to provide these credentials.

If the ``credentials`` to use is explicitly specified, Senlin will save it in
the receiver DB record. When the webhook is invoked later, the saved
credentials will be used for authentication with Keystone. Senlin engine
won't check if the provided credentials actually works when creating the
receiver. The check is postponed to the moment when the receiver is triggered.

If the ``credentials`` to use is not explicitly provided, Senlin will assume
that the receiver will be triggered in the future using the the requester's
credential. To make sure the future authentication succeeds, Senlin engine
will extract the ``user`` ID from the invoking context and create a trust
between the user and the ``senlin`` service account, just like the way how
Senlin deals with other operations.

The requester must be either the owner of the targeted cluster or he/she has
the ``admin`` role in the project. This is enforced by the policy middleware.
If the requester is the ``admin`` of the project, Senlin engine will use the
cluster owner's credentials (i.e. a trust with the Senlin user in this case).
