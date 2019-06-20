GAnarchy
========

GAnarchy is a Project Page Generator focused on giving forks of a project the same visibility as the original repo.
More importantly, it's a tool to help fight against BDFLs and other forms of centralized project management.

Basic Usage
-----------

First, initialize the database with `ganarchy.py initdb`. The database is stored in the XDG data home, as per XDG spec.

Then create or edit the file `$XDG_CONFIG_HOME/ganarchy/config.toml`. It should contain the following items:

```
# Example GAnarchy config

# The base_url is the web address of the GAnarchy instance
# Restrictions: MUST be present. SHOULD be https.
base_url = "https://ganarchy.autistic.space/"

# The title is shown on the homepage. If not present, defaults to "GAnarchy on [base_url's hostname]"
title = "GAnarchy on autistic.space"

# The projects table is made up of "project commit" hashes (see below for project commit)
[projects.385e734a52e13949a7a5c71827f6de920dbfea43]
# Each project is made up of repos and branches
# HEAD is special and refers to the default branch
# Restrictions: active MUST be present, file URLs are disallowed
"https://cybre.tech/SoniEx2/ganarchy".HEAD = { active=true }
# repos/branches with active=false will not be shown or updated
"https://cybre.tech/SoniEx2/ganarchy".broken = { active=false }
```

A project commit is a commit that *must* start with `[Project]` followed by the project name, and may have an optional description.

Example project commit:

```
[Project] GAnarchy

A Project Page Generator written in Python, focused on giving forks of a
project the same visibility as the original repo.
```

To generate the output pages:

```
ganarchy.py cron-target index > index.html
ganarchy.py cron-target config > config.toml # if federation is desired
ganarchy.py cron-target $PROJECT_COMMIT > project/$PROJECT_COMMIT/index.html # for each project
```

It's recommended to use a wrapper script to generate the project pages. `ganarchy.py cron-target project-list` may be of use.

Advanced Usage
--------------

In addition to the basic configuration above, you can also place your own templates in `$XDG_CONFIG_HOME/ganarchy/templates`.

The current templates are: `index.html`, `index.toml`, `project.html`.
