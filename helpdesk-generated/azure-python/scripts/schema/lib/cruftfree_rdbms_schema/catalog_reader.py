"""The engine-neutral contract for reading a live catalog into a snapshot.

A block's live schema is read by a fixed set of catalog queries a stock client
can run, and parsed into an :class:`RdbmsSchemaSnapshot` by a pure function.
This module defines that contract:

- :class:`CatalogQuery` -- one fixed query per catalog fact. Its columns are
  declared once, as ``(key, expression)`` pairs beside its ``FROM``/``WHERE``
  text; the engine's SQL dialect renders ``text`` from them, wrapped to return
  one JSON array ordered by ``key_columns``. No value is ever written into
  ``text``: the places the query reads (the block's schemas) travel beside it
  in ``places`` and are bound as its first parameter.
- :class:`ReflectionIdentity` -- the source-side identity stamped onto the
  parsed snapshot (a live catalog does not know which block it belongs to).
- :class:`CatalogReader` -- the per-engine protocol: the queries for a schema,
  and the parser of their documents.

It imports the standard library and the snapshot model only, so it can run in
generated environment-side tooling; it never imports a database driver.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, replace
from typing import Protocol

from cruftfree_rdbms_schema._snapshot_models import RdbmsSchemaSnapshot

SCHEMA_NAME_KEY = "schema_name"
"""The key every catalog query returns, naming the place each row came from."""


class CatalogQueryDeclarationError(ValueError):
    """A :class:`CatalogQuery` declaration that cannot identify or read its rows."""


@dataclass(frozen=True)
class CatalogQuery:
    """One fixed catalog query and the shape of the JSON document it returns.

    Attributes:
        name: The catalog fact the query reads (``"tables"``, ``"columns"``, ...);
            its document is keyed by this name.
        columns: ``(key, expression)`` pairs, in output order. The key names the
            row's JSON member; the expression is the engine's catalog expression.
        source: The ``FROM`` and ``WHERE`` text the columns are selected from.
        key_columns: The keys that identify a row, in sort order.
        text: The full query text the dialect rendered from the fields above.
        places: The schemas the query reads, bound as its first parameter.
    """

    name: str
    columns: tuple[tuple[str, str], ...]
    source: str
    key_columns: tuple[str, ...]
    text: str
    places: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not self.name.strip():
            raise CatalogQueryDeclarationError(
                "A catalog query has an empty name. Every query is named by the catalog "
                "fact it reads, and its document is keyed by that name."
            )
        self._require_columns()
        self._require_key_columns()
        for field_name in ("source", "text"):
            if not getattr(self, field_name).strip():
                raise CatalogQueryDeclarationError(
                    f"Catalog query '{self.name}' has an empty {field_name}. "
                    "Declare the FROM/WHERE source and render the text through the "
                    "engine's SQL dialect."
                )

    @property
    def keys(self) -> tuple[str, ...]:
        """The JSON member names every row of this query's document carries."""
        return tuple(key for key, _ in self.columns)

    def at_places(self, places: tuple[str, ...]) -> CatalogQuery:
        """This query bound to read *places*: one or more distinct, non-empty schemas."""
        if not places or any(not place.strip() for place in places):
            raise CatalogQueryDeclarationError(
                f"Catalog query '{self.name}' was given the places {places!r}; it needs "
                "at least one non-empty schema name to read, or its document is empty "
                "whatever the catalog holds."
            )
        if len(set(places)) != len(places):
            raise CatalogQueryDeclarationError(
                f"Catalog query '{self.name}' was given the places {places!r}, which name "
                "a schema more than once. Pass each schema once."
            )
        return replace(self, places=places)

    def _require_columns(self) -> None:
        if not self.columns:
            raise CatalogQueryDeclarationError(
                f"Catalog query '{self.name}' declares no columns. Declare each column "
                "once as a (key, expression) pair."
            )
        seen: set[str] = set()
        for key, expression in self.columns:
            if not key.strip() or not expression.strip():
                raise CatalogQueryDeclarationError(
                    f"Catalog query '{self.name}' declares the column ({key!r}, "
                    f"{expression!r}); both the key and the expression must be non-empty."
                )
            if key in seen:
                raise CatalogQueryDeclarationError(
                    f"Catalog query '{self.name}' declares the key '{key}' more than once. "
                    "Each key names one member of the row; declare it once."
                )
            seen.add(key)
        if SCHEMA_NAME_KEY not in seen:
            raise CatalogQueryDeclarationError(
                f"Catalog query '{self.name}' declares no '{SCHEMA_NAME_KEY}' key "
                f"(keys: {sorted(seen)}). Every query returns the place each row came "
                f"from; add a ('{SCHEMA_NAME_KEY}', <schema expression>) column."
            )

    def _require_key_columns(self) -> None:
        if not self.key_columns:
            raise CatalogQueryDeclarationError(
                f"Catalog query '{self.name}' declares no key columns. Name the keys "
                f"that identify a row, starting with '{SCHEMA_NAME_KEY}'."
            )
        keys = self.keys
        unknown = [key for key in self.key_columns if key not in keys]
        if unknown:
            raise CatalogQueryDeclarationError(
                f"Catalog query '{self.name}' names key columns {unknown} that are not "
                f"among its keys {list(keys)}. A key column must be a declared key."
            )
        if len(set(self.key_columns)) != len(self.key_columns):
            raise CatalogQueryDeclarationError(
                f"Catalog query '{self.name}' names a key column more than once in "
                f"{list(self.key_columns)}. Name each key column once."
            )


class ReflectionIdentity(Protocol):
    """Source-side identity stamped onto a parsed live snapshot.

    A live catalog does not know which CruftFree block it belongs to: ``L`` takes its
    identity fields from ``D``, the declared snapshot, handed to
    :meth:`CatalogReader.parse_catalog`.
    """

    @property
    def rdbms_id(self) -> str: ...

    @property
    def service_name(self) -> str: ...

    @property
    def service_version(self) -> str | None: ...

    @property
    def container_name(self) -> str: ...

    @property
    def container_kind(self) -> str: ...

    @property
    def block_name(self) -> str: ...

    @property
    def schema_name(self) -> str | None: ...


class CatalogReader(Protocol):
    """Engine-side contract: fixed catalog queries and a pure parser of their documents.

    Implemented per engine in cruftfree-codegen-sql. A caller runs every query of
    :meth:`catalog_queries` once, binding its ``places``, in a read-only
    transaction, and hands the documents to :meth:`parse_catalog`.
    """

    @property
    def engine(self) -> str: ...

    def catalog_queries(self, schema: str | None) -> tuple[CatalogQuery, ...]:
        """Every catalog query of the engine, bound to read *schema*'s place."""
        ...

    def parse_catalog(
        self, documents: Mapping[str, str], identity: ReflectionIdentity
    ) -> RdbmsSchemaSnapshot:
        """The snapshot the documents describe, keyed by query name.

        Refuses a missing or malformed document, a row whose keys differ from
        its query's, a duplicate row key, and any object the snapshot model
        cannot represent, naming the query or the object.
        """
        ...
