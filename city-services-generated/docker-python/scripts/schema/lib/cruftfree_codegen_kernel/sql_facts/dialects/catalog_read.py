"""The input of one consistent catalog read: its guards, its transaction, its one statement and its client.

A catalog read runs as one client input: the block's lock taken under a guard, the
running server's version checked under a guard, a read-only transaction around the
one statement that reads the catalog, and the lock released under a guard. The
read's digest is the catalog fingerprint; the fingerprint guard recomputes it from
the same document and stops an input planned from that read when it moved.
:class:`CatalogReadStatements` is the part of the ``SQLDialect`` protocol that
spells them, the expressions of the running server's version
(:class:`ServerVersionSql`) and the stock client that runs them
(:class:`CatalogClient`); :class:`CatalogReadRefusals` is what
``DialectBase`` gives a dialect that does not override them: each method refuses,
naming the dialect.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import TYPE_CHECKING, Final, NoReturn, Protocol

from cruftfree_codegen_kernel.sql_facts.errors import DialectFeatureError

if TYPE_CHECKING:
    from collections.abc import Sequence

    from cruftfree_rdbms_schema.catalog_reader import CatalogQuery

#: Characters a place cannot hold in the client argument: a line break would split the one
#: line the argument is printed on, and a NUL cannot travel in a process argument.
_ARGUMENT_BREAKING: Final[tuple[str, ...]] = ("\n", "\r", "\x00")
#: A catalog fingerprint: the SHA-256 of a read's document, as the server prints it in hex.
_CATALOG_FINGERPRINT: Final[re.Pattern[str]] = re.compile(r"[0-9a-f]{64}")


@dataclass(frozen=True)
class TextArraySpelling:
    """How the client argument spells a text array: its delimiters, element quote and escape.

    Every element is quoted, and the escape precedes each escape and quote character
    an element holds, so no element is read as a delimiter, a keyword or a nested array.
    """

    open: str
    close: str
    separator: str
    quote: str
    escape: str


@dataclass(frozen=True)
class ClientConnectionVariables:
    """The environment variables the stock client reads where to connect and as whom.

    A workload that runs the client sets them, so neither the server nor the login travels
    in the client's arguments; no password variable is among them.

    Attributes:
        host: The server's host name or address.
        port: The server's port.
        database: The database the client connects to.
        user: The login the client connects as.
    """

    host: str
    port: str
    database: str
    user: str


@dataclass(frozen=True)
class ClientTlsVariables:
    """The environment variables that set the TLS the stock client reaches its server with.

    A workload reaching a managed database sets ``mode`` to ``verified_mode`` and
    ``root_certificate`` to the CA bundle it carries, or to ``system_root`` for a server whose
    CA no bundle the deploy fetches names, so the client refuses a server whose certificate
    does not chain to it or does not name the host. A workload reaching an external server
    whose block declares no TLS (``ssl = false``) sets ``mode`` to ``opportunistic_mode`` and
    no ``root_certificate``: the TLS the block's own engines connect with.

    Attributes:
        mode: The variable naming the client's TLS mode.
        root_certificate: The variable naming the CA bundle file the server is verified against.
        verified_mode: The mode that requires TLS and verifies the certificate and the host name.
        system_root: The ``root_certificate`` value that verifies against the operating
            system's trust store.
        opportunistic_mode: The mode that uses TLS when the server offers it, without
            verifying the certificate, and connects without TLS otherwise: the engines'
            drivers' own default.
        chain_mode: The mode that requires TLS and verifies the certificate chain against the
            root certificate without checking the host name: the mode of an external block
            whose ``verifyHostName`` is ``false``.
    """

    mode: str
    root_certificate: str
    verified_mode: str
    system_root: str
    opportunistic_mode: str
    chain_mode: str


@dataclass(frozen=True)
class ClientCredentialFile:
    """The file the stock client reads its password from, and how its one line is spelled.

    A workload writes the block's owner credential into this file and sets ``variable`` to its
    path, so no argument and no environment variable holds the secret.

    Attributes:
        variable: The environment variable naming the file.
        prefix: What precedes the secret on the line: the fields that match any server,
            port, database and login.
        escape: The character that makes the one after it literal.
        escaped: The characters of the secret the escape precedes, the escape itself first
            so an escape added for a later character is not escaped again.
        password_variable: The environment variable the stock client would read the secret
            itself from. No generated workload sets or names it: a platform's container
            environment is visible to its API.
    """

    variable: str
    prefix: str
    escape: str
    escaped: tuple[str, ...]
    password_variable: str

    def __post_init__(self) -> None:
        if not self.password_variable or self.password_variable == self.variable:
            raise ValueError(
                f"A credential file was given the password variable {self.password_variable!r} "
                f"beside the file variable {self.variable!r}. Name the variable the stock client "
                "reads a password from, so a command setting it is refused."
            )
        if not self.escaped or self.escaped[0] != self.escape:
            raise ValueError(
                f"A credential file was given the escaped characters {self.escaped!r} with the "
                f"escape {self.escape!r}. Name the escape first, so the escapes added for the "
                "other characters are not escaped again."
            )

    def line(self, secret: str) -> str:
        """The file's one line holding *secret*, without its line break.

        Raises:
            ValueError: *secret* is empty or holds a line break.
        """
        if not secret or "\n" in secret or "\r" in secret:
            raise ValueError(
                "A credential file line was given an empty secret or one holding a line break; "
                "the file holds the secret on one line."
            )
        escaped = secret
        for character in self.escaped:
            escaped = escaped.replace(character, f"{self.escape}{character}")
        return f"{self.prefix}{escaped}"


@dataclass(frozen=True)
class CatalogClient:
    """The stock client a catalog read runs under, and how its input and output are spelled.

    Attributes:
        argv: The client program and the options that make it read its input from
            standard input, print the rows only, and name the input line of a failure.
        variable_option: The option that sets a client variable.
        places_variable: The client variable the places travel in.
        opening: The input's first line: the client stops at the first failing statement.
        run_bound: Follows the composed statement: runs it with the places variable
            bound as its first parameter, never written into the query text.
        field_separator: Separates the fields of the printed row.
        array: How the places argument spells its text array.
        error_line_prefix: The text before the input line number a failure names.
        error_line_markers: The texts, any one of which follows that number on an error
            line: the server's error and the client's own (a command it does not know),
            never a notice or a warning.
        connection: The environment variables the client reads its server and login from.
        tls: The environment variables that make the client verify the server it reaches.
        credential: The file the client reads the login's secret from.
    """

    argv: tuple[str, ...]
    variable_option: str
    places_variable: str
    opening: str
    run_bound: str
    field_separator: str
    array: TextArraySpelling
    error_line_prefix: str
    error_line_markers: tuple[str, ...]
    connection: ClientConnectionVariables
    tls: ClientTlsVariables
    credential: ClientCredentialFile

    def __post_init__(self) -> None:
        if not self.error_line_markers or not all(self.error_line_markers):
            raise ValueError(
                f"A catalog client was given the error line markers {self.error_line_markers!r}. "
                "Name each non-empty text that follows the line number on an error line, so a "
                "notice or a warning is never read as the failure."
            )

    def places_argument(self, places: Sequence[str]) -> str:
        """*places* as the one text-array value the places variable holds.

        Raises:
            ValueError: *places* is empty, or a place holds a line break or a NUL.
        """
        if not places:
            raise ValueError(
                "A catalog read was given no places to bind. Pass the schemas the "
                "queries read, as CatalogQuery.places holds them."
            )
        for place in places:
            held = [
                repr(character)
                for character in _ARGUMENT_BREAKING
                if character in place
            ]
            if held:
                raise ValueError(
                    f"The place {place!r} holds {', '.join(held)}, which the client argument "
                    "cannot carry on one line. A schema name holds no line break or NUL."
                )
        spelling = self.array
        escaped = (
            place.replace(
                spelling.escape, f"{spelling.escape}{spelling.escape}"
            ).replace(spelling.quote, f"{spelling.escape}{spelling.quote}")
            for place in places
        )
        elements = spelling.separator.join(
            f"{spelling.quote}{element}{spelling.quote}" for element in escaped
        )
        return f"{spelling.open}{elements}{spelling.close}"

    def places_option(self, places: Sequence[str]) -> tuple[str, str]:
        """The two client arguments that set the places variable to *places*.

        Raises:
            ValueError: As :meth:`places_argument`.
        """
        return (
            self.variable_option,
            f"{self.places_variable}={self.places_argument(places)}",
        )

    def failed_line(self, stderr: str) -> int | None:
        """The input line the client's first error names in *stderr*, or ``None`` when none does.

        ``None`` is a failure before any input line ran (the client could not connect,
        an option was refused); the caller names that failure from *stderr* itself.
        """
        markers = "|".join(re.escape(marker) for marker in self.error_line_markers)
        pattern = re.compile(
            rf"^{re.escape(self.error_line_prefix)}(\d+)(?:{markers})",
            re.MULTILINE,
        )
        match = pattern.search(stderr)
        return None if match is None else int(match.group(1))


@dataclass(frozen=True)
class ServerVersionSql:
    """Expressions the dialect evaluates on the server a read runs against: its running version.

    Attributes:
        number: An integer expression of the running server's version, in the numbering
            ``RdbmsEngine.server_version_number`` reads a version text into, so it compares
            with the engine's minimum.
        text: A text expression of the running server's version, as the server names it.
    """

    number: str
    text: str

    def at_least(self, minimum: int) -> str:
        """A boolean expression: the running server's version number is *minimum* or later.

        Raises:
            ValueError: *minimum* is not a positive integer (``True`` and ``False`` included).
        """
        if isinstance(minimum, bool) or minimum <= 0:
            raise ValueError(
                f"A server's minimum version must be a positive integer in the engine's "
                f"numbering, not {minimum!r}. Pass the engine's rdbms_minimum_server_version."
            )
        return f"({self.number}) >= {minimum}"


def catalog_read_queries(queries: Sequence[CatalogQuery]) -> tuple[CatalogQuery, ...]:
    """*queries* in name order, once each, all bound to the same places.

    The composed statement binds the places once, as its first parameter, so every
    query must read the same places; its document has one member per query name.

    Raises:
        ValueError: No queries, a name given twice, a query bound to no places, or
            queries bound to different places, naming the query.
    """
    if not queries:
        raise ValueError(
            "A catalog read was given no queries. Pass every query of the engine's "
            "catalog reader (CatalogReader.catalog_queries)."
        )
    first = queries[0]
    seen: set[str] = set()
    for query in queries:
        if query.name in seen:
            raise ValueError(
                f"Catalog query '{query.name}' is given more than once. Its document is "
                "one member of the read, keyed by its name; pass each query once."
            )
        seen.add(query.name)
        if not query.places:
            raise ValueError(
                f"Catalog query '{query.name}' is bound to no places. Bind it with "
                "CatalogQuery.at_places before composing the read."
            )
        if query.places != first.places:
            raise ValueError(
                f"Catalog query '{query.name}' reads the places {list(query.places)} but "
                f"'{first.name}' reads {list(first.places)}. One read binds one set of "
                "places for every query; bind them all to the same schemas."
            )
    return tuple(sorted(queries, key=lambda query: query.name))


def catalog_fingerprint(fingerprint: str) -> str:
    """*fingerprint*, accepted only as a read's digest: 64 lowercase hexadecimal digits.

    A guard writes it into its statement as a literal, so nothing but the digest a read
    printed is ever accepted there.

    Raises:
        ValueError: *fingerprint* is not 64 lowercase hexadecimal digits.
    """
    if _CATALOG_FINGERPRINT.fullmatch(fingerprint) is None:
        raise ValueError(
            f"The catalog fingerprint {fingerprint!r} is not a SHA-256 in lowercase hex "
            "(64 digits 0-9a-f). Pass the digest the catalog read printed and the client "
            "verified."
        )
    return fingerprint


class CatalogReadStatements(Protocol):
    """The statements a dialect spells for one consistent catalog read, and its client."""

    def abort_unless_sql(
        self, condition: str, guard: str, *, reported: str | None = None
    ) -> str:
        """A statement that raises an engine error when *condition* is false, and prints nothing.

        The error's message is *guard*, quoted through ``quote_literal``, followed by the
        value of *reported* when one is given; it is never a format string, so no
        character of *guard* is read as a placeholder.

        PostgreSQL: ``DO <tag> BEGIN IF NOT (<condition>) THEN RAISE EXCEPTION USING
        MESSAGE = '<guard>'[ || (<reported>)]; END IF; END <tag>;`` with a dollar-quote
        tag the body does not hold.

        Args:
            condition: A boolean expression the dialect evaluates (a lock condition).
            guard: The text the error carries, naming what the guard protects.
            reported: An expression this dialect produced (such as
                ``ServerVersionSql.text``) whose value the error carries after *guard*.
                It is evaluated by the server, so it is never block or author text: that
                text goes in *guard*, where it is a quoted literal.

        Raises:
            DialectFeatureError: The dialect declares no guard statement.
            ValueError: *condition* or *guard* is empty, or *reported* is given empty.
        """
        ...

    def server_version_sql(self) -> ServerVersionSql:
        """The expressions of the running server's version: its number and its text.

        PostgreSQL: ``current_setting('server_version_num')::integer`` and
        ``current_setting('server_version')``.

        Raises:
            DialectFeatureError: The dialect declares no expression of the running server's version.
        """
        ...

    def catalog_search_path_sql(self, queries: Sequence[CatalogQuery]) -> str:
        """The statement that resolves names in the queries' places for the rest of the client's session.

        A catalog expression may print a name qualified exactly when its schema is not on
        the session's search path (PostgreSQL's ``regclass`` output and ``pg_get_expr``),
        so the composed document is a function of the catalog rows alone only when every
        statement computing it runs under one path: the read's composed statement, and an
        apply's fingerprint guard and the catalog statement after its commit. The path is the
        one a block's changes resolve names through (``render_set_search_path``: the places,
        then ``public``), set for the session because the guard and the closing statement
        run outside a transaction; the client's session ends with its input. The places are
        quoted identifiers, never spliced text.

        PostgreSQL: ``SET search_path TO "<place>", public;``.

        Raises:
            DialectFeatureError: The dialect declares no catalog search path.
            ValueError: As :func:`catalog_read_queries`.
        """
        ...

    def catalog_read_begin_sql(self) -> str:
        """The statement that opens the read: one snapshot for every statement, nothing written.

        PostgreSQL: ``BEGIN ISOLATION LEVEL REPEATABLE READ READ ONLY;``.

        Raises:
            DialectFeatureError: The dialect declares no read-only snapshot transaction.
        """
        ...

    def catalog_read_commit_sql(self) -> str:
        """The statement that ends the read's transaction.

        PostgreSQL: ``COMMIT;``.

        Raises:
            DialectFeatureError: The dialect declares no read-only snapshot transaction.
        """
        ...

    def apply_begin_sql(self) -> str:
        """The statement that opens a schema apply's transaction: its changes commit together or not at all.

        The changes a convergence plan renders resolve names through a search path set for
        the transaction, so they run inside this one; a failed change ends the client and
        the server rolls back every change before it.

        PostgreSQL: ``BEGIN;`` (DDL is transactional).

        Raises:
            DialectFeatureError: The dialect declares no transaction its schema changes run in.
        """
        ...

    def apply_commit_sql(self) -> str:
        """The statement that commits a schema apply's transaction.

        PostgreSQL: ``COMMIT;``.

        Raises:
            DialectFeatureError: The dialect declares no transaction its schema changes run in.
        """
        ...

    def catalog_client(self) -> CatalogClient:
        """The stock client that runs the read's input, and how that input and its output are spelled.

        PostgreSQL: ``psql -X -A -t -q -f -``, the places set with ``-v places=<array>``
        and bound by ``\\bind :places \\g``.

        Raises:
            DialectFeatureError: The dialect declares no catalog-read client.
        """
        ...

    def catalog_document_sql(self, queries: Sequence[CatalogQuery]) -> str:
        """The one statement that reads every query's document, followed by the client's ``run_bound``.

        It prints one row: one JSON object with one member per query, in query-name
        order, then that text's length and SHA-256, computed by the server in the same
        statement. No place is written into it: the places are its first parameter.

        Raises:
            DialectFeatureError: The dialect declares no composed catalog statement.
            ValueError: As :func:`catalog_read_queries`.
        """
        ...

    def catalog_fingerprint_guard_sql(
        self, queries: Sequence[CatalogQuery], fingerprint: str, guard: str
    ) -> str:
        """A statement that raises *guard* unless the catalog's digest is still *fingerprint*, and prints nothing.

        It recomputes the digest of the document :meth:`catalog_document_sql` reads for
        *queries*, from the same spelling of that document, with the queries' places bound
        inside the statement (no client binding runs it), and compares it with
        *fingerprint*. An apply that opens with it stops before any change when the
        catalog moved after the read it was planned from. The error's message is *guard*,
        quoted through ``quote_literal``, never a format string.

        PostgreSQL: ``DO <tag> DECLARE now_digest text; BEGIN EXECUTE '<digest select>'
        INTO now_digest USING ARRAY[<places>]::text[]; IF now_digest IS DISTINCT FROM
        '<fingerprint>' THEN RAISE EXCEPTION USING MESSAGE = '<guard>'; END IF; END <tag>;``.

        Raises:
            DialectFeatureError: The dialect declares no fingerprint guard.
            ValueError: As :func:`catalog_read_queries` and :func:`catalog_fingerprint`,
                or *guard* is empty.
        """
        ...


class _NamedDialect(Protocol):
    """What a refusal reads from the dialect it refuses for."""

    @property
    def name(self) -> str: ...


def _refuse_catalog_read(
    dialect: _NamedDialect,
    statement: str,
    reason: str,
    *,
    of: str = "a consistent catalog read",
) -> NoReturn:
    """Raise: *dialect* does not spell *statement* of *of* (a consistent catalog read by default).

    Raises:
        DialectFeatureError: Always, naming the dialect, the statement and why.
    """
    raise DialectFeatureError(
        f"The {dialect.name} dialect cannot render {statement} of {of}: {reason} A dialect "
        "that reads and changes its catalog through one client input overrides it."
    )


class CatalogReadRefusals:
    """The catalog-read statements of a dialect that does not override them: each refuses."""

    def abort_unless_sql(
        self: _NamedDialect, condition: str, guard: str, *, reported: str | None = None
    ) -> str:
        """Refuse: this dialect declares no statement that stops the client on a false condition."""
        _refuse_catalog_read(
            self,
            f"the guard '{guard}'",
            "it declares no statement that raises an error when a condition is false.",
        )

    def server_version_sql(self: _NamedDialect) -> ServerVersionSql:
        """Refuse: this dialect declares no expression of the running server's version."""
        _refuse_catalog_read(
            self,
            "the server version",
            "it declares no expression of the running server's version number and text.",
        )

    def catalog_search_path_sql(
        self: _NamedDialect, queries: Sequence[CatalogQuery]
    ) -> str:
        """Refuse: this dialect declares no search path a catalog document is computed under."""
        _refuse_catalog_read(
            self,
            "the search path",
            "it declares no statement that resolves names in the read's places for the session.",
        )

    def catalog_read_begin_sql(self: _NamedDialect) -> str:
        """Refuse: this dialect declares no read-only snapshot transaction."""
        _refuse_catalog_read(
            self,
            "the begin",
            "it declares no read-only transaction holding one snapshot.",
        )

    def catalog_read_commit_sql(self: _NamedDialect) -> str:
        """Refuse: this dialect declares no read-only snapshot transaction."""
        _refuse_catalog_read(
            self,
            "the commit",
            "it declares no read-only transaction holding one snapshot.",
        )

    def apply_begin_sql(self: _NamedDialect) -> str:
        """Refuse: this dialect declares no transaction its schema changes run in."""
        _refuse_catalog_read(
            self,
            "the begin",
            "it declares no transaction its schema changes run in.",
            of="a schema apply",
        )

    def apply_commit_sql(self: _NamedDialect) -> str:
        """Refuse: this dialect declares no transaction its schema changes run in."""
        _refuse_catalog_read(
            self,
            "the commit",
            "it declares no transaction its schema changes run in.",
            of="a schema apply",
        )

    def catalog_client(self: _NamedDialect) -> CatalogClient:
        """Refuse: this dialect declares no stock client that runs a catalog read."""
        _refuse_catalog_read(
            self,
            "the client",
            "it declares no stock client that runs the read's input.",
        )

    def catalog_document_sql(
        self: _NamedDialect, queries: Sequence[CatalogQuery]
    ) -> str:
        """Refuse: this dialect declares no statement composing the catalog queries."""
        names = [query.name for query in queries]
        _refuse_catalog_read(
            self,
            f"the composed statement of the queries {names}",
            "it declares no statement reading every query's document as one.",
        )

    def catalog_fingerprint_guard_sql(
        self: _NamedDialect,
        queries: Sequence[CatalogQuery],
        fingerprint: str,
        guard: str,
    ) -> str:
        """Refuse: this dialect declares no statement that checks the catalog against its fingerprint."""
        _refuse_catalog_read(
            self,
            f"the fingerprint guard '{guard}'",
            "it declares no statement that recomputes the read's digest and raises an "
            "error when it differs.",
        )
