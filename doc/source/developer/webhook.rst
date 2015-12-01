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

=======
Webhook
=======

Concept
~~~~~~~

A "Webhook" is a URI that can be accessed from any users or programs, provided
they possess some credentials that can be authenticated.

Webhooks are used to trigger a specific action on a senlin entity on behalf of
a user. A webhook is an URI that encodes a tuple (``user``, ``entity``,
``action``, ``params``), where:

* The ``user`` is the credential of a user on whose behalf the action will be
  triggered. This is usually the use who created the webhook, but it can be
  any other valid user explicitly specified when the webhook is created.
* The ``entity`` can be a cluster, a node or a policy object;
* The ``action`` is the name of a built-in action supported by the object;
* The ``params`` is a dictionary feeding argument values (if any) to the
  action.

In the long term, senlin may support user-defined actions where ``action``
will be interpreted as the UUID or name of a user-defined action.


Creating a Webhook
~~~~~~~~~~~~~~~~~~

When a user requests the creation of a webhook by invoking :program:`senlin`
command line tool, the request comes with at least two parameters: the
targeted entity and the intended action to invoke when the webhook is
triggered. Optionally, the user can provide some additional parameters to use
and/or the credentials of a different user.

When the Senlin API service receives the request, it does three things:

* Validate the request and rejects it if any of the following conditions is
  met:

  - the targeted entity could not be found;
  - the targeted entity is not owned by the requester and the requester does
    not have an "``admin``" role in the project;
  - the provided action is not supported by the type of the targeted entity;

* Create a webhook object that contains all necessary information that will
  be used to trigger the specified action on the specified entity;

  - Encrypt the user credentials to ensure it won't get leaked and then store
    the encrypted data into the database;
  - Generate a webhook URL with the following format and return it to user::

       http://{host:port}/v1/{tenant_id}/webhooks/{webhook_id}/trigger?key=$KEY

    **NOTE**: The ``$KEY`` above is used to decrypt the password. The user
    have to keep it safe.

Finally, Senlin engine returns a dictionary containing the properties of the
webhook object.


Triggering a Webhook
~~~~~~~~~~~~~~~~~~~~

When triggering a webhook, a user or a software sends a ``POST`` request to
the webhook URL. This request is first processed by the ``webhook`` middleware
before arriving at the Senlin API service.

The ``webhook`` middleware checks this request and the ``key`` value provided.
The middleware attempts to find the webhook record from Senlin database and see
if the named webhook does exist. If the webhook is found, it then tries to
decipher the the saved credentials using the provided ``key``. An error code
404 will be returned if the webhook is not found.

If the credentials are decrypted successfully, the middleware will proceed to
get a Keystone token using the decrypted credentials. Using this token, the
triggering request can pass the token checking by the keystone ``auth_token``
middleware. An exception will be thrown when the authentication operation fails.

When the senlin engine service finally receives the webhook triggering request
it creates an action based on the information stored in webhook object.
The newly created action is then dispatched and scheduled by a scheduler to
perform the expected operation.


Credentials
~~~~~~~~~~~

When requesting the creation of a webhook, the requester need to provide some
credentials for invoking the webhook in future. There are several options to
provide these credentials.

If the ``credentials`` to use is explicitly specified, Senlin will save it in
the webhook DB record in an encrypted format. A ``key`` is returned and
appended to the webhook URL. When the webhook is invoked in the future, the
saved credentials will be used for authentication with Keystone. Senlin engine
won't check if the provided credentials actually works when creating the
webhook. The check is postponed to the moment when the webhook is triggered.

If the ``credentials`` to use is not explicitly provided, Senlin will assume
that the webhook will be triggered in future using the the requester's
credential. To make sure the future authentication succeeds, Senlin engine
will extract the ``user`` ID from the invoking context and create a trust
between the user and the the ``senlin`` service account, just like the way how
Senlin deals with other operations.

The requester must be either the owner of the targeted object or he/she has
the ``admin`` role in the project. This is enforced by the policy middleware.
If the requester is the ``admin`` of the project, Senlin engine will use the
object owner's credentials (i.e. a trust with the Senlin user in this case).


DB Model
~~~~~~~~

A webhook DB object has the following properties:

* ``id``: the UUID of the webhook object;
* ``name``: the name of the webhook (optional);
* ``user``: the ID of the user who created the webhook;
* ``project``: the project ID of the user who created the webhook;
* ``domain``: the domain of the user who created the webhook;
* ``created_time``: timestamp of webhook creation;
* ``deleted_time``: timestamp of webhook deletion;
* ``obj_id``: the ``id`` of a senlin entity (e.g. cluster) to which the
   webhook is associated;
* ``obj_type``: the type of senlin entity to which the webhook is associated;
* ``action``: the name of the action (e.g. ``CLUSTER_RESIZE``) which will be
   created when the webhook is triggered;
* ``credential``: the credential that will be used to invoke the targeted
   action.
* ``params``: the extra parameters that will be passed to the target action
   when the webhook is triggered. This can be overriden when a webhook
   triggering request comes in.
