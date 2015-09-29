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

import croniter
import pytz
import six

from senlin.common import constraints
from senlin.common import exception as exc
from senlin.common.i18n import _
from senlin.common import schema
from senlin.drivers import base as driver_base
from senlin.triggers import base


GENERAL_PROPERTIES = (
    NAME, DESCRIPTION,
    TYPE, STATE, SEVERITY, ENABLED,
    OK_ACTIONS, ALARM_ACTIONS, INSUFFICIENT_DATA_ACTIONS,
) = (
    'name', 'description',
    'type', 'state', 'severity', 'enabled',
    'ok_actions', 'alarm_actions', 'insufficient_data_actions',
)

COMBINATION_OPERATORS = (
    C_AND, C_OR,
) = (
    'and', 'or',
)

OPERATOR_VALUES = (
    OP_LESS_THAN, OP_LESS_EQUAL, OP_EQUAL,
    OP_NOT_EQUAL, OP_GREATER_EQUAL, OP_GREATER_THAN,
) = (
    'lt', 'le', 'eq', 'ne', 'ge', 'gt',
)

STATISTIC_VALUES = (
    SV_MAX, SV_MIN, SV_AVG, SV_SUM, SV_COUNT,
) = (
    'max', 'min', 'avg', 'sum', 'count',
)

ALARM_PROPERTY_KEY = (
    REPEAT, TIME_CONSTRAINTS
) = (
    'repeat_actions', 'time_constraints'
)

TIME_CONSTRAINT_KEYS = (
    TC_NAME, TC_DESCRIPTION, TC_START, TC_DURATION, TC_TIMEZONE,
) = (
    'name', 'description', 'start', 'duration', 'timezone',
)

RULE_KEYS = (
    METRIC, METRICS, OPERATOR, THRESHOLD,
    PERIOD, EVALUATIONS, STATISTIC,
    QUERY, RESOURCE_TYPE, RESOURCE_ID,
    METER_NAME, COMBINATION_OP, ALARM_IDS,
    GRANULARITY, AGG_METHOD,
) = (
    'metric', 'metrics', 'comparison_operator', 'threshold',
    'period', 'evaluation_periods', 'statistic',
    'query', 'resource_type', 'resource_id',
    'meter_name', 'operator', 'alarm_ids',
    'granularity', 'aggregation_method',
)

QUERY_KEYS = (
    Q_FIELD, Q_OP, Q_TYPE, Q_VALUE
) = (
    'field', 'op', 'type', 'value'
)


class Alarm(base.Trigger):

    # time constraints
    alarm_schema = {
        REPEAT: schema.Boolean(
            _('Whether the actions should be re-triggered on each evaluation '
              'cycle. Default to False.'),
            default=False,
        ),
        TIME_CONSTRAINTS: schema.List(
            schema=schema.Map(
                _('A map of time constraint settings.'),
                schema={
                    NAME: schema.String(
                        _('Name of the time constraint.'),
                    ),
                    TC_DESCRIPTION: schema.String(
                        _('A description of the time constraint.'),
                    ),
                    TC_START: schema.String(
                        _('Start point of the time constraint, expressed as a '
                          'string in cron expression format.'),
                        required=True,
                    ),
                    TC_DURATION: schema.Integer(
                        _('How long the constraint should last, in seconds.'),
                        required=True,
                    ),
                    TC_TIMEZONE: schema.String(
                        _('Time zone of the constraint.'),
                        default='',
                    ),
                },
            ),
        )
    }

    def __init__(self, name, spec, **kwargs):
        super(Alarm, self).__init__(name, spec, **kwargs)

        self.alarm_properties = schema.Spec(self.alarm_schema, spec)
        self.namespace = 'default'
        self.rule = None

    def validate(self):
        # validate cron expression if specified
        if TIME_CONSTRAINTS in self.spec:
            tcs = self.alarm_properties[TIME_CONSTRAINTS]
            for tc in tcs:
                exp = tc.get(TC_START, '')
                try:
                    croniter.croniter(exp)
                except Exception as ex:
                    msg = _("Invalid cron expression specified for property "
                            "'%(property)s' (%(exp)s): %(ex)s"
                            ) % {'property': TC_START, 'exp': exp,
                                 'ex': six.text_type(ex)}
                    raise exc.InvalidSpec(message=msg)

                tz = tc.get(TC_TIMEZONE, '')
                try:
                    pytz.timezone(tz)
                except Exception as ex:
                    msg = _("Invalid timezone value specified for property "
                            "'%(property)s' (%(tz)s): %(ex)s"
                            ) % {'property': TC_TIMEZONE, 'tz': tz,
                                 'ex': six.text_type(ex)}
                    raise exc.InvalidSpec(message=msg)

    def create(self, ctx, **kwargs):
        """Create an alarm for a cluster.

        :param name: The name for the alarm.
        :param urls: A list of URLs for webhooks to be triggered.
        :returns: A dict containing properties of the alarm.
        """
        self.ok_actions = kwargs.get(OK_ACTIONS, [])
        self.alarm_actions = kwargs.get(ALARM_ACTIONS, [])
        self.insufficient_data_actions = kwargs.get(
            INSUFFICIENT_DATA_ACTIONS, [])

        rule_name = self.namespace + '_rule'
        rule_data = dict((k, v) for k, v in self.rule.items())
        params = {
            NAME: self.name,
            DESCRIPTION: self.desc,
            TYPE: self.namespace,
            STATE: self.state,
            SEVERITY: self.severity,
            ENABLED: self.enabled,
            OK_ACTIONS: self.ok_actions,
            ALARM_ACTIONS: self.alarm_actions,
            INSUFFICIENT_DATA_ACTIONS: self.insufficient_data_actions,
            TIME_CONSTRAINTS: self.alarm_properties[TIME_CONSTRAINTS],
            REPEAT: self.alarm_properties[REPEAT],
            rule_name: rule_data,
        }

        try:
            cc = driver_base.SenlinDriver().telemetry(ctx.to_dict())
            alarm = cc.alarm_create(**params)
            self.physical_id = alarm.id
            self.store(ctx)
            return True, alarm.to_dict()
        except exc.SenlinException as ex:
            return False, six.text_type(ex)

    def delete(self, ctx, identifier):
        """Delete an alarm.

        :param identifier: This must be an alarm ID.
        """
        try:
            cc = driver_base.SenlinDriver().telemetry(ctx)
            res = cc.alarm_delete(identifier, True)
            return True, res
        except exc.InternalError as ex:
            return False, six.text_type(ex)

    def update(self, identifier, values):
        return NotImplemented


class ThresholdAlarm(Alarm):

    rule_schema = {
        METER_NAME: schema.String(
            _('Name of a meter to evaluate against.'),
            required=True,
        ),
        OPERATOR: schema.String(
            _('Comparison operator for evaluation.'),
            constraints=[
                constraints.AllowedValues(OPERATOR_VALUES),
            ],
            default=OP_EQUAL,
        ),
        THRESHOLD: schema.Number(
            _('Threshold for evaluation.'),
            required=True
        ),
        PERIOD: schema.Integer(
            _('Length of every evaluation period in seconds.'),
            default=60,
        ),
        EVALUATIONS: schema.Integer(
            _('Number of periods to evaluate over.'),
            default=1,
        ),
        STATISTIC: schema.String(
            _('Statistics to evaluate. Must be one of %s, default to "avg".'
              ) % list(STATISTIC_VALUES),
            constraints=[
                constraints.AllowedValues(STATISTIC_VALUES),
            ],
            default=SV_AVG,
        ),
        QUERY: schema.List(
            _('The query to find the dat afor computing statistics.'),
            schema=schema.Map(
                schema={
                    Q_FIELD: schema.String(
                        _('A field of a meter to query.'),
                        required=True,
                    ),
                    Q_OP: schema.String(
                        _('An operator for meter comparison.'),
                        default='==',
                    ),
                    Q_VALUE: schema.String(
                        _('A value for comparison.'),
                        required=True,
                    )
                }
            ),
        )
    }

    def __init__(self, name, spec, **kwargs):
        super(ThresholdAlarm, self).__init__(name, spec, **kwargs)
        rule_spec = spec.get('rule', {})
        self.rule = schema.Spec(self.rule_schema, rule_spec)
        self.namespace = 'threshold'


class CombinationAlarm(Alarm):

    rule_schema = {
        COMBINATION_OP: schema.String(
            _('Operator for combination. Must be one of %s'
              ) % list(COMBINATION_OPERATORS),
            default=C_AND,
        ),
        ALARM_IDS: schema.List(
            _('List of alarm IDs for combination.'),
            schema=schema.String(
                _('The ID of an alarm.'),
                required=True,
            ),
            required=True,
        )
    }

    def __init__(self, name, spec, **kwargs):
        super(CombinationAlarm, self).__init__(name, spec, **kwargs)

        rule_spec = spec.get('rule', {})
        self.rule = schema.Spec(self.rule_schema, rule_spec)
        self.namespace = 'combination'


class ResourceAlarm(Alarm):

    rule_schema = {
        METRIC: schema.String(
            _('Name of a metric to evaluate against.'),
            required=True,
        ),
        OPERATOR: schema.String(
            _('Comparison operator for evaluation.'),
            constraints=[
                constraints.AllowedValues(OPERATOR_VALUES),
            ],
            default=OP_EQUAL,
        ),
        THRESHOLD: schema.Number(
            _('Threshold for evaluation.'),
            required=True
        ),
        GRANULARITY: schema.Integer(
            _('Length of each evaluation period in seconds.'),
            default=60,
        ),
        EVALUATIONS: schema.Integer(
            _('Number of periods to evaluate over.'),
            default=1,
        ),
        AGG_METHOD: schema.String(
            _('Statistics to evaluate. Must be one of %s, default to "avg".'
              ) % list(STATISTIC_VALUES),
            constraints=[
                constraints.AllowedValues(STATISTIC_VALUES),
            ],
            default=SV_AVG,
        ),
        RESOURCE_TYPE: schema.String(
            _('The resource type.'),
            required=True,
        ),
        RESOURCE_ID: schema.String(
            _('The ID of a resource.'),
            required=True,
        )
    }

    def __init__(self, name, spec, **kwargs):
        super(ResourceAlarm, self).__init__(name, spec, **kwargs)

        rule_spec = spec.get('rule', {})
        self.rule = schema.Spec(self.rule_schema, rule_spec)
        self.namespace = 'gnocchi_resources_threshold'


class AggregateByMetricsAlarm(Alarm):

    rule_schema = {
        METRICS: schema.String(
            _('Metrics to evaluate against.'),
            required=True,
        ),
        OPERATOR: schema.String(
            _('Comparison operator for evaluation.'),
            constraints=[
                constraints.AllowedValues(OPERATOR_VALUES),
            ],
            default=OP_EQUAL,
        ),
        THRESHOLD: schema.Number(
            _('Threshold for evaluation.'),
            required=True
        ),
        GRANULARITY: schema.Integer(
            _('Length of every evaluation period in seconds.'),
            default=60,
        ),
        EVALUATIONS: schema.Integer(
            _('Number of periods to evaluate over.'),
            default=1,
        ),
        AGG_METHOD: schema.String(
            _('Statistics to evaluate. Must be one of %s.'
              ) % list(STATISTIC_VALUES),
            constraints=[
                constraints.AllowedValues(STATISTIC_VALUES),
            ],
            default=SV_AVG,
        ),
    }

    def __init__(self, name, spec, **kwargs):
        super(AggregateByMetricsAlarm, self).__init__(name, spec, **kwargs)
        rule_spec = spec.get('rule', {})
        self.rule = schema.Spec(self.rule_schema, rule_spec)
        self.namespace = 'gnocchi_aggregation_by_metrics_threshold'


class AggregateByResourcesAlarm(Alarm):

    rule_schema = {
        METRIC: schema.String(
            _('Metric to evaluate against.'),
            required=True,
        ),
        OPERATOR: schema.String(
            _('Comparison operator for evaluation.'),
            constraints=[
                constraints.AllowedValues(OPERATOR_VALUES),
            ],
            default=OP_EQUAL,
        ),
        THRESHOLD: schema.Number(
            _('Threshold for evaluation.'),
            required=True
        ),
        GRANULARITY: schema.Integer(
            _('Length of every evaluation period in seconds.'),
            default=60,
        ),
        EVALUATIONS: schema.Integer(
            _('Number of periods to evaluate over.'),
            default=1,
        ),
        AGG_METHOD: schema.String(
            _('Statistics to evaluate. Must be one of %s.'
              ) % list(STATISTIC_VALUES),
            constraints=[
                constraints.AllowedValues(STATISTIC_VALUES),
            ],
            default=SV_AVG,
        ),
        RESOURCE_TYPE: schema.String(
            _('The resource type.'),
            required=True,
        ),
        QUERY: schema.String(
            _('Gnocchi resources search query filter.'),
            required=True,
        )
    }

    def __init__(self, name, spec, **kwargs):
        super(AggregateByResourcesAlarm, self).__init__(name, spec, **kwargs)
        rule_spec = spec.get('rule', {})
        self.rule = schema.Spec(self.rule_schema, rule_spec)
        self.namespace = 'gnocchi_aggregation_by_resources_threshold'
