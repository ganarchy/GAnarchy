GAnarchy
========

GAnarchy is a Project Page Generator focused on giving forks of a project the same visibility as the original repo.
More importantly, it's a tool to help fight against BDFLs and other forms of centralized project management.

Basic Usage
-----------

Note: GAnarchy does not come with a main page. You need to provide one yourself. This should be in your website's `/` path (usually `index.html`).
The protocol handler uses the path `/?url=%s`. Additionally, your main page needs to include the `index.js` provided by GAnarchy
for the protocol handler to properly work.

First, initialize the database with `ganarchy.py initdb`. The database is stored in the XDG data home, as per XDG spec.

Then, set the project commit with `ganarchy.py set-commit COMMIT`, where `COMMIT` is the full commit hash.
The commit *must* start with `[Project]` followed by the project name, and may have an optional description.
(Note: This requirement isn't properly checked, but will be in the future. This is important for a future federation
protocol that allows for automatically discovering forks based on the project commit.)

Once everything is initialized, add some repos with `ganarchy.py repo add URL`, and enable or disable them with `ganarchy.py repo enable URL` or
`ganarchy.py repo disable URL`. They currently come enabled by default. You are now ready to go.

Finally, add `ganarchy.py cron-target > path/to/page.html` to your cron. Optionally `scp page.html scp://server@example.org/page.html`.

Example shell session:

```text
$ ganarchy.py initdb
$ ganarchy.py set-commit 385e734a52e13949a7a5c71827f6de920dbfea43
$ ganarchy.py set-project-name GAnarchy
$ ganarchy.py repo add https://cybre.tech/SoniEx2/ganarchy
$ ganarchy.py cron-target > index.html
$ scp index.html scp://example.org/var/www/html/index.html
```

Example project commit:

```
[Project] GAnarchy

A Project Page Generator written in Python, focused on giving forks of a
project the same visibility as the original repo.
```

Advanced Usage
--------------

It's also possible to use the same GAnarchy DB with multiple projects. This is currently done by passing `--project COMMIT` to the `repo` commands,
and using `cron-target COMMIT`.

Note that the same repo may be part of multiple projects, so it is necessary to specify `--project COMMIT` also when enabling/disabling it.

Additionally, it's possible to set a non-default branch by passing `--branch BRANCHNAME` to the `repo` commands. Given that multiple branches of
the same repo may be part of the same project, it is also necessary to use `--branch BRANCHNAME` when enabling/disabling them.
