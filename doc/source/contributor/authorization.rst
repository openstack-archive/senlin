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

====================
Senlin Authorization
====================

As a service to be consumed by end users and possibly other IT persons, Senlin
has some basic components and strategies to manage access control. The design
is meant to be as open as possible though the current focus as this document is
drafted is on enabling Keystone-based (aka. token-based) OpenStack
authorization.

This document presents an overview of the authentication and authorization
mechanisms provided by the Senlin API and its service engine. The top-most
design consideration of these mechanisms is to make it accommodating so that
the interactions with different authentication engines can be done using the
same framework. The reason behind this decision is to make Senlin cloud-backend
agnostic so it can be used to support clustering of resources in a multi-cloud,
or multi-region, or multi-availability-zone setups.


Major Components
~~~~~~~~~~~~~~~~

In the context of an OpenStack cloud, the most important components involved in
the authentication and the authorization process are:

- The Senlin client (i.e. the `python-senlinclient` package) which accepts
  user credentials provided through environment variables and/or the command
  line arguments and forwards them to the OpenStack SDK (i.e. the
  `openstacksdk` package) when making service requests to Senlin API.
- The OpenStack SDK (`openstacksdk`) is used by Senlin engine to
  interact with any other OpenStack services. The Senlin client also uses the
  SDK to talk to the Senlin API. The SDK package translates the user-provided
  credentials into a token by invoking the Keystone service.
- The Keystone middleware (i.e. `keystonemiddleware`) which backs the
  `auth_token` WSGI middleware in the Senlin API pipeline provides a basic
  validation filter. The filter is responsible to validate the token that
  exists in the HTTP request header and then populates the HTTP request header
  with detailed information for the downstream filters (including the API
  itself) to use.
- The `context` WSGI middleware which is based on the `oslo.context` package
  provides a constructor of the `RequestContext` data structure that
  accompanies any requests down the WSGI application pipeline so that those
  downstream components don't have to access the HTTP request header.


Usage Scenarios
~~~~~~~~~~~~~~~

There are several ways to raise a service request to the Senlin API, each of
which has its own characteristics that will affect the way authentication
and/or authorization is performed.

1) Users interact with Senlin service API using the OpenStack client (i.e. the
   plugin provided by the `python-senlinclient` package). The requests, after
   being preprocessed by the OpenStack SDK will contain a valid Keystone token
   that can be validated by the `auth_token` WSGI middleware.
2) Users interact with Senlin service API directly by making HTTP requests
   where the requester's credentials have been validated by Keystone so the
   requests will carry a valid Keystone token for verification by the
   `auth_token` middleware as well.
3) Users interact with Senlin service API directly by making HTTP requests, but
   the requests are "naked" ones which mean that the requests do not contain
   credentials as expected by Senlin API (or other OpenStack services). In
   stead, the URI requested contains some special parameters for authentication
   and/or authorization's purposes.

Scenario 1) and 2) are the most common ways for users to use Senlin API. They
share the same request format when the request arrives at the Senlin API
endpoint. Scenario 3) is a little bit different. What Senlin wants to achieve
is making no assumption where the service requests come from. That means it
cannot assume that the requester (could be any program) will fill in the
required headers in their service requests. One example of such use cases is
the Webhook API Senlin provides that enables a user to trigger an action on an
object managed by Senlin. Senlin provides a special support to these use cases.


Operation Delegation (Trusts)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Since Senlin models most operations as "Actions" that can be executed by
worker threads asynchronously, these operations have to be done on behalf of
the requester so that they can be properly traced, authenticated, audited or
logged.


Credentials and Context
-----------------------

A generic solution to the delegation problem is to ask users to provide their
credentials to Senlin so Senlin can impersonate them when interacting with
other services. In fact, this may be the only solution that can be applied on
different cloud backends.

Senlin supports a `context` property for all "profile" types by default unless
overridden by a profile type implementation. This context can be treated as a
container for these credentials. Storing user credential in Senlin database
does imply a security risk. In future, we hope Senlin can make use of the
Barbican service for this purpose.

Senlin's implementation of context is based on the `oslo_context` package.
There is still room for improvement thanks to the new enhancements to that
package.


Trusts: Dealing with Token Expiration
-------------------------------------

In some cases, the solution above may be impractical because after the
client-side processing and/or the front-end middleware filtering, Senlin
cannot get the original user credentials (e.g. user name and password).
Senlin can only get a "token", which expires in an hour by default. This means
that after no more than one hour, Senlin won't be able to use this token for
authentication/authorization.

The OpenStack identity service (a.k.a Keystone) has considered this situation
and provided a solution. When a requester wants to delegate his/her roles in a
project to a 3rd party, he or she can create a "Trust" relationship between
him/her (the trustor) and that 3rd party (the trustee). The "Trust" has a
unique ID that can be used by the trustee when authenticating with Keystone.
Once trust ID is authenticated, the trustee can perform operations on behalf
of the trustor.

The trust extension in Keystone V3 can be used to solve the token expiration
problem. There are two ways to do this as shown below.

1) Requester Created Trusts: Before creating a profile, a requester can create
   a trust with the trustee set to the `senlin` user. He or she can customize
   the roles that can be assumed by `senlin`, which can be a subset of the
   roles the requester currently has in that project. When the requester later
   on creates a profile, he or she can provide the `trust_id` as a key of the
   `context` property. Senlin can later on use this trust for authentication
   and authorization's purpose.
2) Senlin Created Trusts: The solution above adds some burdens for an end user.
   In order to make Senlin service easy of use, Senlin will do the trust
   creation in the background. Whenever a new request comes in, Senlin will
   check if there is an existing trust relationship between the requester and
   the `senlin` user. Senlin will "hijack" the user's token and create a trust
   with `senlin` as the trustee. This trust relationship is currently stored
   in Senlin database, and the management of this sensitive information can be
   delegated to Barbican as well in future.


Precedence Consideration
------------------------

Since there now exist more than one place for Senlin to get the credentials
for use, Senlin needs to impose a precedence among the credential sources.

When Senlin tries to contact a cloud service via a driver, the requests are
issued from a subclass of `Profile`. Senlin will check the `user` property of
the targeted cluster or node and retrieve the trust record from database using
the `user` as the key. By default, Senlin will try obtain a new token from
Keystone using the `senlin` user's credentials (configured in `senlin.conf`
file) and the `trust_id`. Before doing that, Senlin will check if the profile
used has a "customized" `context`. If there are credentials such as `password`
or `trust_id` in the context, Senlin deletes its current `trust_id` from the
context, and adds the credentials found in the profile into the context.

In this way, a user can specify the credentials Senlin should use when talking
to other cloud services by customizing the `context` property of a profile.
The specified credentials may and may not belong to the requester.


Trust Middleware
----------------

When a service request arrives at Senlin API, Senlin API checks if there is a
trust relationship built between the requester user and the `senlin` user. A
new trust is created if no such record is found.

Once a trust is found or created, the `trust_id` is saved into the current
`context` data structure. Down the invocation path, or during asynchronous
action executions, the `trust_id` will be used for token generation when
needed.

Senlin provides an internal database table to store the trust information. It
may be removed in future when there are better ways to handle this sensitive
information.
