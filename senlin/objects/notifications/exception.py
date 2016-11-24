# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

import inspect

import six

from senlin.objects import base as senlin_base
from senlin.objects import fields
from senlin.objects.notifications import base


@senlin_base.SenlinObjectRegistry.register_notification
class ExceptionPayload(base.NotificationObject):

    VERSION = '1.0'

    fields = {
        'module': fields.StringField(),
        'function': fields.StringField(),
        'exception': fields.StringField(),
        'message': fields.StringField(),
    }

    @classmethod
    def from_exception(cls, exc):
        if exc is None:
            return None
        trace = inspect.trace()[-1]
        module = inspect.getmodule(trace[0])
        module_name = module.__name__ if module else 'unknown'
        return cls(function=trace[3], module=module_name,
                   exception=exc.__class__.__name__,
                   message=six.text_type(exc))
