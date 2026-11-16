"""Target-neutral generation kernel every CruftFree generator builds on.

Holds the generator and generated-file base classes, the template engine,
plugin discovery helpers, the type-mapping registry, the shared route and
runtime-configuration derivations, the deploy-script machinery, the DAL generator
data model and registries, and the Seed reference datasets.

Import each name from the submodule that defines it. This package ``__init__``
deliberately re-exports nothing, so importing one kernel module never loads
the rest of the kernel.
"""
