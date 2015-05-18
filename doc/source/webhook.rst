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

Webhook
=======
Webhook is used to trigger a specific action of  a senlin entity, typically
scaling out/in action of a cluster.

Design
------

Workflow
++++++++
1. User creates a webhook through webhook API. User needs to specify what action
   and which senlin entity this webhook is bound to. Also for some specific
   actions, user can define the parameters they want to use when invoking the
   cluster action API, e.g. the adjustment of scaling operation; User also
   `HAVE TO` specify the credential(usually a user_id and its password)
   explicitly/implicitly. This credential will be used by Senlin service later
   to execute the real action, e.g. cluster scaling, when webhook is triggered
   later.

2. Senlin service receives the request and does three things:

   - Creating a webhook object that contains all necessary information used
     to trigger specific action of a senlin entity;
   - Encrypting the credential information to ensure it won't be hacked and
     then storing the encrypted password into DB;
   - Generating a webhook url with the following format and return it to user:
       http://{server_ip:port}/v1/{tenant_id}/webhooks/{webhook_id}/trigger?key=$KEY
     NOTE: `$KEY` is the key to decrypted the password so user has to keep
     it safely. Also the webhook_url can only be got at the first time the
     webhook is created, so user also need to record it carefully.

3. User triggers the webhook by sending a post request to its url. No any extra
   credential is needed here, e.g.
       curl -i -X 'POST' $WEBHOOK_URL
   Also user can choose to take some extra parameters for the action execution
   when triggering the webhook, e.g.
       curl -i -X 'POST' $WEBHOOK_URL -H 'Content-type: application/json' --data
       '{"params": {"count": 2}}'

4. Webhook middleware of Senlin service handles this post request and decrypt
   the credential. Then it tries to validate the credential by querying a
   token based on it from keystone. If succeed, the token will be added to this
   post request and then send to next middleware in pipeline, usually keystone
   auth_token. If not, an exception will be raised and this webhook triggering
   fail.

5. Senlin engine receives the webhook triggering request and generates action
   based on the information stored in webhook object, e.g. obj_type, obj_id
   and action name;

6. Action is dispatched and scheduled by Senlin scheduler to finish the expected
   operation, e.g. cluster scaling in/out.


Implementation
--------------

DB model
++++++++
A webhook DB object includes the following properties:

 - id: the uuid of webhook
 - name: the name of webhook (optional)
 - user: the id of user who created the webhook
 - project: the project id of user who created the webhook.
 - domain: the domain of the user who created the webhook
 - created_time: time of webhook was created
 - deleted_time: time of webhook was deleted
 - obj_id: the id of senlin entity(e.g. cluster) that the webhook bound to
 - obj_type: the type of senlin entity that the webhook bound to
 - action: action(e.g. scalingin, scalingout) of the target the webhook
   bound to
 - credential: credential that will be used to invoke target action API, e.g.
   clusters/$cluster_id/action when webhook is triggered
 - params: parameters that will be included when invoke the target action API,
   e.g. adjustment of scaling operation
