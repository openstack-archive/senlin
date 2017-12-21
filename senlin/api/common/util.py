#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

import functools

import jsonschema
from oslo_utils import strutils
import six
from webob import exc

from senlin.common.i18n import _
from senlin.common import policy
from senlin.objects import base as obj_base


def policy_enforce(handler):
    """Decorator that enforces policies.

    Check the path matches the request context and enforce policy defined in
    policy file and policies in code.

    This is a handler method decorator.
    """
    @functools.wraps(handler)
    def policy_checker(controller, req, **kwargs):
        # Enable project_id based target check
        rule = "%s:%s" % (controller.REQUEST_SCOPE,
                          handler.__name__)
        allowed = policy.enforce(context=req.context, rule=rule, target={})
        if not allowed:
            raise exc.HTTPForbidden()
        return handler(controller, req, **kwargs)

    return policy_checker


def parse_request(name, req, body, key=None):
    """Formalize an API request and validate it.

    :param name: The name for a versioned request object.
    :param req: Reference to a WSGI request object.
    :param body: The JSON body (if any) that accompanies a request. Could be
                 augmented by controller before getting passed here.
    :param key: An optional key indicating the inner object for a request.
    :returns: A validated, versioned request object
    """
    try:
        req_cls = obj_base.SenlinObject.obj_class_from_name(name)
    except Exception as ex:
        raise exc.HTTPBadRequest(six.text_type(ex))

    try:
        primitive = req_cls.normalize_req(name, body, key)
    except ValueError as ex:
        raise exc.HTTPBadRequest(six.text_type(ex))

    version = req_cls.find_version(req.context)
    obj = None
    try:
        obj = req_cls.obj_from_primitive(primitive)
        jsonschema.validate(primitive, obj.to_json_schema())
    except ValueError as ex:
        raise exc.HTTPBadRequest(six.text_type(ex))
    except jsonschema.exceptions.ValidationError as ex:
        raise exc.HTTPBadRequest(six.text_type(ex.message))

    # Do version coversion if necessary
    if obj is not None and version != req_cls.VERSION:
        obj.obj_make_compatible(primitive, version)
        return req_cls.obj_from_primitive(primitive)

    return obj


def get_allowed_params(params, whitelist):
    """Extract from ``params`` all entries listed in ``whitelist``.

    The returning dict will contain an entry for a key if, and only if,
    there's an entry in ``whitelist`` for that key and at least one entry in
    ``params``. If ``params`` contains multiple entries for the same key, it
    will yield an array of values: ``{key: [v1, v2,...]}``

    :param params: a NestedMultiDict from webob.Request.params
    :param whitelist: an array of strings to whitelist

    :returns: a dict with {key: value} pairs
    """
    allowed_params = {}

    for key, get_type in whitelist.items():
        value = None
        if get_type == 'single':
            value = params.get(key)
        elif get_type in ('mixed', 'multi'):
            value = params.getall(key)

        if value:
            allowed_params[key] = value

    return allowed_params


def parse_bool_param(name, value):
    if str(value).lower() not in ('true', 'false'):
        msg = _("Invalid value '%(value)s' specified for '%(name)s'"
                ) % {'name': name, 'value': value}
        raise exc.HTTPBadRequest(msg)

    return strutils.bool_from_string(value, strict=True)
