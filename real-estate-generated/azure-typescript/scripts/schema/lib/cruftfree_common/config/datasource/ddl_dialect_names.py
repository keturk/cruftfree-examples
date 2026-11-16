"""The names of the SQL dialects whose DDL and DML the RDBMS engines speak.

Each name has this one home: an engine declares the dialect it speaks
(:attr:`~cruftfree_common.config.datasource.rdbms_engine.RdbmsEngine.ddl_dialect`)
from here, and the SQL renderers, the schema readers and the migration planner key
their dialect tables by it. The schema runtime runs after generation without
CruftFree installed, so the module imports only the standard library.
"""

from typing import Final

POSTGRESQL_DDL_DIALECT: Final[str] = "postgresql"
