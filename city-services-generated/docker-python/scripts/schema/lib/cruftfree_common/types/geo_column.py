"""The column facts of the geographic scalar types: which they are and the SRID they are stored in.

The schema runtime (the catalog reader, the change policy and the revision renderer
a generated schema script carries) reads these names after generation without CruftFree
installed, so the module imports only the standard library.

The names are supplied by the geo extension pack rather than the builtin type
registry, which is why they are matched by canonical name instead of being resolved
through ``TypeRegistry``.
"""

from typing import Final

#: Canonical names of the geographic scalar types. Extension-provided, so not
#: resolvable through the builtin ``TypeRegistry``.
GEO_SCALAR_CANONICALS: Final[frozenset[str]] = frozenset({"Geometry", "Geography"})

#: The SRID every geographic column is declared with (EPSG:4326, WGS 84 lon/lat).
#: The column DDL each engine renders, every ORM's column declaration and the
#: schema snapshot read it; nothing else spells it for a column. The database
#: stamps it on a value that carries no SRID and refuses a value in another one.
GEO_COLUMN_SRID: Final[int] = 4326

#: The ``SnapshotType.constraints`` key a geographic column's SRID is recorded
#: under, by the declared snapshot and by every catalog reader alike.
GEO_SRID_CONSTRAINT: Final[str] = "srid"
