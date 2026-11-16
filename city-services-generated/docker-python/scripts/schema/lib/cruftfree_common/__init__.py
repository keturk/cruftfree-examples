"""CruftFree common: the foundation package (AST model, types, config, plugin and
deployment declarations). Semantic analysis, code generation, migrations and
the transpiler each moved to their own package (``cruftfree_semantic``,
``cruftfree_codegen_kernel``/``cruftfree_codegen_common``, ``cruftfree_rdbms_schema``,
``cruftfree_codegen_common.transpiler``) that depends on this one.

Import each name from the submodule that defines it (for example
``from cruftfree_common.constants import CRUFTFREE_FILE_EXTENSION``). This package
``__init__`` deliberately imports nothing: the ``pytest11`` feature-tag plugin
(``cruftfree_common.testing.feature_tags``) loads into every pytest session in the
shared venv, and any import here would load into every one of those sessions
with it.
"""
