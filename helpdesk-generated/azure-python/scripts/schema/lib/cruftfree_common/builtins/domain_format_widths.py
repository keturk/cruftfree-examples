"""The widths of domain scalars whose column is as wide as the format lets a value be.

Kept apart from :mod:`cruftfree_common.builtins.domain_formats`, which reads every
pattern at import: a schema script carries the column widths
(``cruftfree_codegen_kernel.sql_facts.type_mappings``) and must not carry that module.
"""

from __future__ import annotations

from typing import Final

#: The most characters an unsized ``Slug`` holds: the width of its column.
SLUG_UNSIZED_MAX_LENGTH: Final = 255

__all__ = ["SLUG_UNSIZED_MAX_LENGTH"]
