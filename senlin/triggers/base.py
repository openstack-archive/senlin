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


from oslo_utils import timeutils

from senlin.common import exception
from senlin.common.i18n import _
from senlin.common import schema
from senlin.db import api as db_api
from senlin.engine import environment

STATES = (
    OK, ALARM, INSUFFICIENT_DATA,
) = (
    'ok', 'alarm', 'insufficient_data',
)

SEVERITIES = (
    S_LOW, S_MODERATE, S_CRITICAL,
) = (
    'low', 'moderate', 'critical',
)


class Trigger(object):

    KEYS = (
        TYPE, VERSION, RULE,
    ) = (
        'type', 'version', 'rule',
    )

    spec_schema = {
        TYPE: schema.String(
            _('Type name of the trigger type.'),
            required=True,
        ),
        VERSION: schema.String(
            _('Version number string of the trigger type.'),
            required=True,
        ),
        RULE: schema.Map(
            _('Rule collection for the trigger.'),
            required=True,
        )
    }

    def __new__(cls, name, spec, **kwargs):
        """Create a trigger instance based on its type and version.

        :param name: The name for the trigger.
        :param spec: A dictionary containing the spec for the trigger.
        :param kwargs: Keyword arguments for trigger creation.
        :returns: An instance of a specific sub-class of BaseTrigger.
        """
        type_name, version = schema.get_spec_version(spec)

        if cls != Trigger:
            TriggerClass = cls
        else:
            TriggerClass = environment.global_env().get_trigger(type_name)

        return super(Trigger, cls).__new__(TriggerClass)

    def __init__(self, name, spec, **kwargs):
        """Initialize a trigger instance.

        :param name: The name for the trigger.
        :param spec: A dictionary containing the detailed trigger spec.
        :param kwargs: Keyword arguments for initializing the trigger.
        :returns: An instance of a specific sub-class of BaseTrigger.
        """
        type_name, version = schema.get_spec_version(spec)

        self.type_name = type_name
        self.name = name
        self.id = kwargs.get('id', None)
        self.physical_id = kwargs.get('physical_id', None)
        self.desc = kwargs.get('desc', '')
        self.state = kwargs.get('state', INSUFFICIENT_DATA)
        self.enabled = kwargs.get('enabled', True)
        self.severity = kwargs.get('severity', S_LOW)
        self.links = kwargs.get('links', {})

        self.user = kwargs.get('user')
        self.project = kwargs.get('project')
        self.domain = kwargs.get('domain')
        self.created_time = kwargs.get('created_time', None)
        self.updated_time = kwargs.get('updated_time', None)
        self.deleted_time = kwargs.get('deleted_time', None)

        self.spec = spec
        self.spec_data = schema.Spec(self.spec_schema, spec)

    @classmethod
    def _from_db_record(cls, record):
        """Construct a trigger object from a database record."""

        kwargs = {
            'id': record.id,
            'physical_id': record.physical_id,
            'desc': record.desc,
            'state': record.state,
            'enabled': record.enabled,
            'severity': record.severity,
            'links': record.links,
            'user': record.user,
            'project': record.project,
            'domain': record.domain,
            'created_time': record.created_time,
            'updated_time': record.updated_time,
            'deleted_time': record.deleted_time,
        }

        return cls(record.name, record.spec, **kwargs)

    @classmethod
    def load(cls, ctx, trigger_id=None, db_trigger=None):
        """Retrieve and reconstruct a trigger object from DB.

        :param ctx: A request context for DB operations.
        :param trigger_id: The ID of a trigger for retrieval.
        :param db_trigger: A DB record for a trigger.
        """
        if db_trigger is None:
            db_trigger = db_api.trigger_get(ctx, trigger_id)
            if db_trigger is None:
                raise exception.TriggerNotFound(trigger=trigger_id)

        return cls._from_db_record(db_trigger)

    @classmethod
    def load_all(cls, ctx, limit=None, marker=None, sort_keys=None,
                 sort_dir=None, filters=None, project_safe=True,
                 show_deleted=False):
        """Retrieve all trigger objects from database.

        Optionally, you can use some parameters to fine tune the query.
        :param ctx: A request context for DB operations.
        :param limit: Maximum number of records to return.
        :param marker: The ID of a last-seen record. Only records after this
                       ID value will be returned.
        :param sort_keys: A list of trigger properties for sorting.
        :param sort_dir: A string indicating the sorting direction. It can be
                         either `desc` for descending sorting or `asc` for
                         ascending sorting.
        :param filters: A map consisting key-value pairs to filter the
                        results.
        :param show_deleted: A boolean indicating whether soft-deleted objects
                             should be included in the results.
        """
        records = db_api.trigger_get_all(ctx, limit=limit, marker=marker,
                                         sort_keys=sort_keys,
                                         sort_dir=sort_dir, filters=filters,
                                         project_safe=project_safe,
                                         show_deleted=show_deleted)

        for record in records:
            yield cls._from_db_record(record)

    @classmethod
    def delete(cls, ctx, trigger_id):
        """Deletes the specified trigger.

        :param ctx: The request context for DB operations.
        :param trigger_id: The unique ID of a trigger.
        """
        return db_api.trigger_delete(ctx, trigger_id)

    def store(self, ctx):
        """Store the trigger object into the database table.

        :param context: The request context for DB operations.
        """
        timestamp = timeutils.utcnow()

        values = {
            'name': self.name,
            'type': self.type_name,
            'desc': self.desc,
            'state': self.state,
            'enabled': self.enabled,
            'severity': self.severity,
            'links': self.links,
            'spec': self.spec,
        }

        if self.id is not None:
            self.updated_time = timestamp
            values['updated_time'] = timestamp
            db_api.trigger_update(ctx, self.id, values)
        else:
            self.created_time = timestamp
            values['created_time'] = timestamp
            values['user'] = ctx.user
            values['project'] = ctx.project
            values['domain'] = ctx.domain
            db_trigger = db_api.trigger_create(ctx, values)
            self.id = db_trigger.id

        return self.id

    def validate(self):
        """Validate the schema and the data provided."""
        self.spec_data.validate()
        # NOTE: the rule property is supposed to be assigned in subclasses.
        self.rule.validate()

    @classmethod
    def get_schema(cls):
        return dict((name, dict(schema))
                    for name, schema in cls.spec_schema.items())

    def to_dict(self):
        def _fmt_time(value):
            return value and value.isoformat()

        trigger_dict = {
            'id': self.id,
            'name': self.name,
            'type': self.type_name,
            'desc': self.desc,
            'state': self.state,
            'enabled': self.enabled,
            'severity': self.severity,
            'links': self.links,
            'spec': self.spec,
            'user': self.user,
            'project': self.project,
            'domain': self.domain,
            'created_time': _fmt_time(self.created_time),
            'updated_time': _fmt_time(self.updated_time),
            'deleted_time': _fmt_time(self.deleted_time),
        }
        return trigger_dict
