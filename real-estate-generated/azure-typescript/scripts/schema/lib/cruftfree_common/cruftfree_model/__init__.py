"""CruftFree Model — the single-layer object graph for .cfree source files.

The package re-exports nothing: every name is imported from the module that
declares it (``cruftfree_common.cruftfree_model.containers.Application``,
``cruftfree_common.cruftfree_model.entity.Entity``, ...), so importing one model
module never loads the rest of the model and each symbol has one import path.
"""
