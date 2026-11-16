"""Generation framework -- generators, generated files, templates, and discovery.

Import each name from the submodule that defines it. This package ``__init__``
deliberately re-exports nothing: the language layer in ``cruftfree-codegen-common``
imports these submodules, and an eager re-export here would load the whole
generation framework on the first import of any one submodule.
"""
