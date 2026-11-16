"""The column types a geographic field is created as, per RDBMS engine, typed with its SRID.

Each spelling has this one home: an engine declares its geographic column types
(:attr:`~cruftfree_common.config.datasource.rdbms_engine.RdbmsEngine.geometry_column_type`,
``geography_column_type``) from here, and the kernel's SQL type map renders the DDL
from it. Both carry :data:`~cruftfree_common.types.geo_column.GEO_COLUMN_SRID`, so the
database stamps that SRID on a value carrying none and refuses one in another SRID. The
schema runtime runs after generation without CruftFree installed, so the module imports only
the standard library and the standard-library-only ``geo_column``.
"""

from typing import Final

from cruftfree_common.types.geo_column import GEO_COLUMN_SRID

#: PostGIS typmods name a geometry subtype for both types: ``geography(Geography,n)``
#: is refused ("Invalid geometry type modifier"), so a geography column is
#: ``geography(Geometry,n)``.
POSTGRES_GEOMETRY_COLUMN_TYPE: Final[str] = f"geometry(Geometry,{GEO_COLUMN_SRID})"
POSTGRES_GEOGRAPHY_COLUMN_TYPE: Final[str] = f"geography(Geometry,{GEO_COLUMN_SRID})"
