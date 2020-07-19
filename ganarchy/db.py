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

"""This module handles GAnarchy's database.

Attributes:
    MIGRATIONS: Migrations.
"""

import sqlite3

import ganarchy.dirs
import ganarchy.data

# FIXME this should not be used directly because it's a pain.
MIGRATIONS = {
        "toml-config": (
                (
                    '''UPDATE "repo_history"
                    SET "project" = (SELECT "git_commit" FROM "config")
                    WHERE "project" IS NULL''',

                    '''ALTER TABLE "repos"
                    RENAME TO "repos_old"''',
                ),
                (
                    '''UPDATE "repo_history"
                    SET "project" = NULL
                    WHERE "project" = (SELECT "git_commit" FROM "config")''',

                    '''ALTER TABLE "repos_old"
                    RENAME TO "repos"''',
                ),
                "switches to toml config format. the old 'repos' " #cont
                "table is preserved as 'repos_old'"
            ),
        "better-project-management": (
                (
                    '''ALTER TABLE "repos"
                    ADD COLUMN "branch" TEXT''',

                    '''ALTER TABLE "repos"
                    ADD COLUMN "project" TEXT''',

                    '''CREATE UNIQUE INDEX "repos_url_branch_project"
                    ON "repos" ("url", "branch", "project")''',

                    '''CREATE INDEX "repos_project"
                    ON "repos" ("project")''',

                    '''ALTER TABLE "repo_history"
                    ADD COLUMN "branch" TEXT''',

                    '''ALTER TABLE "repo_history"
                    ADD COLUMN "project" TEXT''',

                    '''CREATE INDEX "repo_history_url_branch_project"
                    ON "repo_history" ("url", "branch", "project")''',
                ),
                (
                    '''DELETE FROM "repos"
                    WHERE "branch" IS NOT NULL OR "project" IS NOT NULL''',
                    '''DELETE FROM "repo_history"
                    WHERE "branch" IS NOT NULL OR "project" IS NOT NULL''',
                ),
                "supports multiple projects, and allows choosing " #cont
                "non-default branches"
            ),
        "test": (
                (
                    '''-- apply''',
                ),
                (
                    '''-- revert''',
                ),
                "does nothing"
            )
        }

class Database:
    """A database connection/session, returned by ``connect_database``.

    Some methods may require repos to be loaded.
    """

    def __init__(self, conn):
        self.conn = conn

    def initialize(self):
        """Initializes the database tables as expected by GAnarchy.
        """
        c = self.conn.cursor()
        c.execute('''
            CREATE TABLE "repo_history" (
                "entry" INTEGER PRIMARY KEY ASC AUTOINCREMENT,
                "url" TEXT,
                "count" INTEGER,
                "head_commit" TEXT,
                "branch" TEXT,
                "project" TEXT
            )
        ''')
        c.execute('''
            CREATE INDEX "repo_history_url_branch_project"
            ON "repo_history" ("url", "branch", "project")
        ''')
        self.conn.commit()
        c.close()

    def apply_migration(self, migration):
        """Applies a migration, by name.

        WARNING: Destructive operation.

        Args:
            migration (str): The name of the migration.
        """
        c = self.conn.cursor()
        for migration in MIGRATIONS[migration][0]:
            c.execute(migration)
        self.conn.commit()
        c.close()

    def revert_migration(self, migration):
        """Reverts a previously-applied migration, by name.

        WARNING: Destructive operation.

        Args:
            migration (str): The name of the migration.
        """
        c = self.conn.cursor()
        for migration in MIGRATIONS[migration][1]:
            c.execute(migration)
        self.conn.commit()
        c.close()

    def load_repos(self, effective_repo_list):
        """Loads repos from repo list.

        Must be done once for each instance of Database.

        Args:
            effective_repo_list (ganarchy.data.DataSource): The data
            source for the repo list.
        """
        c = self.conn.cursor()
        c.execute('''
            CREATE TEMPORARY TABLE "repos" (
                "url" TEXT PRIMARY KEY,
                "active" INT,
                "branch" TEXT,
                "project" TEXT
            )
        ''')
        c.execute('''
            CREATE UNIQUE INDEX "temp"."repos_url_branch_project"
            ON "repos" ("url", "branch", "project")
        ''')
        c.execute('''
            CREATE INDEX "temp"."repos_project"
            ON "repos" ("project")
        ''')
        c.execute('''
            CREATE INDEX "temp"."repos_active"
            ON "repos" ("active")
        ''')
        for repo in effective_repo_list.get_property_values(
            ganarchy.data.DataProperty.VCS_REPOS
        ):
            if repo.active:
                c.execute(
                    '''INSERT INTO "repos" VALUES (?, ?, ?, ?)''',
                    (repo.uri, 1, repo.branch, repo.project_commit)
                )
        self.conn.commit()
        c.close()

    def insert_activity(self, project_commit, uri, branch, head, count):
        """Inserts activity of a repo-branch.

        Args:
            project_commit: The project commit.
            uri: The repo uri.
            branch: The branch.
            head: The latest known head commit.
            count: The number of new commits.
        """
        self.insert_activities([(project_commit, uri, branch, head, count)])

    def insert_activities(self, activities):
        """Inserts activities of repo-branches.

        Args:
            activities: List of tuple. The tuple must match up with the
            argument order specified by ``insert_activity``.
        """
        c = self.conn.cursor()
        c.executemany(
            '''
                INSERT INTO "repo_history" (
                    "project",
                    "url",
                    "branch",
                    "head_commit",
                    "count"
                )
                VALUES (?, ?, ?, ?, ?)
            ''',
            activities
        )
        conn.commit()
        c.close()

    def list_projects(self):
        """Lists loaded projects.

        Repos must be loaded first.

        Yields:
            str: Project commit of each project.
        """
        c = self.conn.cursor()
        try:
            for (project,) in c.execute(
                '''SELECT DISTINCT "project" FROM "repos" '''
            ):
                yield project
        finally:
            c.close()

    def list_repobranches(self, project_commit):
        """Lists repo-branches of a project.

        Repos must be loaded first.

        Results are sorted by recent activity.

        Args:
            project_commit: The project commit.

        Yields:
            A 3-tuple holding the URI, branch name, and last known head
            commit.
        """
        c = self.conn.cursor()
        try:
            for (e, url, branch, head_commit) in c.execute(
                '''
                    SELECT "max"("e"), "url", "branch", "head_commit"
                    FROM (
                        SELECT
                            "max"("T1"."entry") "e",
                            "T1"."url",
                            "T1"."branch",
                            "T1"."head_commit"
                        FROM "repo_history" "T1"
                        WHERE (
                            SELECT "active"
                            FROM "repos" "T2"
                            WHERE
                                "url" = "T1"."url"
                                AND "branch" IS "T1"."branch"
                                AND "project" IS ?1
                        )
                        GROUP BY "T1"."url", "T1"."branch"
                        UNION
                        SELECT null, "T3"."url", "T3"."branch", null
                        FROM "repos" "T3"
                        WHERE "active" AND "project" IS ?1
                    )
                    GROUP BY "url"
                    ORDER BY "e"
                ''',
                (project_commit,)
            ):
                yield url, branch, head_commit
        finally:
            c.close()

    def list_repobranch_activity(self, project_commit, uri, branch):
        """Lists activity of a repo-branch.

        Args:
            project_commit: The project commit.
            uri: The repo uri.
            branch: The branch.

        Returns:
            list of int: Number of commits between updates.
        """
        c = self.conn.cursor()
        history = c.execute(
            '''
                SELECT "count"
                FROM "repo_history"
                WHERE
                    "url" = ?
                    AND "branch" IS ?
                    AND "project" IS ?
                ORDER BY "entry" ASC
            ''',
            (url, branch, project)
        ).fetchall()
        history = [x for [x] in history]
        c.close()
        return history

    def close(self):
        """Closes the database.
        """
        self.conn.close()

def connect_database(effective_config):
    """Opens the database specified by the given config.

    Args:
        effective_config (ganarchy.data.DataSource): The data source
        for the config.
    """
    del effective_config  # currently unused, intended for the future
    conn = sqlite3.connect(ganarchy.dirs.data_home + "/ganarchy.db")
    return Database(conn)
