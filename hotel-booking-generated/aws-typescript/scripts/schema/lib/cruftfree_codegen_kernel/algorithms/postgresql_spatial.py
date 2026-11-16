"""PostgreSQL spatial-index access method.

The spatial counterpart of :mod:`~cruftfree_codegen_kernel.algorithms.postgresql_fulltext`:
the physical index METHOD a geographic column's index is built with, kept in one place
so a target's ORM declaration and its migration DDL can never name different methods
for the same object. The index NAME is not here -- every index and constraint name
comes from :mod:`cruftfree_rdbms_schema.index_naming`.
"""

from __future__ import annotations

__all__ = ["SPATIAL_INDEX_METHOD"]

#: PostgreSQL index method for a spatial (geographic) column. A GiST index is the
#: only method that answers the containment/proximity queries a geographic column
#: exists for, so every target realizing the spatial kind on PostgreSQL emits this
#: one method.
SPATIAL_INDEX_METHOD = "gist"
