"""SQL text and helpers of the PostgreSQL dialect."""

from __future__ import annotations

from cruftfree_common.utils.sql_text import dollar_quoted

from cruftfree_codegen_kernel.sql_facts.dialects._dialect_statement_types import (
    EnumNeighbour,
    StatementReader,
)
from cruftfree_codegen_kernel.sql_facts.dialects.catalog_read import (
    CatalogClient,
    ClientConnectionVariables,
    ClientCredentialFile,
    ClientTlsVariables,
    TextArraySpelling,
)

#: The pieces of the ``DO`` blocks that make a creation conditional on the catalog.
#: Each renderer builds its block from them and the read-back recognises the same
#: pieces, so the two can never disagree on a spelling.
_IF_BLOCK_CLOSE = " END IF; END"
_UNIQUE_GUARD_OPEN = "BEGIN IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = "
_ENUM_TYPE_GUARD_OPEN = "BEGIN CREATE TYPE "
_ENUM_TYPE_GUARD_CLOSE = "EXCEPTION WHEN duplicate_object OR unique_violation THEN null; END"
_PROMOTE_GUARD_OPEN = "BEGIN IF to_regclass("
_PROMOTE_GUARD_THEN = ") IS NOT NULL THEN "
_PROMOTE_USING_INDEX = " UNIQUE USING INDEX "
_ENUM_TYPE_AS_ENUM = " AS ENUM ("
_ADD_VALUE = " ADD VALUE IF NOT EXISTS "
_ADD_VALUE_AFTER = " AFTER "
_ADD_VALUE_BEFORE = " BEFORE "
_ALTER_TYPE = "ALTER TYPE "
_DROP_TYPE_IF_EXISTS = "DROP TYPE IF EXISTS "
_LABEL_LIST_SEPARATOR = ", "
_LABEL_PREDICATE_OPEN = (
    "EXISTS (SELECT 1 FROM pg_enum e JOIN pg_type t ON t.oid = e.enumtypid "
    "JOIN pg_namespace n ON n.oid = t.typnamespace WHERE t.typname = "
)
_LABEL_PREDICATE_SCHEMA = " AND n.nspname = "
_LABEL_PREDICATE_VISIBLE = " AND pg_type_is_visible(t.oid)"
_LABEL_PREDICATE_LABEL = " AND e.enumlabel = "
_LABEL_PREDICATE_CLOSE = ")"
_RENAME_GUARD_OPEN = "BEGIN IF "
_RENAME_GUARD_CONFLICT = " THEN IF "

_DO_HEAD = "DO "
_DOLLAR = "$"
#: Ends a catalog read's transaction and a schema apply's alike.
_COMMIT = "COMMIT;"
#: The alias of the subquery a catalog query selects its rows in.
_CATALOG_ROW_ALIAS = "q"

#: The psql variable a catalog read's places travel in.
_CATALOG_PLACES_VARIABLE = "places"
#: The stock client of a catalog read (the psql manual): no psqlrc (``-X``), unaligned rows
#: (``-A``, fields split by ``|``), rows only (``-t``), no command tags (``-q``), the input read
#: from standard input (``-f -``), which makes every error name its input line: the server's as
#: ``psql:<stdin>:<line>: ERROR:``, psql's own (a meta-command it does not know) as
#: ``psql:<stdin>:<line>: error:``. ``\bind`` (psql 16+) runs the composed statement under the
#: extended query protocol with the places as ``$1``. It takes ``:places``, not ``:'places'``:
#: in a meta-command argument ``:'var'`` is the value quoted as an SQL literal, quotes included,
#: which the server would read as the array; ``:var`` is the value itself, one argument.
_CATALOG_CLIENT = CatalogClient(
    argv=("psql", "-X", "-A", "-t", "-q", "-f", "-"),
    variable_option="-v",
    places_variable=_CATALOG_PLACES_VARIABLE,
    opening="\\set ON_ERROR_STOP on",
    run_bound=f"\\bind :{_CATALOG_PLACES_VARIABLE} \\g",
    field_separator="|",
    array=TextArraySpelling(open="{", close="}", separator=",", quote='"', escape="\\"),
    error_line_prefix="psql:<stdin>:",
    error_line_markers=(": ERROR:", ": error:"),
    # libpq's connection variables (the libpq manual, "Environment Variables").
    connection=ClientConnectionVariables(
        host="PGHOST", port="PGPORT", database="PGDATABASE", user="PGUSER"
    ),
    # libpq's TLS variables, and its mode that verifies the chain and the host name (the
    # libpq manual, "SSL Support"); sslrootcert=system (libpq 16+) verifies against the
    # operating system's trust store and forces verify-full. prefer is libpq's and asyncpg's
    # default mode: TLS when the server offers it, unverified.
    tls=ClientTlsVariables(
        mode="PGSSLMODE",
        root_certificate="PGSSLROOTCERT",
        verified_mode="verify-full",
        system_root="system",
        opportunistic_mode="prefer",
        chain_mode="verify-ca",
    ),
    # libpq's password file (the libpq manual, "The Password File"): one line
    # hostname:port:database:username:password, '*' matching any value of a field, and
    # '\' before each '\' and ':' of a value. libpq reads it only when it is not group- or
    # world-readable. PGPASSWORD is libpq's password variable ("Environment Variables").
    credential=ClientCredentialFile(
        variable="PGPASSFILE",
        prefix="*:*:*:*:",
        escape="\\",
        escaped=("\\", ":"),
        password_variable="PGPASSWORD",
    ),
)
#: The most arguments a PostgreSQL function takes (``FUNC_MAX_ARGS``); ``json_build_object``
#: takes two per member.
_FUNCTION_ARGUMENT_LIMIT = 100
#: The digest of a catalog read's document ``d.doc``: SHA-256 over its UTF-8 text, in hex. The
#: read prints it and the fingerprint guard recomputes it, from this one spelling.
_DOCUMENT_DIGEST = "encode(sha256(convert_to(d.doc, 'UTF8')), 'hex')"
#: The PL/pgSQL variable the fingerprint guard recomputes the digest into.
_GUARD_DIGEST_VARIABLE = "now_digest"


def _read_neighbour(reader: StatementReader) -> EnumNeighbour | None:
    """The ``AFTER``/``BEFORE '<label>'`` an ``ADD VALUE`` carries, or ``None`` for a bare append.

    What follows is not checked here: the caller re-renders the statement from what
    was read and accepts it only when that reproduces it exactly.
    """
    for keyword, before in ((_ADD_VALUE_AFTER, False), (_ADD_VALUE_BEFORE, True)):
        if reader.keyword(keyword):
            label = reader.literal()
            return None if label is None else EnumNeighbour(label=label, before=before)
    return None


def _do_block_body(head: str) -> str | None:
    """The body of ``DO <tag> <body> <tag>;`` as :func:`dollar_quoted` writes it, else ``None``.

    The body is accepted only when quoting it again reproduces *head* exactly, so
    the tag read is the one the renderer chose.
    """
    if not head.startswith(_DO_HEAD + _DOLLAR):
        return None
    tag_end = head.find(_DOLLAR, len(_DO_HEAD) + 1)
    if tag_end < 0:
        return None
    tag = head[len(_DO_HEAD):tag_end + 1]
    opening = f"{_DO_HEAD}{tag} "
    closing = f" {tag};"
    if len(head) < len(opening) + len(closing) or not head.endswith(closing):
        return None
    body = head[len(opening):len(head) - len(closing)]
    if f"{_DO_HEAD}{dollar_quoted(body)};" != head:
        return None
    return body


def _schema_and_name(reader: StatementReader) -> tuple[str | None, str] | None:
    """Consume an identifier optionally qualified by a schema; return ``(schema, name)``."""
    first = reader.identifier()
    if first is None:
        return None
    if not reader.keyword("."):
        return None, first
    name = reader.identifier()
    return None if name is None else (first, name)


def _label_list(reader: StatementReader) -> tuple[str, ...] | None:
    """Consume ``'a', 'b', ...`` -- one or more literals -- and return the labels."""
    labels: list[str] = []
    while True:
        label = reader.literal()
        if label is None:
            return None
        labels.append(label)
        if not reader.keyword(_LABEL_LIST_SEPARATOR):
            return tuple(labels)


def _label_predicate(reader: StatementReader) -> tuple[str, str | None, str] | None:
    """Consume the catalog predicate ``_enum_label_exists_predicate`` builds.

    Returns:
        ``(type name, schema, label)``; the schema is ``None`` when the predicate
        looks the type up on the ``search_path``.
    """
    if not reader.keyword(_LABEL_PREDICATE_OPEN):
        return None
    type_name = reader.literal()
    if type_name is None:
        return None
    schema: str | None = None
    if reader.keyword(_LABEL_PREDICATE_SCHEMA):
        schema = reader.literal()
        if schema is None:
            return None
    elif not reader.keyword(_LABEL_PREDICATE_VISIBLE):
        return None
    if not reader.keyword(_LABEL_PREDICATE_LABEL):
        return None
    label = reader.literal()
    if label is None or not reader.keyword(_LABEL_PREDICATE_CLOSE):
        return None
    return type_name, schema, label
