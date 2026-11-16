"""Schema snapshot format and version."""

from __future__ import annotations

# ── Constants ──

SCHEMA_FORMAT = "cruftfree.rdbms.schema"
#: The one snapshot format version. Both sides of every comparison are produced fresh
#: on each run -- the declared schema by generation, the live catalog by its catalog
#: reader -- so a snapshot of any other version was written by another CruftFree and is
#: refused, never read under rules it was not written by.
SCHEMA_VERSION = 9
UTF8 = "utf-8"
