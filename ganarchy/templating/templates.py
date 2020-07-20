# This file is part of GAnarchy - decentralized project hub
# Copyright (C) 2020  Soni L.
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

import jinja2

import ganarchy.dirs

def get_template_loader():
    return jinja2.ChoiceLoader([
        jinja2.FileSystemLoader([ganarchy.dirs.CONFIG_HOME + "/templates"] + [config_dir + "/templates" for config_dir in ganarchy.dirs.CONFIG_DIRS]),
        jinja2.DictLoader({
            ## index.html
            'index.html': """<!DOCTYPE html>
<html lang="en">
    <head>
        <meta charset="utf-8" />
        <!--
        GAnarchy - project homepage generator
        Copyright (C) 2019  Soni L.

        This program is free software: you can redistribute it and/or modify
        it under the terms of the GNU General Public License as published by
        the Free Software Foundation, either version 3 of the License, or
        (at your option) any later version.

        This program is distributed in the hope that it will be useful,
        but WITHOUT ANY WARRANTY; without even the implied warranty of
        MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
        GNU General Public License for more details.

        You should have received a copy of the GNU General Public License
        along with this program.  If not, see <https://www.gnu.org/licenses/>.
        -->
        <title>{{ ganarchy.title|e }}</title>
        <meta name="description" content="{{ ganarchy.title|e }}" />
        <!--if your browser doesn't like the following, use a different browser.-->
        <script type="application/javascript" src="/index.js"></script>
    </head>
    <body>
        <h1>{{ ganarchy.title|e }}</h1>
        <p>This is {{ ganarchy.title|e }}. Currently tracking the following projects:</p>
        <ul>
        {% for project in ganarchy.projects -%}{% if project.exists -%}
            <li><a href="/project/{{ project.commit|e }}">{{ project.title|e }}</a>: {{ project.description|e }}</li>
        {% endif -%}{% endfor -%}
        </ul>
        <p>Powered by <a href="https://ganarchy.autistic.space/">GAnarchy</a>. AGPLv3-licensed. <a href="https://cybre.tech/SoniEx2/ganarchy">Source Code</a>.</p>
        <p>
            <a href="{{ ganarchy.base_url|e }}" onclick="event.preventDefault(); navigator.registerProtocolHandler('web+ganarchy', this.href + '?url=%s', 'GAnarchy');">Register web+ganarchy: URI handler</a>.
        </p>
    </body>
</html>
""",
            ## index.toml
            'index.toml': """# Generated by GAnarchy

{%- for project in database.list_projects() %}
[projects.{{project}}]
{%- for repo_url, branch, _head_commit in database.list_repobranches(project) %}
"{{repo_url|tomle}}".{% if branch == "HEAD" %}HEAD{% else %}"{{branch|tomle}}"{% endif %} = { active=true }
{%- endfor %}
{% endfor -%}
""",
            ## project.html FIXME
            'project.html': """<!DOCTYPE html>
<html lang="en">
    <head>
        <meta charset="utf-8" />
        <!--
        GAnarchy - project homepage generator
        Copyright (C) 2019  Soni L.

        This program is free software: you can redistribute it and/or modify
        it under the terms of the GNU General Public License as published by
        the Free Software Foundation, either version 3 of the License, or
        (at your option) any later version.

        This program is distributed in the hope that it will be useful,
        but WITHOUT ANY WARRANTY; without even the implied warranty of
        MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
        GNU General Public License for more details.

        You should have received a copy of the GNU General Public License
        along with this program.  If not, see <https://www.gnu.org/licenses/>.
        -->
        <title>{{ project_title|e }}</title>
        {% if project_desc %}<meta name="description" content="{{ project_desc|e }}" />{% endif %}
        <style type="text/css">.branchname { color: #808080; font-style: italic; }</style>
    </head>
    <body>
        <h1>{{ project_title|e }}</h1>
        <p>Tracking <span id="project_commit"><a href="web+ganarchy:{{ project_commit }}">{{ project_commit }}</a></span></p>
        <div id="project_body"><p>{{ project_body|e|replace("\n\n", "</p><p>") }}</p></div>
        <ul>
        {% for url, msg, img, branch in repos -%}
            <li><a href="{{ url|e }}">{{ url|e }}</a>{% if branch %} <span class="branchname">[{{ branch|e }}]</span>{% endif %}: {{ msg|e }}</li>
        {% endfor -%}
        </ul>
        <p>Powered by <a href="https://ganarchy.autistic.space/">GAnarchy</a>. AGPLv3-licensed. <a href="https://cybre.tech/SoniEx2/ganarchy">Source Code</a>.</p>
        <p>
            <a href="/">Main page</a>.
            <a href="{{ base_url|e }}" onclick="event.preventDefault(); navigator.registerProtocolHandler('web+ganarchy', this.href + '?url=%s', 'GAnarchy');">Register web+ganarchy: URI handler</a>.
        </p>
    </body>
</html>
""",
            ## history.svg FIXME
            'history.svg': """""",
        })
    ])