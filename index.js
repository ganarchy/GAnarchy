// GAnarchy - project homepage generator
// Copyright (C) 2019  Soni L.
//
// This program is free software: you can redistribute it and/or modify
// it under the terms of the GNU General Public License as published by
// the Free Software Foundation, either version 3 of the License, or
// (at your option) any later version.
//
// This program is distributed in the hope that it will be useful,
// but WITHOUT ANY WARRANTY; without even the implied warranty of
// MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
// GNU General Public License for more details.
//
// You should have received a copy of the GNU General Public License
// along with this program.  If not, see <https://www.gnu.org/licenses/>.

(function() {
	var url = new URL(document.location.href);
	var target = url.searchParams.get("url");
	if (target !== null) {
		// accepts both web+ganarchy:fae and
		// web+ganarchy://example.org/fae
		var project = target.match(/^web\+ganarchy\:(?:\/\/[^\\/?#]+[\\/])([a-fA-F0-9]+)$/);
		if (project !== null) {
			// some browsers don't like it when you set this directly
			url.search = "";
			url.pathname = "/project/" + project[1];
			document.location = url.href;
		}
	}
})();
