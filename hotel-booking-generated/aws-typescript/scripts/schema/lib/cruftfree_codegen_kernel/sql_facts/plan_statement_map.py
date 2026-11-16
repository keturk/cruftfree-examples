"""A plan phase's statement map: which statement, and which change, owns each line of its SQL file.

A failed apply names the line of the SQL file its client stopped at. The process that runs the
apply never holds the :class:`~cruftfree_codegen_kernel.sql_facts.convergence.PlanPhase` that file
was written from, so the plan writes, beside each SQL file, the phase's statements as JSON: each
statement's line range, its owner and the kind of the change it renders, bound to the exact SQL
bytes by their SHA-256. :func:`load_statement_map` reads that document back with the standard
library alone into a :class:`StatementMap`, whose ``statement_at`` names the same owner and change
kind as the phase's ``statement_at``.

The loader fails closed. A document that is not JSON, holds a key, a value or a type the map does
not define, leaves a line of the SQL unmapped, maps a line twice, or was written for other SQL
bytes is refused with a :class:`StatementMapError` naming why: a map that does not describe the
file the client ran would name the wrong statement.
"""

from __future__ import annotations

import hashlib
import itertools
import json
import re
from dataclasses import dataclass
from typing import TYPE_CHECKING, Final

if TYPE_CHECKING:
    from pathlib import Path

    from cruftfree_codegen_kernel.sql_facts.convergence import PlanPhase

__all__ = [
    "PLAN_FILE_ENCODING",
    "STATEMENT_MAP_SUFFIX",
    "MappedStatement",
    "StatementMap",
    "StatementMapError",
    "load_statement_map",
    "sql_file_bytes",
    "statement_map_document",
    "statement_map_path",
]

#: How a phase's SQL file and its statement map are written: every character as it is,
#: nothing translated.
PLAN_FILE_ENCODING: Final[str] = "utf-8"

#: What a SQL file's name gains to name its statement map: ``<sql file>.statements.json``.
STATEMENT_MAP_SUFFIX: Final[str] = ".statements.json"

_SQL_DIGEST_KEY: Final[str] = "sql_sha256"
_STATEMENTS_KEY: Final[str] = "statements"
_FIRST_LINE_KEY: Final[str] = "first_line"
_LAST_LINE_KEY: Final[str] = "last_line"
_OWNER_KEY: Final[str] = "owner"
_CHANGE_KIND_KEY: Final[str] = "change_kind"

_DOCUMENT_KEYS: Final[frozenset[str]] = frozenset({_SQL_DIGEST_KEY, _STATEMENTS_KEY})
_STATEMENT_KEYS: Final[frozenset[str]] = frozenset(
    {_FIRST_LINE_KEY, _LAST_LINE_KEY, _OWNER_KEY, _CHANGE_KIND_KEY}
)
_SHA256_HEX: Final[re.Pattern[str]] = re.compile(r"[0-9a-f]{64}")
_LINE_BREAK: Final[bytes] = b"\n"


class StatementMapError(ValueError):
    """A statement map that does not describe the SQL file beside it; the message says why."""


@dataclass(frozen=True)
class MappedStatement:
    """One statement of a phase's SQL file, as its statement map records it.

    Attributes:
        first_line: The file's line the statement starts at, numbered from 1.
        last_line: The file's line it ends at; never before ``first_line``.
        owner: What the statement is, as a failed apply names it (``PlanStatement.owner``).
        change_kind: The kind of the change it renders (``ChangeKind`` value); ``None`` for a
            guard, the transaction's begin or commit, the schema prelude or the catalog
            statement.
    """

    first_line: int
    last_line: int
    owner: str
    change_kind: str | None


@dataclass(frozen=True)
class StatementMap:
    """Every line of one SQL file, each owned by exactly one statement.

    Attributes:
        sql_sha256: The SHA-256 of the SQL file's bytes, lowercase hex.
        statements: The statements in file order; their line ranges cover the file from line 1
            to its last line, each line once.
    """

    sql_sha256: str
    statements: tuple[MappedStatement, ...]

    def statement_at(self, line: int) -> MappedStatement | None:
        """The statement line *line* (numbered from 1) of the SQL belongs to; ``None`` past it."""
        for statement in self.statements:
            if statement.first_line <= line <= statement.last_line:
                return statement
        return None


def statement_map_path(sql_path: Path) -> Path:
    """Where the statement map of the SQL file at *sql_path* lies: beside it, its name suffixed."""
    return sql_path.with_name(f"{sql_path.name}{STATEMENT_MAP_SUFFIX}")


def sql_file_bytes(phase: PlanPhase) -> bytes:
    """*phase*'s SQL as its file holds it, the bytes its statement map's digest is taken of."""
    return phase.sql.encode(PLAN_FILE_ENCODING)


def _sql_digest(sql: bytes) -> str:
    return hashlib.sha256(sql).hexdigest()


def statement_map_document(phase: PlanPhase) -> str:
    """*phase*'s statement map as JSON: each statement's line range, owner and change kind.

    The ranges come from ``phase.lines``, the same line split ``phase.sql`` and
    ``phase.statement_at`` use, so line *n* of the map is line *n* of the file. A phase with no
    statement maps no line of its empty file.
    """
    statements: list[dict[str, object]] = []
    first_line = 1
    for _, group in itertools.groupby(phase.lines, key=lambda pair: id(pair[1])):
        owned = tuple(group)
        statement = owned[0][1]
        last_line = first_line + len(owned) - 1
        statements.append(
            {
                _FIRST_LINE_KEY: first_line,
                _LAST_LINE_KEY: last_line,
                _OWNER_KEY: statement.owner,
                _CHANGE_KIND_KEY: (
                    None if statement.change is None else statement.change.kind.value
                ),
            }
        )
        first_line = last_line + 1
    document = {
        _SQL_DIGEST_KEY: _sql_digest(sql_file_bytes(phase)),
        _STATEMENTS_KEY: statements,
    }
    return json.dumps(document, indent=2, ensure_ascii=False) + "\n"


def _refuse_duplicate_keys(pairs: list[tuple[str, object]]) -> dict[str, object]:
    keys = [key for key, _ in pairs]
    repeated = sorted({key for key in keys if keys.count(key) > 1})
    if repeated:
        raise StatementMapError(f"the statement map repeats the key(s) {repeated}")
    return dict(pairs)


def _refuse_constant(name: str) -> object:
    raise StatementMapError(f"the statement map holds {name}, which is not a JSON number")


def _parsed(document: bytes) -> object:
    try:
        text = document.decode(PLAN_FILE_ENCODING)
    except UnicodeDecodeError as error:
        raise StatementMapError(f"the statement map is not UTF-8: {error}") from error
    try:
        return json.loads(
            text,
            object_pairs_hook=_refuse_duplicate_keys,
            parse_constant=_refuse_constant,
        )
    except json.JSONDecodeError as error:
        raise StatementMapError(f"the statement map is not JSON: {error}") from error


def _object(value: object, keys: frozenset[str], what: str) -> dict[str, object]:
    if not isinstance(value, dict):
        raise StatementMapError(f"{what} is a JSON {type(value).__name__}, not an object")
    missing = sorted(keys - value.keys())
    unknown = sorted(value.keys() - keys)
    if missing or unknown:
        raise StatementMapError(
            f"{what} must hold exactly the keys {sorted(keys)}; "
            f"missing {missing}, unknown {unknown}"
        )
    return value


def _line_number(value: object, key: str, what: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 1:
        raise StatementMapError(f"{what}'s {key} is {value!r}, not a line number from 1")
    return value


def _text(value: object, key: str, what: str) -> str:
    if not isinstance(value, str) or not value:
        raise StatementMapError(f"{what}'s {key} is {value!r}, not a non-empty string")
    return value


def _statement(value: object, index: int) -> MappedStatement:
    what = f"statement {index} of the statement map"
    fields = _object(value, _STATEMENT_KEYS, what)
    first_line = _line_number(fields[_FIRST_LINE_KEY], _FIRST_LINE_KEY, what)
    last_line = _line_number(fields[_LAST_LINE_KEY], _LAST_LINE_KEY, what)
    if last_line < first_line:
        raise StatementMapError(
            f"{what} ends at line {last_line}, before the line {first_line} it starts at"
        )
    change_kind = fields[_CHANGE_KIND_KEY]
    return MappedStatement(
        first_line=first_line,
        last_line=last_line,
        owner=_text(fields[_OWNER_KEY], _OWNER_KEY, what),
        change_kind=(
            None if change_kind is None else _text(change_kind, _CHANGE_KIND_KEY, what)
        ),
    )


def _require_contiguous(statements: tuple[MappedStatement, ...]) -> None:
    """Each statement starts on the line after the one before it ends: no line twice, none skipped."""
    expected = 1
    for index, statement in enumerate(statements, start=1):
        if statement.first_line < expected:
            raise StatementMapError(
                f"statement {index} of the statement map starts at line "
                f"{statement.first_line}, which statement {index - 1} already maps: "
                "the statements overlap"
            )
        if statement.first_line > expected:
            raise StatementMapError(
                f"the statement map leaves lines {expected}-{statement.first_line - 1} "
                f"unmapped before statement {index}"
            )
        expected = statement.last_line + 1


def _line_count(sql: bytes) -> int:
    """How many lines *sql* holds, the last one counted whether or not a line break ends it."""
    if not sql:
        return 0
    return sql.count(_LINE_BREAK) + (0 if sql.endswith(_LINE_BREAK) else 1)


def load_statement_map(document: bytes, sql: bytes) -> StatementMap:
    """The statement map *document* holds, refused unless it describes exactly *sql*.

    Args:
        document: The map file's bytes, as :func:`statement_map_document` wrote them.
        sql: The bytes of the SQL file the map was written beside.

    Raises:
        StatementMapError: *document* is not UTF-8 JSON, holds a key, value or type the map
            does not define, maps a line twice or leaves one unmapped, was written for other
            bytes than *sql*, or does not end at *sql*'s last line.
    """
    fields = _object(_parsed(document), _DOCUMENT_KEYS, "the statement map")
    digest = fields[_SQL_DIGEST_KEY]
    if not isinstance(digest, str) or not _SHA256_HEX.fullmatch(digest):
        raise StatementMapError(
            f"the statement map's {_SQL_DIGEST_KEY} is {digest!r}, not 64 lowercase hex digits"
        )
    listed = fields[_STATEMENTS_KEY]
    if not isinstance(listed, list):
        raise StatementMapError(
            f"the statement map's {_STATEMENTS_KEY} is a JSON {type(listed).__name__}, not a list"
        )
    statements = tuple(_statement(value, index) for index, value in enumerate(listed, start=1))
    _require_contiguous(statements)
    actual = _sql_digest(sql)
    if digest != actual:
        raise StatementMapError(
            f"the statement map was written for other SQL: it records SHA-256 {digest}, "
            f"the SQL file's bytes hash to {actual}"
        )
    mapped = statements[-1].last_line if statements else 0
    lines = _line_count(sql)
    if mapped != lines:
        raise StatementMapError(
            f"the statement map maps {mapped} line(s), the SQL file holds {lines}"
        )
    return StatementMap(sql_sha256=digest, statements=statements)
