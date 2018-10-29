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
# -*- coding: utf-8 -*-

from docutils import nodes
from docutils.parsers import rst
from docutils.parsers.rst import directives
from functools import cmp_to_key
from oslo_utils import importutils
from sphinx.util import logging

from senlin.common import schema

LOG = logging.getLogger(__name__)


class SchemaDirective(rst.Directive):
    required_arguments = 0
    optional_arguments = 0
    final_argument_whitespace = True
    option_spec = {'package': directives.unchanged}
    has_content = False
    add_index = True
    section_title = 'Spec'
    properties_only = False

    def run(self):
        """Build doctree nodes consisting for the specified schema class

        :returns: doctree node list
        """

        # gives you access to the options of the directive
        options = self.options

        content = []

        # read in package class
        obj = importutils.import_class(options['package'])

        # skip other spec properties if properties_only is True
        if not self.properties_only:
            section = self._create_section(content, 'spec',
                                           title=self.section_title)

            # create version section
            version_section = self._create_section(section, 'version',
                                                   title='Latest Version')
            field = nodes.line('', obj.VERSION)
            version_section.append(field)

            # build versions table
            version_tbody = self._build_table(
                section, 'Available Versions',
                ['Version', 'Status', 'Supported Since'])
            sorted_versions = sorted(obj.VERSIONS.items())
            for version, support_status in sorted_versions:
                for support in support_status:
                    cells = [version]
                    sorted_support = sorted(support.items(), reverse=True)
                    cells += [x[1] for x in sorted_support]
                    self._create_table_row(cells, version_tbody)

            # create applicable profile types
            profile_type_description = ('This policy is designed to handle '
                                        'the following profile types:')
            profile_type_section = self._create_section(
                section, 'profile_types', title='Applicable Profile Types')
            field = nodes.line('', profile_type_description)
            profile_type_section.append(field)
            for profile_type in obj.PROFILE_TYPE:
                profile_type_section += self._create_list_item(profile_type)

            # create actions handled
            policy_trigger_description = ('This policy is triggered by the '
                                          'following actions during the '
                                          'respective phases:')
            target_tbody = self._build_table(
                section, 'Policy Triggers',
                ['Action', 'Phase'],
                policy_trigger_description
            )
            sorted_targets = sorted(obj.TARGET, key=lambda tup: tup[1])
            for phase, action in sorted_targets:
                cells = [action, phase]
                self._create_table_row(cells, target_tbody)

            # build properties
            properties_section = self._create_section(section, 'properties',
                                                      title='Properties')
        else:
            properties_section = content

        sorted_schema = sorted(obj.properties_schema.items(),
                               key=cmp_to_key(self._sort_by_type))
        for k, v in sorted_schema:
            self._build_properties(k, v, properties_section)

        # we return the result
        return content

    def _create_section(self, parent, sectionid, title=None, term=None):
        """Create a new section

        :returns: If term is specified, returns a definition node contained
        within the newly created section.  Otherwise return the newly created
        section node.
        """

        idb = nodes.make_id(sectionid)
        section = nodes.section(ids=[idb])
        parent.append(section)

        if term:
            if term != '**':
                section.append(nodes.term('', term))

            definition = nodes.definition()
            section.append(definition)

            return definition

        if title:
            section.append(nodes.title('', title))

        return section

    def _create_list_item(self, str):
        """Creates a new list item

        :returns: List item node
        """
        para = nodes.paragraph()
        para += nodes.strong('', str)

        item = nodes.list_item()
        item += para

        return item

    def _create_def_list(self, parent):
        """Creates a definition list

        :returns: Definition list node
        """

        definition_list = nodes.definition_list()
        parent.append(definition_list)

        return definition_list

    def _sort_by_type(self, x, y):
        """Sort two keys so that map and list types are ordered last."""

        x_key, x_value = x
        y_key, y_value = y

        # if both values are map or list, sort by their keys
        if ((isinstance(x_value, schema.Map) or
             isinstance(x_value, schema.List)) and
                (isinstance(y_value, schema.Map) or
                 isinstance(y_value, schema.List))):
            return (x_key > y_key) - (x_key < y_key)

        # show simple types before maps or list
        if (isinstance(x_value, schema.Map) or
                isinstance(x_value, schema.List)):
            return 1

        if (isinstance(y_value, schema.Map) or
                isinstance(y_value, schema.List)):
            return -1

        return (x_key > y_key) - (x_key < y_key)

    def _create_table_row(self, cells, parent):
        """Creates a table row for cell in cells

        :returns: Row node
        """

        row = nodes.row()
        parent.append(row)

        for c in cells:
            entry = nodes.entry()
            row += entry
            entry += nodes.literal(text=c)

        return row

    def _build_table(self, section, title, headers, description=None):
        """Creates a table with given title, headers and description

        :returns: Table body node
        """

        table_section = self._create_section(section, title, title=title)

        if description:
            field = nodes.line('', description)
            table_section.append(field)

        table = nodes.table()
        tgroup = nodes.tgroup(len(headers))
        table += tgroup

        table_section.append(table)

        for _ in headers:
            tgroup.append(nodes.colspec(colwidth=1))

        # create header
        thead = nodes.thead()
        tgroup += thead
        self._create_table_row(headers, thead)

        tbody = nodes.tbody()
        tgroup += tbody

        # create body consisting of targets
        tbody = nodes.tbody()
        tgroup += tbody

        return tbody

    def _build_properties(self, k, v, definition):
        """Build schema property documentation

        :returns: None
        """

        if isinstance(v, schema.Map):
            newdef = self._create_section(definition, k, term=k)

            if v.schema is None:
                # if it's a map for arbritary values, only include description
                field = nodes.line('', v.description)
                newdef.append(field)
                return

            newdeflist = self._create_def_list(newdef)

            sorted_schema = sorted(v.schema.items(),
                                   key=cmp_to_key(self._sort_by_type))
            for key, value in sorted_schema:
                self._build_properties(key, value, newdeflist)
        elif isinstance(v, schema.List):
            newdef = self._create_section(definition, k, term=k)

            # identify next section as list properties
            field = nodes.line()
            emph = nodes.emphasis('', 'List properties:')
            field.append(emph)
            newdef.append(field)

            newdeflist = self._create_def_list(newdef)

            self._build_properties('**', v.schema['*'], newdeflist)
        else:
            newdef = self._create_section(definition, k, term=k)
            if 'description' in v:
                field = nodes.line('', v['description'])
                newdef.append(field)
            else:
                field = nodes.line('', '++')
                newdef.append(field)


class SchemaProperties(SchemaDirective):
    properties_only = True


class SchemaSpec(SchemaDirective):
    section_title = 'Spec'
    properties_only = False


def setup(app):
    app.add_directive('schemaprops', SchemaProperties)
    app.add_directive('schemaspec', SchemaSpec)
