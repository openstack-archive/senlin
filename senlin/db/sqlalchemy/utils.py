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

from oslo_config import cfg
from oslo_utils import timeutils


def exact_filter(query, model, filters):
    """Applies exact match filtering to a query.

    Returns the updated query.  Modifies filters argument to remove
    filters consumed.

    :param query: query to apply filters to
    :param model: model object the query applies to, for IN-style
                  filtering
    :param filters: dictionary of filters; values that are lists,
                    tuples, sets, or frozensets cause an 'IN' test to
                    be performed, while exact matching ('==' operator)
                    is used for other values
    """

    filter_dict = {}
    if filters is None:
        filters = {}

    for key, value in filters.items():
        if isinstance(value, (list, tuple, set, frozenset)):
            column_attr = getattr(model, key)
            query = query.filter(column_attr.in_(value))
        else:
            filter_dict[key] = value

    if filter_dict:
        query = query.filter_by(**filter_dict)

    return query


def get_sort_params(value, default_key=None):
    """Parse a string into a list of sort_keys and a list of sort_dirs.

    :param value: A string that contains the sorting parameters.
    :param default_key: An optional key set as the default sorting key when
                        no sorting option value is specified.

    :return: A list of sorting keys and a list of sorting dirs.
    """
    keys = []
    dirs = []
    if value:
        for s in value.split(','):
            s_key, _s, s_dir = s.partition(':')
            keys.append(s_key)
            s_dir = s_dir or 'asc'
            nulls_appendix = 'nullsfirst' if s_dir == 'asc' else 'nullslast'
            sort_dir = '-'.join([s_dir, nulls_appendix])
            dirs.append(sort_dir)
    elif default_key:
        # use default if specified
        return [default_key, 'id'], ['asc-nullsfirst', 'asc']

    if 'id' not in keys:
        keys.append('id')
        dirs.append('asc')

    return keys, dirs


def is_service_dead(service):
    """Check if a given service is dead."""
    cfg.CONF.import_opt("periodic_interval", "senlin.common.config")
    max_elapse = 2 * cfg.CONF.periodic_interval

    return timeutils.is_older_than(service.updated_at, max_elapse)
