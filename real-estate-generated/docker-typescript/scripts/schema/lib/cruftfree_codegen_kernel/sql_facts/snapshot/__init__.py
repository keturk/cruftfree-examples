"""Readers of a recorded RDBMS schema snapshot every migration renderer shares.

The table and column a schema change names, a column's recorded default as SQL, the
statements of a column's default and unique-constraint changes, and the index an
``INDEX_ADDED`` change carries -- facts of the snapshot format, never of a host language.
"""
