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

import ganarchy.templating.templates
import ganarchy.templating.toml

def get_env():
    env = jinja2.Environment(
        loader=ganarchy.templating.templates.get_template_loader(),
        autoescape=False,
        # aka please_stop_mangling_my_templates=True
        keep_trailing_newline=True
    )
    env.filters['tomlescape'] = ganarchy.templating.toml.tomlescape
    env.filters['tomle'] = env.filters['tomlescape']
    return env
