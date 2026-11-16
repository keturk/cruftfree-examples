"""The database DEFAULT of a collection-typed column.

A collection field (``Array<T>``, ``Set<T>``, ``Map<K, V>``) and a ``JSON``
field are stored in one JSON column on every dialect, so a collection literal
default is a JSON document after ``DEFAULT``. The document is the one the
default declares (:func:`cruftfree_common.cruftfree_model.collection_default.collection_default_document`),
the text a schema snapshot records for it, so the ``CREATE TABLE`` DDL and every
migration adapter state the same default -- ``["a", "b"]`` for
``['a', 'b']``, never a shortened ``[]``. How the document is placed after
``DEFAULT`` is the dialect's (:meth:`SQLDialect.json_column_default`).
"""

from __future__ import annotations

import json
from typing import Final

from cruftfree_codegen_kernel.sql_facts.dialects.dialect_table import sql_dialect
from cruftfree_codegen_kernel.sql_facts.errors import TypeMappingError

__all__ = ["collection_default_sql", "is_collection_default_source"]

_COLLECTION_OPENERS: Final[tuple[str, ...]] = ("[", "{")


def is_collection_default_source(source_text: str) -> bool:
    """True when *source_text* is the recorded document of a collection literal default."""
    return source_text.strip().startswith(_COLLECTION_OPENERS)


def collection_default_sql(document: str, ddl_dialect: str, *, column: str) -> str:
    """The expression after ``DEFAULT`` for a collection literal default.

    Args:
        document: The JSON document the default declares, as a schema snapshot
            records it (``[]``, ``{}``, ``["a", "b"]``).
        ddl_dialect: Target DDL dialect name.
        column: The column (or field) name, for the error message.

    Returns:
        The dialect's JSON-column default expression for the document.

    Raises:
        TypeMappingError: *document* is not a JSON array or object -- a snapshot
            recorded by an older rule, or not a collection default at all.
        DialectNotFoundError: *ddl_dialect* is not a registered DDL dialect.
    """
    text = document.strip()
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError as exc:
        raise TypeMappingError(
            f"Column '{column}' records the collection default {document!r}, which is not a "
            f"JSON document ({exc.msg}). Expected: the JSON array or object the default "
            'declares, as the schema snapshot records it (e.g. [] or ["a"]). Fix: regenerate '
            "the block so its schema snapshot records the default's document."
        ) from exc
    if not isinstance(parsed, (list, dict)):
        raise TypeMappingError(
            f"Column '{column}' records the collection default {document!r}, which is a JSON "
            f"{type(parsed).__name__}, not an array or object. Expected: the document of a "
            "list or map literal default."
        )
    return sql_dialect(ddl_dialect).json_column_default(text)
