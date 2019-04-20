GAnarchy
========

GAnarchy is a Project Page Generator focused on giving forks of a project the same visibility as the original repo.
More importantly, it's a tool to help fight against BDFLs and other forms of centralized project management.

Usage
-----

First, initialize the database with `ganarchy.py initdb`. The database is stored in the XDG data home, as per XDG spec.

Then, set the project commit with `ganarchy.py set-commit COMMIT`, where `COMMIT` is the full commit hash.
The commit *must* start with `[Project]` followed by the project name, and may have an optional description.
(Note: This requirement isn't currently checked, but will be in the future. This is important for a future federation
protocol that allows for automatically discovering forks based on the project commit.)

Currently, you also need to set the project title manually using `ganarchy.py set-project-title PROJECT-TITLE`. This will
be replaced with the above mechanism in the future.

Once everything is initialized, add some repos with `ganarchy.py repo add URL`, and enable them with `ganarchy.py repo enable URL`
(they come disabled by default). You are now ready to go.

Finally, add `ganarchy.py cron-target > path/to/page.html` to your cron. Optionally `scp page.html scp://server@example.org/page.html`.

Example shell session:

```text
$ ganarchy.py initdb
$ ganarchy.py set-commit 385e734a52e13949a7a5c71827f6de920dbfea43
$ ganarchy.py set-project-name GAnarchy
$ ganarchy.py repo add https://cybre.tech/SoniEx2/ganarchy
$ ganarchy.py repo enable https://cybre.tech/SoniEx2/ganarchy
$ ganarchy.py cron-target > index.html
$ scp index.html scp://example.org/var/www/html/index.html
```

Example project commit:

```
[Project] GAnarchy

A Project Page Generator written in Python, focused on giving forks of a
project the same visibility as the original repo.
```