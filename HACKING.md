Hacking GAnarchy
================

Project Structure
-----------------

`requirements.txt` lists known-good, frozen dependencies. if needed or
desired, install dependencies listed in setup.py directly.

GAnarchy uses GAnarchy-based dependencies. they are identified by `gan$COMMIT`
names. e.g. in requirements.txt:

```
-e git+https://soniex2.autistic.space/git-repos/abdl.git@1b26ad799217af7e187fdae78e862a6bf46e5591#egg=gan0f74bd87a23b515b45da7e6f5d9cc82380443dab
```

or in setup.py:

```
install_requires=[
    "gan0f74bd87a23b515b45da7e6f5d9cc82380443dab",  # a boneless datastructure library
]
```

(the comment is just a hint for humans to read)

note however that not all forks are compatible with the project.
requirements.txt provides known-good versions.

Input Validation
----------------

GAnarchy accepts untrusted input: from the user, from remote servers, etc.

Where relevant, input should be validated in `data.py`. For example, URIs
should be normalized (domain and protocol should be converted to
all-lowercase), NULs should be rejected, etc. (FIXME: As of writing this, this
is not the case)
