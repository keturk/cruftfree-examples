"""The one rule that names a constraint by its definition.

A check constraint has no column list to name it by, and the engine re-prints the
SQL CruftFree wrote in its own normalized form, so whether a live check is the declared
one cannot be decided by reading its SQL back. The name decides it instead: it
carries the digest of the definition, so two checks are the same check exactly when
their names are equal, and a changed definition is a new name -- the old check is
dropped and the new one created, never compared or parsed.

The name is ``<kind>_<table>_<subject>_<digest>``: the digest is the first 8 hex
characters of the SHA-256 of the definition's SQL as the block's dialect renders it.
It is capped by :func:`~cruftfree_common.utils.identifier_case.truncate_identifier` with the digest
as the trailing component, which is re-appended after any truncation, so a long name
still ends in its digest. :func:`~cruftfree_common.utils.identifier_case.truncate_db_identifier` is
not used: it cuts the end of the name, digest included.

This module sits in ``cruftfree-rdbms-schema`` beside :mod:`cruftfree_rdbms_schema.index_naming`
because the snapshot builder records the names it derives.
"""

from __future__ import annotations

import hashlib

from cruftfree_common.utils.identifier_case import (
    DB_MAX_IDENTIFIER_LENGTH,
    truncate_identifier,
)

__all__ = [
    "CHECK_KIND",
    "DEFINITION_DIGEST_LENGTH",
    "definition_digest",
    "definition_name",
]

#: Kind marker of a check constraint name.
CHECK_KIND = "chk"
#: Hex characters of the definition's SHA-256 a name ends in.
DEFINITION_DIGEST_LENGTH = 8


def definition_digest(definition_sql: str) -> str:
    """The digest a definition-named constraint ends in.

    Args:
        definition_sql: The constraint's definition, as the block's dialect renders it.

    Returns:
        The first :data:`DEFINITION_DIGEST_LENGTH` hex characters of its SHA-256.
    """
    digest = hashlib.sha256(definition_sql.encode("utf-8")).hexdigest()
    return digest[:DEFINITION_DIGEST_LENGTH]


def definition_name(kind: str, table: str, subject: str, definition_sql: str) -> str:
    """Name a constraint by its kind, table, subject and definition.

    Args:
        kind: The constraint kind marker (:data:`CHECK_KIND`).
        table: Physical name of the table holding the constraint.
        subject: What the constraint governs on the table: a column, a relationship,
            or ``rule``.
        definition_sql: The constraint's definition, as the block's dialect renders it.

    Returns:
        ``<kind>_<table>_<subject>_<digest>``, capped at the identifier limit and
        always ending in the digest of *definition_sql*.
    """
    return truncate_identifier(
        "%s_%s_%s" % (kind, table, subject),
        DB_MAX_IDENTIFIER_LENGTH,
        separator="_",
        trailing=definition_digest(definition_sql),
    )
