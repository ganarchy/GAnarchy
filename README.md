GAnarchy
========

GAnarchy is a decentralized project hub. Additionally, it's an attempt to
decentralize development: What if you could build a community around
fragmentation? GAnarchy proposes a development model that is not centered
around "sending patches".

There are not and there never will be Pull Requests, Merge Requests or Email
on GAnarchy.

Quick Start Guide
-----------------

First, initialize the database with `python -m ganarchy initdb`. The database
is stored in the XDG data home, as per the XDG Base Directory specification.

Then create or edit the file `$XDG_CONFIG_HOME/ganarchy/config.toml`. It
can contain the following items, some of which are required:

```toml
# Example GAnarchy config

# The base_url is the web address of the GAnarchy instance.
# Restrictions: MUST be present. SHOULD be https.
base_url = "https://ganarchy.autistic.space/"

# The title is shown on the homepage. If not present, defaults to
# "GAnarchy on [base_url's hostname]".
title = "GAnarchy on autistic.space"

# The repo_list_srcs table references external repo lists, which MUST follow
# the same format as this config but only the projects table (see below) is
# used.
[repo_list_srcs]
# Each repo list src is an URL that points to the repo list.
# Restrictions: active MUST be present. MUST be https or file.
"https://ganarchy.autistic.space/index.toml" = { active=true }
# active=false won't be processed.
"https://ganarchy.github.io/index.toml" = { active=false }

# The projects table is made up of "project commit" hashes (see below for
# what a project commit is)
[projects.385e734a52e13949a7a5c71827f6de920dbfea43]
# Each project is made up of repos and branches
# HEAD is special and refers to the default branch
# Restrictions: active MUST be present. MUST be https.
"https://cybre.tech/SoniEx2/ganarchy".HEAD = { active=true }
# repos/branches with active=false will not be shown or updated.
"https://cybre.tech/SoniEx2/ganarchy".broken = { active=false }
# federate=false won't be shared with other instances, but will be shown and
# updated. (handy if you don't fully trust a repo yet.)
"https://soniex2.autistic.space/git-repos/ganarchy.git"."feature/new-config" = { active=true, federate=false }
```

A project commit is a commit whose message MUST start with `[Project]`
followed by the project name, and may have an optional description.

Example project commit:

```
[Project] GAnarchy

A Project Page Generator written in Python, focused on giving forks of a
project the same visibility as the original repo.
```

The following command generates the output pages in the "public" directory:

```
python -m ganarchy run public
```

You can change the directory by changing "public" to another name, e.g.:

```
python -m ganarchy run output
```

generates an "output" directory instead. You can then upload the result
to your service of choice.

Advanced Usage
--------------

In addition to the basic configuration above, you can also place your own
templates in `$XDG_CONFIG_HOME/ganarchy/templates`.

The current templates are: `index.html`, `index.toml`, `project.html`.

<!-- TODO further docs on advanced usage? -->
